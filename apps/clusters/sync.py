"""PCS → PCSS 数据同步模块

负责收集本地集群扫描数据并推送到 PCSS 云平台。
"""
import json
import logging
from datetime import timedelta

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

SYNC_TIMEOUT = 30  # 请求超时(秒)
SYNC_MAX_RETRIES = 3


def push_cluster_data(cluster, force_full=False):
    """收集集群数据并推送到 PCSS

    Args:
        cluster: Cluster 实例，必须 sync_enabled=True 且有 sync_url/sync_id/sync_token
        force_full: 强制全量推送（忽略增量判断）

    Returns:
        dict: {"ok": True/False, "message": "...", "synced_at": ...}
    """
    if not cluster.sync_enabled:
        return {"ok": False, "message": "同步未启用"}

    if not cluster.sync_url or not cluster.sync_id or not cluster.sync_token:
        return {"ok": False, "message": "同步配置不完整（缺少 sync_url/sync_id/sync_token）"}

    # 收集数据
    data = _collect_cluster_data(cluster)

    # 判断同步类型：首次全量 or 增量
    sync_type = "full" if force_full or cluster.last_synced_at is None else "incremental"
    data["sync_type"] = sync_type

    # 添加认证信息
    data["sync_id"] = cluster.sync_id
    data["sync_token"] = cluster.sync_token
    data["scanned_at"] = timezone.now().isoformat()
    data["cluster_id"] = cluster.id
    data["cluster_name"] = cluster.name
    data["version"] = cluster.pve_version

    # 推送（带重试）
    url = f"{cluster.sync_url.rstrip('/')}/api/sync/upload/"
    last_error = None

    for attempt in range(SYNC_MAX_RETRIES):
        try:
            response = requests.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=SYNC_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                cluster.last_synced_at = timezone.now()
                cluster.save(update_fields=["last_synced_at"])
                logger.info(
                    f"集群 {cluster.name} 同步成功 ({sync_type}), "
                    f"耗时 {response.elapsed.total_seconds():.2f}s"
                )
                return {"ok": True, "message": "同步成功", "synced_at": cluster.last_synced_at}

            elif response.status_code == 401:
                return {"ok": False, "message": "同步认证失败，请检查 sync_id/sync_token"}

            elif response.status_code == 423:
                return {"ok": False, "message": "目标集群已停用"}

            elif response.status_code == 410:
                return {"ok": False, "message": "目标集群已删除"}

            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"

        except requests.Timeout:
            last_error = f"请求超时 ({SYNC_TIMEOUT}s)"
        except requests.ConnectionError as e:
            last_error = f"连接失败: {e}"
        except Exception as e:
            last_error = f"未知错误: {e}"

        # 重试前等待
        if attempt < SYNC_MAX_RETRIES - 1:
            import time
            time.sleep(2 ** attempt)  # 指数退避: 1s, 2s

    logger.error(f"集群 {cluster.name} 同步失败（重试 {SYNC_MAX_RETRIES} 次）: {last_error}")
    return {"ok": False, "message": f"同步失败: {last_error}"}


def _collect_cluster_data(cluster):
    """收集集群当前数据用于同步推送"""
    from apps.scanner.models import (
        ClusterNode, VM, LXC, VMConfig, LXCConfig, Storage,
        NetworkInterface, CephStatus, HAResource, SDNZone,
        SDNVNet, SDNSubnet, ScanHistory,
    )

    # 获取最新的扫描数据（每个节点最新一条）
    cutoff = timezone.now() - timedelta(days=7)

    nodes_qs = (
        ClusterNode.objects
        .filter(cluster=cluster, scanned_at__gte=cutoff)
        .order_by("-scanned_at")
    )
    # 每个节点名只取最新一条
    seen_nodes = set()
    nodes = []
    for n in nodes_qs:
        if n.node_name not in seen_nodes:
            seen_nodes.add(n.node_name)
            nodes.append(n)

    data = {
        "nodes": [_serialize_node(n) for n in nodes],
    }

    # 收集该集群下的 VM / LXC / Config
    node_ids = [n.id for n in nodes]
    if node_ids:
        vms = VM.objects.filter(node_id__in=node_ids)
        vm_ids = [v.id for v in vms]
        vm_configs = {c.vm_id: c for c in VMConfig.objects.filter(vm_id__in=vm_ids)}

        containers = LXC.objects.filter(node_id__in=node_ids)
        ct_ids = [c.id for c in containers]
        ct_configs = {c.container_id: c for c in LXCConfig.objects.filter(container_id__in=ct_ids)}

        # 按节点分组 VM/容器
        node_vm_map = {}
        node_ct_map = {}
        for v in vms:
            node_vm_map.setdefault(v.node_id, []).append(v)
        for c in containers:
            node_ct_map.setdefault(c.node_id, []).append(c)

        for n in nodes:
            n_data = data["nodes"][nodes.index(n)]
            n_data["vms"] = [_serialize_vm(v, vm_configs.get(v.id)) for v in node_vm_map.get(n.id, [])]
            n_data["containers"] = [_serialize_container(c, ct_configs.get(c.id)) for c in node_ct_map.get(n.id, [])]
            n_data["storages"] = _serialize_storages(n)
            n_data["networks"] = _serialize_networks(n)

    # Ceph 状态
    ceph = CephStatus.objects.filter(cluster=cluster).order_by("-scanned_at").first()
    if ceph:
        data["ceph"] = {
            "health": ceph.health,
            "total_osds": ceph.total_osds,
            "up_osds": ceph.up_osds,
            "in_osds": ceph.in_osds,
            "pool_count": ceph.pool_count,
            "total_used_gb": ceph.total_used_gb,
            "total_avail_gb": ceph.total_avail_gb,
            "total_space_gb": ceph.total_space_gb,
        }

    # HA 资源
    ha_list = HAResource.objects.filter(
        cluster=cluster, scanned_at__gte=cutoff
    ).order_by("-scanned_at")[:50]
    seen_sids = set()
    ha_resources = []
    for h in ha_list:
        if h.sid not in seen_sids:
            seen_sids.add(h.sid)
            ha_resources.append({
                "sid": h.sid,
                "type": h.resource_type,
                "vmid": h.vmid,
                "node": h.node_name,
                "state": h.state,
                "ha_group": h.ha_group,
                "ha_status": h.ha_status,
                "crm_state": h.crm_state,
                "max_restarts": h.max_restarts,
                "max_shutdown": h.max_shutdown,
                "raw": h.raw_data,
            })
    if ha_resources:
        data["ha_resources"] = ha_resources

    # SDN
    zones = SDNZone.objects.filter(cluster=cluster).order_by("-scanned_at")[:10]
    seen_zones = set()
    zone_list = []
    for z in zones:
        if z.zone not in seen_zones:
            seen_zones.add(z.zone)
            zone_list.append({
                "zone": z.zone,
                "type": z.zone_type,
                "nodes": z.nodes,
            })

    vnets = SDNVNet.objects.filter(cluster=cluster).order_by("-scanned_at")[:20]
    seen_vnets = set()
    vnet_list = []
    for v in vnets:
        if v.vnet not in seen_vnets:
            seen_vnets.add(v.vnet)
            vnet_list.append({
                "vnet": v.vnet,
                "type": v.vnet_type,
                "vlan": v.vlan,
                "zone": v.zone_name,
            })

    subnets = SDNSubnet.objects.filter(cluster=cluster).order_by("-scanned_at")[:20]
    seen_subnets = set()
    subnet_list = []
    for s in subnets:
        if s.subnet not in seen_subnets:
            seen_subnets.add(s.subnet)
            subnet_list.append({
                "subnet": s.subnet,
                "vnet": s.vnet_name,
                "gateway": s.gateway,
                "dnsserver": s.dns_server,
                "dnszoneprefix": s.dns_zone_prefix,
            })

    if zone_list or vnet_list or subnet_list:
        data["sdn"] = {
            "zones": zone_list,
            "vnets": vnet_list,
            "subnets": subnet_list,
        }

    # 扫描历史（最近几条用于趋势图）
    histories = ScanHistory.objects.filter(
        cluster=cluster, scanned_at__gte=cutoff
    ).order_by("-scanned_at")[:30]
    if histories.exists():
        data["scan_history"] = [
            {
                "snapshot_data": h.snapshot_data,
                "scanned_at": h.scanned_at.isoformat(),
            }
            for h in histories
        ]

    return data


def _serialize_node(node):
    """序列化节点数据"""
    return {
        "name": node.node_name,
        "status": node.status,
        "pve_version": node.pve_version,
        "kernel_version": node.kernel_version,
        "cpu_model": node.cpu_model,
        "cpu_cores": node.cpu_cores,
        "cpu_sockets": node.cpu_sockets,
        "cpu_load": node.cpu_load,
        "memory_total_mb": node.memory_total_mb,
        "memory_used_mb": node.memory_used_mb,
        "memory_free_mb": node.memory_free_mb,
        "memory_usage_pct": node.memory_usage_pct,
        "rootfs_total_gb": node.rootfs_total_gb,
        "rootfs_used_gb": node.rootfs_used_gb,
        "rootfs_avail_gb": node.rootfs_avail_gb,
        "swap_total_mb": node.swap_total_mb,
        "swap_used_mb": node.swap_used_mb,
        "disk_io_delay_ms": node.disk_io_delay_ms,
        "diskstat": node.diskstat,
        "ip_address": str(node.ip_address) if node.ip_address else None,
        "mac_address": node.mac_address,
        "is_ceph_node": node.is_ceph_node,
        "is_ha_node": node.is_ha_node,
        "uptime_seconds": node.uptime_seconds,
    }


def _serialize_vm(vm, config=None):
    """序列化 VM 数据"""
    data = {
        "vmid": vm.vmid,
        "name": vm.name,
        "status": vm.status,
        "cpu_cores": vm.cpu_cores,
        "cpu_sockets": vm.cpu_sockets,
        "cpu_usage": vm.cpu_usage,
        "memory_mb": vm.memory_mb,
        "memory_used_mb": vm.memory_used_mb,
        "balloon_min_mb": vm.balloon_min_mb,
        "balloon_max_mb": vm.balloon_max_mb,
        "disk_gb": vm.disk_gb,
        "max_disk_gb": vm.max_disk_gb,
        "disk_write_iops": vm.disk_write_iops,
        "disk_read_iops": vm.disk_read_iops,
        "net_in_bps": vm.net_in_bps,
        "net_out_bps": vm.net_out_bps,
        "uptime_seconds": vm.uptime_seconds,
        "os_type": vm.os_type,
        "snapshot_count": vm.snapshot_count,
        "has_template": vm.has_template,
        "tags": vm.tags,
        "description": vm.description,
    }
    if config:
        data["config"] = {
            "cpu_type": config.cpu_type,
            "cpu_cores": config.cpu_cores,
            "cpu_sockets": config.cpu_sockets,
            "memory_mb": config.memory_mb,
            "balloon_min_mb": config.balloon_min_mb,
            "os_type": config.os_type,
            "boot_order": config.boot_order,
            "scsi_disks": config.scsi_disks,
            "ide_disks": config.ide_disks,
            "net_devices": config.net_devices,
            "agent_enabled": config.agent_enabled,
            "ha_enabled": config.ha_enabled,
            "ha_group": config.ha_group,
            "description": config.description,
            "tags": config.tags,
            "raw_config": config.raw_config,
        }
    return data


def _serialize_container(container, config=None):
    """序列化 LXC 容器数据"""
    data = {
        "vmid": container.vmid,
        "name": container.name,
        "status": container.status,
        "cpu_cores": container.cpu_cores,
        "cpu_usage": container.cpu_usage,
        "memory_mb": container.memory_mb,
        "memory_used_mb": container.memory_used_mb,
        "swap_mb": container.swap_mb,
        "swap_used_mb": container.swap_used_mb,
        "disk_gb": container.disk_gb,
        "uptime_seconds": container.uptime_seconds,
        "tags": container.tags,
        "description": container.description,
        "has_template": container.has_template,
    }
    if config:
        data["config"] = {
            "hostname": config.hostname,
            "cpu_cores": config.cpu_cores,
            "memory_mb": config.memory_mb,
            "swap_mb": config.swap_mb,
            "os_type": config.os_type,
            "rootfs": config.rootfs,
            "mount_points": config.mount_points,
            "net_devices": config.net_devices,
            "ha_enabled": config.ha_enabled,
            "ha_group": config.ha_group,
            "description": config.description,
            "tags": config.tags,
            "startup_order": config.startup_order,
            "raw_config": config.raw_config,
        }
    return data


def _serialize_storages(node):
    """序列化节点存储数据"""
    from apps.scanner.models import Storage
    storages = Storage.objects.filter(node=node).order_by("-scanned_at")
    seen = set()
    result = []
    for s in storages:
        if s.storage_name not in seen:
            seen.add(s.storage_name)
            result.append({
                "name": s.storage_name,
                "type": s.type,
                "status": s.status,
                "active": s.active,
                "used_gb": s.used_gb,
                "avail_gb": s.avail_gb,
                "total_gb": s.total_gb,
                "used_fraction": s.used_fraction,
                "content_types": s.content_types,
                "shared": s.shared,
            })
    return result


def _serialize_networks(node):
    """序列化节点网络数据"""
    from apps.scanner.models import NetworkInterface
    nets = NetworkInterface.objects.filter(node=node).order_by("-scanned_at")
    seen = set()
    result = []
    for n in nets:
        if n.name not in seen:
            seen.add(n.name)
            result.append({
                "name": n.name,
                "type": n.type,
                "active": n.active,
                "method": n.method,
                "address": n.address,
                "gateway": n.gateway,
                "speed_mbps": n.speed_mbps,
                "bridge_ports": n.bridge_ports,
                "bond_mode": n.bond_mode,
                "bond_slaves": n.bond_slaves,
                "vlan_id": n.vlan_id,
                "mtu": n.mtu,
            })
    return result
