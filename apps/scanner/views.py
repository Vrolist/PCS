from datetime import timedelta

from django.db.models import Max, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from .models import (ClusterNode, VM, LXC, VMConfig, LXCConfig, VMSnapshot, HAResource,
                     Storage, NetworkInterface, CephStatus, ScanHistory, SDNZone, SDNVNet, SDNSubnet,
                     BackupStorage, BackupJob, BackupHistory, ReplicationJob,
                     FirewallOptions, FirewallRule, FirewallIPSet, FirewallIPSetEntry, FirewallAlias)


def _all_cluster_ids():
    """返回所有集群 ID 列表"""
    return Cluster.objects.values_list("id", flat=True)


def _latest_node_ids():
    """获取每个物理节点最新扫描的 ClusterNode ID 列表"""
    cluster_ids = _all_cluster_ids()
    latest = (
        ClusterNode.objects
        .filter(cluster_id__in=cluster_ids)
        .values("cluster_id", "node_name")
        .annotate(last_scan=Max("scanned_at"))
    )
    node_ids = []
    for item in latest:
        pk = (
            ClusterNode.objects
            .filter(
                cluster_id=item["cluster_id"],
                node_name=item["node_name"],
                scanned_at=item["last_scan"],
            )
            .values_list("pk", flat=True)
            .first()
        )
        if pk:
            node_ids.append(pk)
    return node_ids


class NodeListView(APIView):
    """GET /api/scanner/nodes/ — 节点列表（最新扫描数据）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        node_ids = _latest_node_ids()
        nodes = ClusterNode.objects.filter(pk__in=node_ids).select_related("cluster")
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        data = [{
            "id": n.id,
            "cluster_id": n.cluster_id,
            "cluster_name": n.cluster.name,
            "node_name": n.node_name,
            "status": n.status,
            "cpu_model": n.cpu_model,
            "cpu_vendor": n.cpu_vendor,
            "cpu_family": n.cpu_family,
            "cpu_cores": n.cpu_cores,
            "cpu_sockets": n.cpu_sockets,
            "cpu_load": n.cpu_load,
            "cpu_mhz": n.cpu_mhz,
            "cpu_hvm": n.cpu_hvm,
            "memory_total_mb": n.memory_total_mb,
            "memory_used_mb": n.memory_used_mb,
            "memory_usage_pct": n.memory_usage_pct,
            "rootfs_total_gb": n.rootfs_total_gb,
            "rootfs_used_gb": n.rootfs_used_gb,
            "rootfs_avail_gb": n.rootfs_avail_gb,
            "disk_io_delay_ms": n.disk_io_delay_ms,
            "ip_address": n.ip_address,
            "pve_version": n.pve_version,
            "kernel_version": n.kernel_version,
            "uptime_seconds": n.uptime_seconds,
            "is_ceph_node": n.is_ceph_node,
            "is_ha_node": n.is_ha_node,
            "scanned_at": n.scanned_at,
        } for n in nodes]
        return Response(data)


class SDNZoneListView(APIView):
    """GET /api/scanner/sdn/zones/ — SDN 区域列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _all_cluster_ids()
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        zones = SDNZone.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        data = [{
            "id": z.id,
            "zone": z.zone,
            "zone_type": z.zone_type,
            "nodes": z.nodes,
            "cluster_name": z.cluster.name,
            "scanned_at": z.scanned_at,
        } for z in zones]
        return Response(data)


class SDNVNetListView(APIView):
    """GET /api/scanner/sdn/vnets/ — SDN 虚拟网络列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _all_cluster_ids()
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        vnets = SDNVNet.objects.filter(cluster_id__in=cluster_ids).select_related("cluster", "zone")
        data = [{
            "id": v.id,
            "vnet": v.vnet,
            "vnet_type": v.vnet_type,
            "vlan": v.vlan,
            "zone_name": v.zone_name,
            "zone": v.zone.zone if v.zone else "",
            "cluster_name": v.cluster.name,
            "scanned_at": v.scanned_at,
        } for v in vnets]
        return Response(data)


class SDNSubnetListView(APIView):
    """GET /api/scanner/sdn/subnets/ — SDN 子网列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _all_cluster_ids()
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        subnets = SDNSubnet.objects.filter(cluster_id__in=cluster_ids).select_related("cluster", "vnet")
        data = [{
            "id": s.id,
            "subnet": s.subnet,
            "vnet_name": s.vnet_name,
            "vnet": s.vnet.vnet if s.vnet else "",
            "gateway": s.gateway,
            "dns_server": s.dns_server,
            "dns_zone_prefix": s.dns_zone_prefix,
            "cluster_name": s.cluster.name,
            "scanned_at": s.scanned_at,
        } for s in subnets]
        return Response(data)


class NodeDetailView(APIView):
    """GET /api/scanner/nodes/<id>/detail/ — 节点详情（含存储/网络/VM/容器）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, node_id):
        try:
            node = ClusterNode.objects.select_related("cluster").get(pk=node_id)
        except ClusterNode.DoesNotExist:
            return Response({"error": "Node not found"}, status=404)

        # 基本信息
        data = {
            "node": {
                "id": node.id,
                "cluster_id": node.cluster_id,
                "cluster_name": node.cluster.name,
                "node_name": node.node_name,
                "status": node.status,
                "cpu_model": node.cpu_model,
                "cpu_vendor": node.cpu_vendor,
                "cpu_family": node.cpu_family,
                "cpu_cores": node.cpu_cores,
                "cpu_sockets": node.cpu_sockets,
                "cpu_load": node.cpu_load,
                "cpu_mhz": node.cpu_mhz,
                "cpu_hvm": node.cpu_hvm,
                "cpu_flags": node.cpu_flags,
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
                "ip_address": node.ip_address,
                "mac_address": node.mac_address,
                "pve_version": node.pve_version,
                "kernel_version": node.kernel_version,
                "uptime_seconds": node.uptime_seconds,
                "is_ceph_node": node.is_ceph_node,
                "is_ha_node": node.is_ha_node,
                "scanned_at": node.scanned_at,
            },
            "storages": [],
            "networks": [],
            "vms": [],
            "containers": [],
        }

        # 该节点的最新存储
        storage_latest = (
            Storage.objects
            .filter(node=node)
            .values("storage_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        storages = []
        for item in storage_latest:
            s = Storage.objects.filter(
                node=node, storage_name=item["storage_name"],
                scanned_at=item["last_scan"]
            ).first()
            if s:
                storages.append({
                    "name": s.storage_name, "type": s.type, "status": s.status,
                    "active": s.active, "total_gb": s.total_gb, "used_gb": s.used_gb,
                    "avail_gb": s.avail_gb, "content_types": s.content_types, "shared": s.shared,
                })
        data["storages"] = storages

        # 该节点的最新网络接口
        net_latest = (
            NetworkInterface.objects
            .filter(node=node)
            .values("name")
            .annotate(last_scan=Max("scanned_at"))
        )
        networks = []
        for item in net_latest:
            ni = NetworkInterface.objects.filter(
                node=node, name=item["name"],
                scanned_at=item["last_scan"]
            ).first()
            if ni:
                networks.append({
                    "name": ni.name, "type": ni.type, "active": ni.active,
                    "method": ni.method, "address": ni.address,
                    "gateway": ni.gateway, "speed_mbps": ni.speed_mbps,
                    "bridge_ports": ni.bridge_ports,
                    "bond_mode": ni.bond_mode, "bond_slaves": ni.bond_slaves,
                    "vlan_id": ni.vlan_id, "mtu": ni.mtu,
                })
        data["networks"] = networks

        # 该节点最新扫描的 VM
        vm_latest = (
            VM.objects
            .filter(node=node)
            .values("vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        vms = []
        for item in vm_latest:
            vm = VM.objects.filter(
                node=node, vmid=item["vmid"],
                scanned_at=item["last_scan"]
            ).first()
            if vm:
                vms.append({
                    "vmid": vm.vmid, "name": vm.name, "status": vm.status,
                    "cpu_cores": vm.cpu_cores, "cpu_usage": vm.cpu_usage,
                    "memory_mb": vm.memory_mb, "memory_used_mb": vm.memory_used_mb,
                    "disk_gb": vm.max_disk_gb, "uptime_seconds": vm.uptime_seconds,
                })
        data["vms"] = vms

        # 该节点最新扫描的 LXC
        lxc_latest = (
            LXC.objects
            .filter(node=node)
            .values("vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        containers = []
        for item in lxc_latest:
            ct = LXC.objects.filter(
                node=node, vmid=item["vmid"],
                scanned_at=item["last_scan"]
            ).first()
            if ct:
                containers.append({
                    "vmid": ct.vmid, "name": ct.name, "status": ct.status,
                    "cpu_cores": ct.cpu_cores, "cpu_usage": ct.cpu_usage,
                    "memory_mb": ct.memory_mb, "memory_used_mb": ct.memory_used_mb,
                    "swap_mb": ct.swap_mb, "swap_used_mb": ct.swap_used_mb,
                    "disk_gb": ct.disk_gb, "uptime_seconds": ct.uptime_seconds,
                    "has_template": ct.has_template,
                })
        data["containers"] = containers

        return Response(data)


class StorageListView(APIView):
    """GET /api/scanner/storage/ — 存储列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()
        nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        storages = Storage.objects.filter(node__in=nodes).select_related("node__cluster")

        # 只取每个存储的最新记录
        latest = (
            storages.values("node__node_name", "storage_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(node__node_name=item["node__node_name"],
                   storage_name=item["storage_name"],
                   scanned_at=item["last_scan"])

        if q:
            storages = Storage.objects.filter(q, node__in=nodes).select_related("node__cluster")
        else:
            storages = Storage.objects.none()

        data = [{
            "id": s.id,
            "node_name": s.node.node_name,
            "cluster_name": s.node.cluster.name,
            "name": s.storage_name,
            "type": s.type,
            "status": s.status,
            "total_gb": s.total_gb,
            "used_gb": s.used_gb,
            "available_gb": s.avail_gb,
            "content": s.content_types,
            "shared": s.shared,
            "scanned_at": s.scanned_at,
        } for s in storages]
        return Response(data)


class NetworkInterfaceListView(APIView):
    """GET /api/scanner/networks/ — 网络接口列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()
        nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        ifaces = NetworkInterface.objects.filter(node__in=nodes).select_related("node__cluster")

        latest = (
            ifaces.values("node__node_name", "name")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(node__node_name=item["node__node_name"],
                   name=item["name"],
                   scanned_at=item["last_scan"])

        if q:
            ifaces = NetworkInterface.objects.filter(q, node__in=nodes).select_related("node__cluster")
        else:
            ifaces = NetworkInterface.objects.none()

        data = [{
            "id": i.id,
            "node_name": i.node.node_name,
            "cluster_name": i.node.cluster.name,
            "name": i.name,
            "type": i.type,
            "address": i.address,
            "gateway": i.gateway,
            "mac_address": "",
            "speed": i.speed_mbps,
            "status": "up" if i.active else "down",
            "bridge_ports": i.bridge_ports,
            "bond_mode": i.bond_mode,
            "bond_slaves": i.bond_slaves,
            "vlan_id": i.vlan_id,
            "mtu": i.mtu,
            "scanned_at": i.scanned_at,
        } for i in ifaces]
        return Response(data)


class CephStatusView(APIView):
    """GET /api/scanner/ceph/ — Ceph 状态"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()
        latest = (
            CephStatus.objects.filter(cluster_id__in=cluster_ids)
            .values("cluster_id")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], scanned_at=item["last_scan"])

        if q:
            ceph_statuses = CephStatus.objects.filter(q).order_by("-scanned_at")
        else:
            ceph_statuses = CephStatus.objects.none()

        if cluster_filter:
            ceph_statuses = ceph_statuses.filter(cluster_id=cluster_filter)

        if not ceph_statuses:
            return Response(None)

        s = ceph_statuses.first()
        data = {
            "id": s.id,
            "cluster_name": s.cluster.name if hasattr(s, "cluster") else "",
            "health": s.health,
            "total_osds": s.total_osds,
            "up_osds": s.up_osds,
            "in_osds": s.in_osds,
            "total_pgs": s.pool_count,
            "bytes_used_gb": s.total_used_gb,
            "bytes_total_gb": s.total_avail_gb,
            "version": "",
            "uptime": "",
            "scanned_at": s.scanned_at,
        }
        return Response(data)


class VMListView(APIView):
    """GET /api/scanner/vms/ — 虚拟机列表（每个 VM 只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _all_cluster_ids()
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        # 只取最新扫描的节点 ID
        node_ids = _latest_node_ids()

        # 在最新节点中，按 (node_name, vmid) 去重取最新
        latest = (
            VM.objects
            .filter(node_id__in=node_ids)
            .values("node__node_name", "vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                node__node_name=item["node__node_name"],
                vmid=item["vmid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        vms = VM.objects.filter(q).select_related("node", "node__cluster")

        if cluster_filter:
            vms = vms.filter(node__cluster_id=cluster_filter)
        if node_filter:
            vms = vms.filter(node_id=node_filter)
        if status_filter:
            vms = vms.filter(status=status_filter)
        if search:
            vms = vms.filter(Q(name__icontains=search) | Q(vmid__icontains=search))

        data = [{
            "id": vm.id,
            "node_id": vm.node_id,
            "node_name": vm.node.node_name,
            "cluster_id": vm.node.cluster_id,
            "cluster_name": vm.node.cluster.name,
            "vmid": vm.vmid,
            "name": vm.name,
            "status": vm.status,
            "cpu_cores": vm.cpu_cores,
            "cpu_usage": vm.cpu_usage,
            "memory_mb": vm.memory_mb,
            "memory_used_mb": vm.memory_used_mb,
            "disk_gb": vm.disk_gb,
            "max_disk_gb": vm.max_disk_gb,
            "net_in_bps": vm.net_in_bps,
            "net_out_bps": vm.net_out_bps,
            "disk_read_iops": vm.disk_read_iops,
            "disk_write_iops": vm.disk_write_iops,
            "uptime_seconds": vm.uptime_seconds,
            "os_type": vm.os_type,
            "tags": vm.tags,
            "scanned_at": vm.scanned_at,
        } for vm in vms]
        return Response(data)


class LXCListView(APIView):
    """GET /api/scanner/containers/ — 容器列表（每个容器只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        node_ids = _latest_node_ids()

        latest = (
            LXC.objects
            .filter(node_id__in=node_ids)
            .values("node__node_name", "vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                node__node_name=item["node__node_name"],
                vmid=item["vmid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        containers = LXC.objects.filter(q).select_related("node", "node__cluster")

        if cluster_filter:
            containers = containers.filter(node__cluster_id=cluster_filter)
        if node_filter:
            containers = containers.filter(node_id=node_filter)
        if status_filter:
            containers = containers.filter(status=status_filter)
        if search:
            containers = containers.filter(Q(name__icontains=search) | Q(vmid__icontains=search))

        # 预加载最新 LXCConfig 以提取 IP
        from .models import LXCConfig
        container_ids = [ct.id for ct in containers]
        latest_configs = {}
        if container_ids:
            configs = (
                LXCConfig.objects
                .filter(container_id__in=container_ids)
                .values("container_id")
                .annotate(last_scan=Max("scanned_at"))
            )
            for cfg in configs:
                lc = LXCConfig.objects.filter(
                    container_id=cfg["container_id"],
                    scanned_at=cfg["last_scan"]
                ).first()
                if lc:
                    latest_configs[cfg["container_id"]] = lc

        def _extract_ip(ct):
            """从 LXCConfig.net_devices 提取第一个 IPv4 地址"""
            cfg = latest_configs.get(ct.id)
            if not cfg:
                return ""
            for net in (cfg.net_devices or []):
                ip_val = net.get("ip", "")
                if ip_val and ip_val != "dhcp" and "/" in ip_val:
                    return ip_val.split("/")[0]
            return ""

        data = [{
            "id": ct.id,
            "node_id": ct.node_id,
            "node_name": ct.node.node_name,
            "cluster_id": ct.node.cluster_id,
            "cluster_name": ct.node.cluster.name,
            "vmid": ct.vmid,
            "name": ct.name,
            "status": ct.status,
            "ip_address": _extract_ip(ct),
            "cpu_cores": ct.cpu_cores,
            "cpu_usage": ct.cpu_usage,
            "memory_mb": ct.memory_mb,
            "memory_used_mb": ct.memory_used_mb,
            "swap_mb": ct.swap_mb,
            "swap_used_mb": ct.swap_used_mb,
            "disk_gb": ct.disk_gb,
            "uptime_seconds": ct.uptime_seconds,
            "tags": ct.tags,
            "has_template": ct.has_template,
            "scanned_at": ct.scanned_at,
        } for ct in containers]
        return Response(data)


class VMDetailView(APIView):
    """GET /api/scanner/vms/<id>/detail/ — VM 详情（含配置）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, vm_id):
        try:
            vm = VM.objects.select_related("node", "node__cluster").get(pk=vm_id)
        except VM.DoesNotExist:
            return Response({"error": "VM not found"}, status=404)

        config = (
            VMConfig.objects
            .filter(vm=vm)
            .order_by("-scanned_at")
            .first()
        )

        data = {
            "vm": {
                "id": vm.id,
                "vmid": vm.vmid,
                "name": vm.name,
                "status": vm.status,
                "node_name": vm.node.node_name,
                "cluster_name": vm.node.cluster.name,
                "cpu_cores": vm.cpu_cores,
                "cpu_sockets": vm.cpu_sockets,
                "cpu_usage": vm.cpu_usage,
                "memory_mb": vm.memory_mb,
                "memory_used_mb": vm.memory_used_mb,
                "balloon_min_mb": vm.balloon_min_mb,
                "balloon_max_mb": vm.balloon_max_mb,
                "disk_gb": vm.disk_gb,
                "max_disk_gb": vm.max_disk_gb,
                "disk_read_iops": vm.disk_read_iops,
                "disk_write_iops": vm.disk_write_iops,
                "net_in_bps": vm.net_in_bps,
                "net_out_bps": vm.net_out_bps,
                "uptime_seconds": vm.uptime_seconds,
                "os_type": vm.os_type,
                "snapshot_count": vm.snapshot_count,
                "has_template": vm.has_template,
                "tags": vm.tags,
                "description": vm.description,
                "scanned_at": vm.scanned_at,
            },
            "config": None,
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
            }

        return Response(data)


class LXCDetailView(APIView):
    """GET /api/scanner/containers/<id>/detail/ — LXC 详情（含配置）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, ct_id):
        try:
            ct = LXC.objects.select_related("node", "node__cluster").get(pk=ct_id)
        except LXC.DoesNotExist:
            return Response({"error": "Container not found"}, status=404)

        config = (
            LXCConfig.objects
            .filter(container=ct)
            .order_by("-scanned_at")
            .first()
        )

        # 从 net_devices 提取 IP
        ip_address = ""
        if config:
            for net in (config.net_devices or []):
                ip_val = net.get("ip", "")
                if ip_val and ip_val != "dhcp" and "/" in ip_val:
                    ip_address = ip_val.split("/")[0]
                    break

        data = {
            "container": {
                "id": ct.id,
                "vmid": ct.vmid,
                "name": ct.name,
                "status": ct.status,
                "node_name": ct.node.node_name,
                "cluster_name": ct.node.cluster.name,
                "ip_address": ip_address,
                "cpu_cores": ct.cpu_cores,
                "cpu_usage": ct.cpu_usage,
                "memory_mb": ct.memory_mb,
                "memory_used_mb": ct.memory_used_mb,
                "swap_mb": ct.swap_mb,
                "swap_used_mb": ct.swap_used_mb,
                "disk_gb": ct.disk_gb,
                "uptime_seconds": ct.uptime_seconds,
                "tags": ct.tags,
                "has_template": ct.has_template,
                "scanned_at": ct.scanned_at,
            },
            "config": None,
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
            }

        return Response(data)


class HAListView(APIView):
    """GET /api/scanner/ha/ — HA 高可用资源列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        # 只取每个 sid 的最新记录
        base_qs = HAResource.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            base_qs = base_qs.filter(cluster_id=cluster_filter)
        latest = (
            base_qs
            .values("sid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(sid=item["sid"], scanned_at=item["last_scan"])

        if q:
            resources = HAResource.objects.filter(q).select_related("cluster")
        else:
            resources = HAResource.objects.none()

        data = [{
            "id": r.id,
            "sid": r.sid,
            "resource_type": r.resource_type,
            "vmid": r.vmid,
            "node_name": r.node_name,
            "cluster_name": r.cluster.name,
            "state": r.state,
            "ha_group": r.ha_group,
            "ha_status": r.ha_status,
            "crm_state": r.crm_state,
            "max_restarts": r.max_restarts,
            "max_shutdown": r.max_shutdown,
            "scanned_at": r.scanned_at,
        } for r in resources]
        return Response(data)


class SnapshotListView(APIView):
    """GET /api/scanner/snapshots/ — VM 快照列表（每个快照只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _all_cluster_ids()
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        vmid_filter = request.query_params.get("vmid")
        search = request.query_params.get("search", "").strip()

        node_ids = _latest_node_ids()

        # 在最新节点中，按 (vm, snapid) 去重取最新
        latest = (
            VMSnapshot.objects
            .filter(vm__node_id__in=node_ids)
            .values("vm_id", "snapid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                vm_id=item["vm_id"],
                snapid=item["snapid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        snaps = VMSnapshot.objects.filter(q).select_related("vm", "vm__node", "vm__node__cluster")

        if cluster_filter:
            snaps = snaps.filter(vm__node__cluster_id=cluster_filter)
        if node_filter:
            snaps = snaps.filter(vm__node_id=node_filter)
        if vmid_filter:
            snaps = snaps.filter(vm__vmid=vmid_filter)
        if search:
            snaps = snaps.filter(
                Q(name__icontains=search) | Q(description__icontains=search) |
                Q(vm__name__icontains=search) | Q(snapid__icontains=search)
            )

        data = [{
            "id": s.id,
            "snapid": s.snapid,
            "name": s.name,
            "description": s.description,
            "snap_time": s.snap_time,
            "parent": s.parent,
            "ram": s.ram,
            "vmstate": s.vmstate,
            "snap_type": s.snap_type,
            "size_mb": s.size_mb,
            "vm_id": s.vm_id,
            "vm_vmid": s.vm.vmid,
            "vm_name": s.vm.name,
            "vm_status": s.vm.status,
            "node_name": s.vm.node.node_name,
            "cluster_id": s.vm.node.cluster_id,
            "cluster_name": s.vm.node.cluster.name,
            "scanned_at": s.scanned_at,
        } for s in snaps]
        return Response(data)


class BackupStorageListView(APIView):
    """GET /api/scanner/backup/storages/ — 备份存储列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()
        qs = BackupStorage.objects.filter(cluster_id__in=cluster_ids).select_related("cluster", "node")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        # Only latest per (cluster, storage_name)
        latest = (
            qs.values("cluster_id", "storage_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], storage_name=item["storage_name"],
                    scanned_at=item["last_scan"])
        if q:
            qs = BackupStorage.objects.filter(q, cluster_id__in=cluster_ids).select_related("cluster", "node")
        else:
            qs = BackupStorage.objects.none()
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        data = [{
            "id": s.id,
            "cluster_id": s.cluster_id,
            "cluster_name": s.cluster.name,
            "node_name": s.node.node_name if s.node else "",
            "storage_name": s.storage_name,
            "storage_type": s.storage_type,
            "path": s.path,
            "content_types": s.content_types,
            "active": s.active,
            "shared": s.shared,
            "total_gb": s.total_gb,
            "used_gb": s.used_gb,
            "avail_gb": s.avail_gb,
            "used_fraction": s.used_fraction,
            "scanned_at": s.scanned_at,
        } for s in qs]
        return Response(data)


class BackupJobListView(APIView):
    """GET /api/scanner/backup/jobs/ — 备份任务列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        status_filter = request.query_params.get("status")
        cluster_ids = _all_cluster_ids()
        qs = BackupJob.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        # Only latest per (cluster, job_id)
        latest = (
            qs.values("cluster_id", "job_id")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], job_id=item["job_id"],
                    scanned_at=item["last_scan"])
        if q:
            qs = BackupJob.objects.filter(q, cluster_id__in=cluster_ids).select_related("cluster")
        else:
            qs = BackupJob.objects.none()
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        if status_filter:
            qs = qs.filter(last_status=status_filter)
        data = [{
            "id": j.id,
            "cluster_id": j.cluster_id,
            "cluster_name": j.cluster.name,
            "job_id": j.job_id,
            "vmid": j.vmid,
            "resource_type": j.resource_type,
            "node_name": j.node_name,
            "storage_name": j.storage_name,
            "mode": j.mode,
            "schedule": j.schedule,
            "retention": j.retention,
            "enabled": j.enabled,
            "compress": j.compress,
            "notes": j.notes,
            "last_run": j.last_run,
            "last_status": j.last_status,
            "next_run": j.next_run,
            "scanned_at": j.scanned_at,
        } for j in qs]
        return Response(data)


class BackupHistoryListView(APIView):
    """GET /api/scanner/backup/history/ — 备份历史列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        status_filter = request.query_params.get("status")
        vmid_filter = request.query_params.get("vmid")
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        cluster_ids = _all_cluster_ids()
        qs = BackupHistory.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if vmid_filter:
            qs = qs.filter(vmid=vmid_filter)
        if search:
            qs = qs.filter(
                Q(task_id__icontains=search) | Q(filename__icontains=search) |
                Q(node_name__icontains=search) | Q(error_message__icontains=search)
            )

        total = qs.count()
        qs = qs.order_by("-started_at")[(page - 1) * page_size: page * page_size]

        data = [{
            "id": h.id,
            "cluster_id": h.cluster_id,
            "cluster_name": h.cluster.name,
            "task_id": h.task_id,
            "vmid": h.vmid,
            "resource_type": h.resource_type,
            "node_name": h.node_name,
            "storage_name": h.storage_name,
            "mode": h.mode,
            "status": h.status,
            "started_at": h.started_at,
            "finished_at": h.finished_at,
            "duration_seconds": h.duration_seconds,
            "size_bytes": h.size_bytes,
            "filename": h.filename,
            "error_message": h.error_message,
            "scanned_at": h.scanned_at,
        } for h in qs]
        return Response({"count": total, "results": data})


class BackupStatsView(APIView):
    """GET /api/scanner/backup/stats/ — 备份统计概览"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        storages_qs = BackupStorage.objects.filter(cluster_id__in=cluster_ids)
        jobs_qs = BackupJob.objects.filter(cluster_id__in=cluster_ids)
        history_qs = BackupHistory.objects.filter(cluster_id__in=cluster_ids)

        if cluster_filter:
            storages_qs = storages_qs.filter(cluster_id=cluster_filter)
            jobs_qs = jobs_qs.filter(cluster_id=cluster_filter)
            history_qs = history_qs.filter(cluster_id=cluster_filter)

        # Deduplicate storages
        storages_latest = storages_qs.values("cluster_id", "storage_name").annotate(last_scan=Max("scanned_at"))
        q = Q()
        for item in storages_latest:
            q |= Q(cluster_id=item["cluster_id"], storage_name=item["storage_name"],
                    scanned_at=item["last_scan"])
        storages = BackupStorage.objects.filter(q) if q else BackupStorage.objects.none()

        # Deduplicate jobs
        jobs_latest = jobs_qs.values("cluster_id", "job_id").annotate(last_scan=Max("scanned_at"))
        jq = Q()
        for item in jobs_latest:
            jq |= Q(cluster_id=item["cluster_id"], job_id=item["job_id"],
                     scanned_at=item["last_scan"])
        jobs = BackupJob.objects.filter(jq) if jq else BackupJob.objects.none()

        total_storage = storages.count()
        total_storages_gb = sum(s.total_gb or 0 for s in storages)
        used_storages_gb = sum(s.used_gb or 0 for s in storages)

        total_jobs = jobs.count()
        enabled_jobs = jobs.filter(enabled=True).count()

        total_backups = history_qs.count()
        success_backups = history_qs.filter(status="ok").count()
        failed_backups = history_qs.filter(status="error").count()
        total_backup_size = sum(h.size_bytes or 0 for h in history_qs)

        return Response({
            "total_storages": total_storage,
            "total_storages_gb": total_storages_gb,
            "used_storages_gb": used_storages_gb,
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "total_backups": total_backups,
            "success_backups": success_backups,
            "failed_backups": failed_backups,
            "success_rate": round(success_backups / total_backups * 100, 1) if total_backups > 0 else 0,
            "total_backup_size_gb": round(total_backup_size / 1073741824, 2),
        })


class ReplicationJobListView(APIView):
    """GET /api/scanner/replication/ — 存储复制任务列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        cluster_ids = _all_cluster_ids()
        qs = ReplicationJob.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        if status_filter:
            qs = qs.filter(state=status_filter)
        if search:
            qs = qs.filter(
                Q(job_id__icontains=search) | Q(source_node__icontains=search) |
                Q(target_node__icontains=search) | Q(comment__icontains=search)
            )

        # Only latest per (cluster, job_id)
        latest = (
            qs.values("cluster_id", "job_id")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], job_id=item["job_id"],
                    scanned_at=item["last_scan"])
        if q:
            qs = ReplicationJob.objects.filter(q, cluster_id__in=cluster_ids).select_related("cluster")
        else:
            qs = ReplicationJob.objects.none()
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        if status_filter:
            qs = qs.filter(state=status_filter)
        if search:
            qs = qs.filter(
                Q(job_id__icontains=search) | Q(source_node__icontains=search) |
                Q(target_node__icontains=search) | Q(comment__icontains=search)
            )

        data = [{
            "id": j.id,
            "cluster_id": j.cluster_id,
            "cluster_name": j.cluster.name,
            "job_id": j.job_id,
            "vmid": j.vmid,
            "resource_type": j.resource_type,
            "source_node": j.source_node,
            "target_node": j.target_node,
            "schedule": j.schedule,
            "rate_limit": j.rate_limit,
            "comment": j.comment,
            "enabled": j.enabled,
            "state": j.state,
            "last_sync": j.last_sync,
            "last_try": j.last_try,
            "last_duration": j.last_duration,
            "error_message": j.error_message,
            "sync_count": j.sync_count,
            "scanned_at": j.scanned_at,
        } for j in qs]
        return Response(data)


# ============================================================
# 防火墙 API（只读）
# ============================================================

class FirewallSummaryView(APIView):
    """GET /api/scanner/firewall/summary/ — 防火墙总览"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        opts = FirewallOptions.objects.filter(cluster_id__in=cluster_ids)
        rules = FirewallRule.objects.filter(cluster_id__in=cluster_ids)
        ipsets = FirewallIPSet.objects.filter(cluster_id__in=cluster_ids)
        aliases = FirewallAlias.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            opts = opts.filter(cluster_id=cluster_filter)
            rules = rules.filter(cluster_id=cluster_filter)
            ipsets = ipsets.filter(cluster_id=cluster_filter)
            aliases = aliases.filter(cluster_id=cluster_filter)

        # 集群级选项（取最新）
        cluster_opts = opts.filter(scope="cluster").order_by("-scanned_at").first()

        return Response({
            "cluster_enabled": cluster_opts.enabled if cluster_opts else False,
            "policy_in": cluster_opts.policy_in if cluster_opts else "ACCEPT",
            "policy_out": cluster_opts.policy_out if cluster_opts else "ACCEPT",
            "policy_forward": cluster_opts.policy_forward if cluster_opts else "ACCEPT",
            "total_rules": rules.count(),
            "total_security_groups": rules.filter(scope="group").values("group_name").distinct().count(),
            "total_ipsets": ipsets.count(),
            "total_aliases": aliases.count(),
            "cluster_rules": rules.filter(scope="cluster").count(),
            "node_rules": rules.filter(scope="node").count(),
            "vm_rules": rules.filter(scope="vm").count(),
            "ct_rules": rules.filter(scope="ct").count(),
            "group_rules": rules.filter(scope="group").count(),
            "scanned_at": cluster_opts.scanned_at if cluster_opts else None,
        })


class FirewallRulesView(APIView):
    """GET /api/scanner/firewall/rules/ — 防火墙规则列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        scope_filter = request.query_params.get("scope")
        group_filter = request.query_params.get("group")
        search = request.query_params.get("search", "").strip()

        cluster_ids = _all_cluster_ids()
        qs = FirewallRule.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")

        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        if scope_filter:
            qs = qs.filter(scope=scope_filter)
        if group_filter:
            qs = qs.filter(group_name=group_filter)
        if search:
            qs = qs.filter(
                Q(source__icontains=search) | Q(dest__icontains=search) |
                Q(dport__icontains=search) | Q(comment__icontains=search) |
                Q(proto__icontains=search)
            )

        # 只取每个 (scope, node_name, vmid, group_name, pos) 的最新记录
        latest = (
            qs.values("cluster_id", "scope", "node_name", "vmid", "group_name", "pos")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                cluster_id=item["cluster_id"], scope=item["scope"],
                node_name=item["node_name"], vmid=item["vmid"],
                group_name=item["group_name"], pos=item["pos"],
                scanned_at=item["last_scan"],
            )
        if q:
            rules = FirewallRule.objects.filter(q).select_related("cluster")
            if cluster_filter:
                rules = rules.filter(cluster_id=cluster_filter)
            if scope_filter:
                rules = rules.filter(scope=scope_filter)
            if group_filter:
                rules = rules.filter(group_name=group_filter)
            if search:
                rules = rules.filter(
                    Q(source__icontains=search) | Q(dest__icontains=search) |
                    Q(dport__icontains=search) | Q(comment__icontains=search) |
                    Q(proto__icontains=search)
                )
        else:
            rules = FirewallRule.objects.none()

        data = [{
            "id": r.id,
            "cluster_id": r.cluster_id,
            "cluster_name": r.cluster.name,
            "scope": r.scope,
            "scope_display": dict(FirewallRule._meta.get_field("scope").choices or {}).get(r.scope, r.scope),
            "group_name": r.group_name,
            "node_name": r.node_name,
            "vmid": r.vmid,
            "pos": r.pos,
            "action": r.action,
            "direction": r.direction,
            "proto": r.proto,
            "source": r.source,
            "dest": r.dest,
            "dport": r.dport,
            "sport": r.sport,
            "comment": r.comment,
            "enabled": r.enabled,
            "log": r.log,
            "iface": r.iface,
            "macro": r.macro,
            "scanned_at": r.scanned_at,
        } for r in rules]
        return Response(data)


class FirewallIPSetsView(APIView):
    """GET /api/scanner/firewall/ipsets/ — 防火墙 IPSet 列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        qs = FirewallIPSet.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)

        # 只取每个 (cluster, name) 的最新记录
        latest = qs.values("cluster_id", "name").annotate(last_scan=Max("scanned_at"))
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], name=item["name"], scanned_at=item["last_scan"])
        if q:
            ipsets = FirewallIPSet.objects.filter(q).select_related("cluster")
            if cluster_filter:
                ipsets = ipsets.filter(cluster_id=cluster_filter)
        else:
            ipsets = FirewallIPSet.objects.none()

        data = []
        for ip in ipsets:
            entries = ip.entries.all().values("id", "cidr", "comment", "nomatch")
            data.append({
                "id": ip.id,
                "cluster_id": ip.cluster_id,
                "cluster_name": ip.cluster.name,
                "scope": ip.scope,
                "name": ip.name,
                "comment": ip.comment,
                "entry_count": len(entries),
                "entries": list(entries),
                "scanned_at": ip.scanned_at,
            })
        return Response(data)


class FirewallAliasesView(APIView):
    """GET /api/scanner/firewall/aliases/ — 防火墙别名列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        qs = FirewallAlias.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)

        # 只取每个 (cluster, name) 的最新记录
        latest = qs.values("cluster_id", "name").annotate(last_scan=Max("scanned_at"))
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], name=item["name"], scanned_at=item["last_scan"])
        if q:
            aliases = FirewallAlias.objects.filter(q).select_related("cluster")
            if cluster_filter:
                aliases = aliases.filter(cluster_id=cluster_filter)
        else:
            aliases = FirewallAlias.objects.none()

        data = [{
            "id": a.id,
            "cluster_id": a.cluster_id,
            "cluster_name": a.cluster.name,
            "scope": a.scope,
            "name": a.name,
            "cidr": a.cidr,
            "alias_type": a.alias_type,
            "comment": a.comment,
            "scanned_at": a.scanned_at,
        } for a in aliases]
        return Response(data)


class FirewallOptionsView(APIView):
    """GET /api/scanner/firewall/options/ — 防火墙选项列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        qs = FirewallOptions.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)

        # 只取每个 (scope, node_name, vmid) 的最新记录
        latest = qs.values("cluster_id", "scope", "node_name", "vmid").annotate(last_scan=Max("scanned_at"))
        q = Q()
        for item in latest:
            q |= Q(
                cluster_id=item["cluster_id"], scope=item["scope"],
                node_name=item["node_name"], vmid=item["vmid"],
                scanned_at=item["last_scan"],
            )
        if q:
            opts = FirewallOptions.objects.filter(q).select_related("cluster")
            if cluster_filter:
                opts = opts.filter(cluster_id=cluster_filter)
        else:
            opts = FirewallOptions.objects.none()

        data = [{
            "id": o.id,
            "cluster_id": o.cluster_id,
            "cluster_name": o.cluster.name,
            "scope": o.scope,
            "node_name": o.node_name,
            "vmid": o.vmid,
            "enabled": o.enabled,
            "policy_in": o.policy_in,
            "policy_out": o.policy_out,
            "policy_forward": o.policy_forward,
            "log_level_in": o.log_level_in,
            "log_level_out": o.log_level_out,
            "dhcp": o.dhcp,
            "ipfilter": o.ipfilter,
            "ndp": o.ndp,
            "macfilter": o.macfilter,
            "scanned_at": o.scanned_at,
        } for o in opts]
        return Response(data)


class FirewallSecurityGroupsView(APIView):
    """GET /api/scanner/firewall/security-groups/ — 防火墙安全组列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        qs = FirewallRule.objects.filter(cluster_id__in=cluster_ids, scope="group")
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)

        # 只取每个 (cluster, group_name, pos) 的最新记录
        latest = qs.values("cluster_id", "group_name", "pos").annotate(last_scan=Max("scanned_at"))
        q = Q()
        for item in latest:
            q |= Q(
                cluster_id=item["cluster_id"], group_name=item["group_name"],
                pos=item["pos"], scanned_at=item["last_scan"],
            )
        if q:
            rules = FirewallRule.objects.filter(q, scope="group").select_related("cluster")
            if cluster_filter:
                rules = rules.filter(cluster_id=cluster_filter)
        else:
            rules = FirewallRule.objects.none()

        # 按安全组分组
        groups = {}
        for r in rules:
            gname = r.group_name
            if gname not in groups:
                groups[gname] = {
                    "name": gname,
                    "cluster_id": r.cluster_id,
                    "cluster_name": r.cluster.name,
                    "rules": [],
                    "scanned_at": r.scanned_at,
                }
            groups[gname]["rules"].append({
                "id": r.id,
                "pos": r.pos,
                "action": r.action,
                "direction": r.direction,
                "proto": r.proto,
                "source": r.source,
                "dest": r.dest,
                "dport": r.dport,
                "sport": r.sport,
                "comment": r.comment,
                "enabled": r.enabled,
                "log": r.log,
                "macro": r.macro,
            })

        return Response(list(groups.values()))


class DependencyGraphView(APIView):
    """GET /api/scanner/dependency/ — 依赖关系图数据"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        resource_type = request.query_params.get("resource_type")  # vm or container
        resource_id = request.query_params.get("resource_id")
        cluster_ids = _all_cluster_ids()
        if cluster_filter:
            cluster_ids = [int(cluster_filter)]

        nodes_list = []
        edges_list = []

        # 1. 集群节点
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        for c in clusters:
            nodes_list.append({
                "id": f"cluster-{c.id}",
                "type": "cluster",
                "name": c.name,
                "cluster_id": c.id,
            })

        # 2. 物理节点
        node_ids = _latest_node_ids()
        if cluster_filter:
            node_ids = [
                nid for nid in node_ids
                if ClusterNode.objects.filter(pk=nid, cluster_id=cluster_filter).exists()
            ]

        # 始终显示集群中的所有节点
        pve_nodes = ClusterNode.objects.filter(pk__in=node_ids).select_related("cluster")
        for n in pve_nodes:
            nodes_list.append({
                "id": f"node-{n.id}",
                "type": "node",
                "node_id": n.id,
                "name": n.node_name,
                "status": n.status,
                "cpu_load": n.cpu_load,
                "memory_usage_pct": n.memory_usage_pct,
                "ip_address": n.ip_address,
                "cluster_id": n.cluster_id,
            })
            edges_list.append({
                "source": f"cluster-{n.cluster_id}",
                "target": f"node-{n.id}",
                "type": "cluster-node",
            })

        # 未选择特定资源时，只返回集群+节点（快速加载）
        if not (resource_type and resource_id):
            return Response({"nodes": nodes_list, "edges": edges_list})

        vm_entries = []   # (vm_obj, node_dict)
        ct_entries = []   # (lxc_obj, node_dict)
        vm_qs = VM.objects.none()
        lxc_qs = LXC.objects.none()

        # 3. VM（仅在选择 VM 时加载）
        if resource_type == "vm":
            vm_qs = VM.objects.filter(node_id__in=node_ids).select_related("node").order_by("node_id", "vmid", "-scanned_at")
            if resource_id:
                try:
                    vm_ref = VM.objects.get(pk=resource_id)
                    vm_qs = vm_qs.filter(node_id=vm_ref.node_id, vmid=vm_ref.vmid)
                except VM.DoesNotExist:
                    vm_qs = vm_qs.none()
            seen_vms = set()
            for vm in vm_qs:
                vm_key = f"{vm.node_id}-{vm.vmid}"
                if vm_key in seen_vms:
                    continue
                seen_vms.add(vm_key)
                vm_id = f"vm-{vm.node_id}-{vm.vmid}"
                vm_node = {
                    "id": vm_id,
                    "type": "vm",
                    "name": vm.name or f"VM {vm.vmid}",
                    "vmid": vm.vmid,
                    "status": vm.status,
                    "cpu_cores": vm.cpu_cores,
                    "memory_mb": vm.memory_mb,
                    "node_id": vm.node_id,
                    "ha_enabled": False,
                    "ha_group": "",
                }
                nodes_list.append(vm_node)
                vm_entries.append((vm, vm_node))
                edges_list.append({
                    "source": f"node-{vm.node_id}",
                    "target": vm_id,
                    "type": "node-vm",
                })

        # 4. LXC 容器（仅在选择容器时加载）
        if resource_type == "container":
            lxc_qs = LXC.objects.filter(node_id__in=node_ids).select_related("node").order_by("node_id", "vmid", "-scanned_at")
            if resource_id:
                try:
                    ct_ref = LXC.objects.get(pk=resource_id)
                    lxc_qs = lxc_qs.filter(node_id=ct_ref.node_id, vmid=ct_ref.vmid)
                except LXC.DoesNotExist:
                    lxc_qs = lxc_qs.none()
            seen_containers = set()
            for ct in lxc_qs:
                ct_key = f"{ct.node_id}-{ct.vmid}"
                if ct_key in seen_containers:
                    continue
                seen_containers.add(ct_key)
                ct_id = f"ct-{ct.node_id}-{ct.vmid}"
                ct_node = {
                    "id": ct_id,
                    "type": "container",
                    "name": ct.name or f"CT {ct.vmid}",
                    "vmid": ct.vmid,
                    "status": ct.status,
                    "cpu_cores": ct.cpu_cores,
                    "memory_mb": ct.memory_mb,
                    "node_id": ct.node_id,
                    "ha_enabled": False,
                    "ha_group": "",
                }
                nodes_list.append(ct_node)
                ct_entries.append((ct, ct_node))
                edges_list.append({
                    "source": f"node-{ct.node_id}",
                    "target": ct_id,
                    "type": "node-container",
                })

        # 3.1 通过 HAResource 补充 VM/容器的 HA 信息
        # 4.1 通过 HAResource 补充容器的 HA 信息
        # 4.2 HA 组节点（跨节点的 HA 组关系）
        # 统一从 HAResource 查询 HA 信息（HAResource 是 HA 配置的权威来源）
        ha_resource_qs = HAResource.objects.filter(cluster_id__in=cluster_ids)
        ha_map: dict[tuple[str, int], str] = {}  # (resource_type, vmid) -> ha_group
        for hr in ha_resource_qs:
            if hr.vmid:
                group = hr.ha_group or (hr.raw_data or {}).get("group", "")
                if group:
                    ha_map[(hr.resource_type, hr.vmid)] = group

        for vm_obj, vm_node in vm_entries:
            group = ha_map.get(("vm", vm_obj.vmid), "")
            vm_node["ha_enabled"] = bool(group)
            vm_node["ha_group"] = group

        for ct_obj, ct_node in ct_entries:
            group = ha_map.get(("ct", ct_obj.vmid), "")
            ct_node["ha_enabled"] = bool(group)
            ct_node["ha_group"] = group

        # 4.2 HA 故障转移连线
        # HA 资源可迁移到集群内其他节点，用虚线连接表示
        ha_enabled_resources = [
            n for n in nodes_list
            if n.get("ha_enabled") and n["type"] in ("vm", "container")
        ]
        pve_node_ids = [n["id"] for n in nodes_list if n["type"] == "node"]
        for res in ha_enabled_resources:
            # ID 格式: "vm-{node_db_id}-{vmid}" / "ct-{node_db_id}-{vmid}"
            # 提取 node_db_id 拼出当前节点 ID
            parts = res["id"].split("-", 2)  # ["vm", "5", "100"]
            if len(parts) >= 2:
                current_node_id = f"node-{parts[1]}"
                for nid in pve_node_ids:
                    if nid != current_node_id:
                        edges_list.append({
                            "source": res["id"],
                            "target": nid,
                            "type": "ha-failover",
                        })

        # 5. 存储 - 选择特定资源时只显示该资源使用的存储
        storage_node_ids = node_ids
        used_storage_names = set()  # 该资源使用的存储名
        if resource_id and resource_type:
            if resource_type == "vm":
                vm_obj = VM.objects.filter(pk=resource_id).first()
                if vm_obj:
                    storage_node_ids = [vm_obj.node_id]
                    # 从 VMConfig 获取该 VM 使用的存储
                    vm_config = VMConfig.objects.filter(vm=vm_obj).first()
                    if vm_config:
                        for disk in (vm_config.scsi_disks or []):
                            if disk.get("storage"):
                                used_storage_names.add(disk["storage"])
                        for disk in (vm_config.ide_disks or []):
                            if disk.get("storage"):
                                used_storage_names.add(disk["storage"])
            elif resource_type == "container":
                ct_obj = LXC.objects.filter(pk=resource_id).first()
                if ct_obj:
                    storage_node_ids = [ct_obj.node_id]
                    # 从 LXCConfig 获取该容器使用的存储
                    ct_config = LXCConfig.objects.filter(container=ct_obj).first()
                    if ct_config and ct_config.rootfs and ct_config.rootfs.get("storage"):
                        used_storage_names.add(ct_config.rootfs["storage"])

        storage_qs = Storage.objects.filter(node_id__in=storage_node_ids).order_by("node_id", "storage_name", "-scanned_at")
        seen_storages = set()
        for s in storage_qs:
            storage_key = f"{s.node_id}-{s.storage_name}"
            if storage_key in seen_storages:
                continue
            # 选择特定资源时，只显示该资源使用的存储
            if resource_id and resource_type and used_storage_names and s.storage_name not in used_storage_names:
                continue
            seen_storages.add(storage_key)
            storage_id = f"storage-{s.node_id}-{s.storage_name}"
            nodes_list.append({
                "id": storage_id,
                "type": "storage",
                "name": s.storage_name,
                "storage_type": s.type,
                "total_gb": s.total_gb,
                "used_gb": s.used_gb,
                "shared": s.shared,
                "node_id": s.node_id,
            })
            edges_list.append({
                "source": f"node-{s.node_id}",
                "target": storage_id,
                "type": "node-storage",
            })

        # 6. 网络接口 - 选择特定资源时只显示该资源使用的网桥
        net_node_ids = node_ids
        used_bridges = set()  # 该资源使用的网桥名
        if resource_id and resource_type:
            if resource_type == "vm":
                vm_obj = VM.objects.filter(pk=resource_id).first()
                if vm_obj:
                    net_node_ids = [vm_obj.node_id]
                    # 从 VMConfig 获取该 VM 使用的网桥
                    vm_config = VMConfig.objects.filter(vm=vm_obj).first()
                    if vm_config:
                        for nd in (vm_config.net_devices or []):
                            if nd.get("bridge"):
                                used_bridges.add(nd["bridge"])
            elif resource_type == "container":
                ct_obj = LXC.objects.filter(pk=resource_id).first()
                if ct_obj:
                    net_node_ids = [ct_obj.node_id]
                    # 从 LXCConfig 获取该容器使用的网桥
                    ct_config = LXCConfig.objects.filter(container=ct_obj).first()
                    if ct_config:
                        for nd in (ct_config.net_devices or []):
                            if nd.get("bridge"):
                                used_bridges.add(nd["bridge"])

        net_qs = NetworkInterface.objects.filter(node_id__in=net_node_ids).order_by("node_id", "name", "-scanned_at")
        seen_nets = set()
        for ni in net_qs:
            net_key = f"{ni.node_id}-{ni.name}"
            if net_key in seen_nets:
                continue
            # 选择特定资源时，只显示该资源使用的网桥，不显示物理网卡
            if resource_id and resource_type:
                if used_bridges:
                    if ni.name not in used_bridges:
                        continue
                else:
                    # 没有网桥配置时不显示任何网络
                    continue
            seen_nets.add(net_key)
            net_id = f"net-{ni.node_id}-{ni.name}"
            nodes_list.append({
                "id": net_id,
                "type": "network",
                "name": ni.name,
                "net_type": ni.type,
                "address": ni.address,
                "active": ni.active,
                "bridge_ports": ni.bridge_ports,
                "bond_slaves": ni.bond_slaves,
                "node_id": ni.node_id,
            })
            edges_list.append({
                "source": f"node-{ni.node_id}",
                "target": net_id,
                "type": "node-network",
            })

        # 7. VM/容器 → 网络（通过 VMConfig.net_devices / LXCConfig.net_devices 的 bridge 字段）
        vm_ids = [vm.id for vm in vm_qs]
        if vm_ids:
            vm_configs = VMConfig.objects.filter(vm_id__in=vm_ids)
            for cfg in vm_configs:
                vm_obj = next((v for v in vm_qs if v.id == cfg.vm_id), None)
                if not vm_obj:
                    continue
                vm_node_id = f"vm-{vm_obj.node_id}-{vm_obj.vmid}"
                for nd in (cfg.net_devices or []):
                    bridge = nd.get("bridge", "")
                    if bridge:
                        net_id = f"net-{vm_obj.node_id}-{bridge}"
                        # 只添加有效连接
                        if any(n["id"] == net_id for n in nodes_list):
                            edges_list.append({
                                "source": vm_node_id,
                                "target": net_id,
                                "type": "vm-network",
                            })

        ct_ids = [ct.id for ct in lxc_qs]
        if ct_ids:
            ct_configs = LXCConfig.objects.filter(container_id__in=ct_ids)
            for cfg in ct_configs:
                ct_obj = next((c for c in lxc_qs if c.id == cfg.container_id), None)
                if not ct_obj:
                    continue
                ct_node_id = f"ct-{ct_obj.node_id}-{ct_obj.vmid}"
                for nd in (cfg.net_devices or []):
                    bridge = nd.get("bridge", "")
                    if bridge:
                        net_id = f"net-{ct_obj.node_id}-{bridge}"
                        if any(n["id"] == net_id for n in nodes_list):
                            edges_list.append({
                                "source": ct_node_id,
                                "target": net_id,
                                "type": "container-network",
                            })

        # 7b. VM/容器 → 存储（通过 VMConfig/LXCConfig 的磁盘配置）
        # 只在选择特定资源时添加这些连线
        if resource_id and resource_type:
            if resource_type == "vm" and vm_ids:
                vm_configs = VMConfig.objects.filter(vm_id__in=vm_ids)
                for cfg in vm_configs:
                    vm_obj = next((v for v in vm_qs if v.id == cfg.vm_id), None)
                    if not vm_obj:
                        continue
                    vm_node_id = f"vm-{vm_obj.node_id}-{vm_obj.vmid}"
                    # SCSI 磁盘
                    for disk in (cfg.scsi_disks or []):
                        storage_name = disk.get("storage", "")
                        if storage_name:
                            storage_id = f"storage-{vm_obj.node_id}-{storage_name}"
                            if any(n["id"] == storage_id for n in nodes_list):
                                edges_list.append({
                                    "source": vm_node_id,
                                    "target": storage_id,
                                    "type": "vm-storage",
                                })
                    # IDE 磁盘
                    for disk in (cfg.ide_disks or []):
                        storage_name = disk.get("storage", "")
                        if storage_name:
                            storage_id = f"storage-{vm_obj.node_id}-{storage_name}"
                            if any(n["id"] == storage_id for n in nodes_list):
                                edges_list.append({
                                    "source": vm_node_id,
                                    "target": storage_id,
                                    "type": "vm-storage",
                                })
            elif resource_type == "container" and ct_ids:
                ct_configs = LXCConfig.objects.filter(container_id__in=ct_ids)
                for cfg in ct_configs:
                    ct_obj = next((c for c in lxc_qs if c.id == cfg.container_id), None)
                    if not ct_obj:
                        continue
                    ct_node_id = f"ct-{ct_obj.node_id}-{ct_obj.vmid}"
                    # rootfs
                    if cfg.rootfs and cfg.rootfs.get("storage"):
                        storage_id = f"storage-{ct_obj.node_id}-{cfg.rootfs['storage']}"
                        if any(n["id"] == storage_id for n in nodes_list):
                            edges_list.append({
                                "source": ct_node_id,
                                "target": storage_id,
                                "type": "container-storage",
                            })
                    # mount_points
                    for mp in (cfg.mount_points or []):
                        # 从 raw 中解析 storage name（格式如 "local-lvm:vm-107-disk-0,size=8G"）
                        raw = mp.get("raw", "")
                        if ":" in raw:
                            storage_name = raw.split(":")[0]
                            storage_id = f"storage-{ct_obj.node_id}-{storage_name}"
                            if any(n["id"] == storage_id for n in nodes_list):
                                edges_list.append({
                                    "source": ct_node_id,
                                    "target": storage_id,
                                    "type": "container-storage",
                                })

        # 8. Ceph 状态 - 选择特定资源时不显示 Ceph（集群级别）
        if resource_id and resource_type:
            ceph_qs = CephStatus.objects.none()
        else:
            ceph_qs = CephStatus.objects.filter(cluster_id__in=cluster_ids).order_by("cluster_id", "-scanned_at")
        seen_ceph = set()
        for cs in ceph_qs:
            ceph_key = str(cs.cluster_id)
            if ceph_key in seen_ceph:
                continue
            seen_ceph.add(ceph_key)
            ceph_id = f"ceph-{cs.cluster_id}"
            nodes_list.append({
                "id": ceph_id,
                "type": "ceph",
                "name": "Ceph 存储",
                "health": cs.health,
                "total_osds": cs.total_osds,
                "up_osds": cs.up_osds,
                "cluster_id": cs.cluster_id,
            })
            edges_list.append({
                "source": f"cluster-{cs.cluster_id}",
                "target": ceph_id,
                "type": "cluster-ceph",
            })

        # 9. HA 资源
        ha_qs = HAResource.objects.filter(cluster_id__in=cluster_ids).select_related("cluster").order_by("sid", "-scanned_at")
        # 如果选择了特定资源，只显示与该资源相关的 HA
        if resource_id and resource_type:
            if resource_type == "vm":
                vm_obj = VM.objects.filter(pk=resource_id).first()
                if vm_obj:
                    ha_qs = ha_qs.filter(vmid=vm_obj.vmid, resource_type="vm")
                else:
                    ha_qs = ha_qs.none()
            elif resource_type == "container":
                ct_obj = LXC.objects.filter(pk=resource_id).first()
                if ct_obj:
                    ha_qs = ha_qs.filter(vmid=ct_obj.vmid, resource_type="lxc")
                else:
                    ha_qs = ha_qs.none()
        seen_ha = set()
        for ha in ha_qs:
            ha_key = ha.sid
            if ha_key in seen_ha:
                continue
            seen_ha.add(ha_key)
            ha_id = f"ha-{ha.cluster_id}-{ha.sid}"
            nodes_list.append({
                "id": ha_id,
                "type": "ha",
                "name": ha.sid,
                "resource_type": ha.resource_type,
                "vmid": ha.vmid,
                "state": ha.state,
                "ha_group": ha.ha_group,
                "cluster_id": ha.cluster_id,
            })
            # HA → 节点（优先用 node_name，否则通过 vmid 关联 VM/LXC）
            if ha.node_name:
                target_node = next(
                    (n for n in nodes_list if n["type"] == "node" and n["name"] == ha.node_name),
                    None
                )
                if target_node:
                    edges_list.append({
                        "source": target_node["id"],
                        "target": ha_id,
                        "type": "node-ha",
                    })
            elif ha.vmid:
                # 通过 vmid 查找对应的 VM 或 LXC
                target_vm = next(
                    (n for n in nodes_list if n["type"] == "vm" and n.get("vmid") == ha.vmid),
                    None
                )
                target_ct = next(
                    (n for n in nodes_list if n["type"] == "container" and n.get("vmid") == ha.vmid),
                    None
                )
                target_resource = target_vm or target_ct
                if target_resource:
                    edges_list.append({
                        "source": target_resource["id"],
                        "target": ha_id,
                        "type": "resource-ha",
                    })

        # 10. SDN - 选择特定资源时不显示 SDN（集群级别）
        if resource_id and resource_type:
            sdn_zones = SDNZone.objects.none()
        else:
            sdn_zones = SDNZone.objects.filter(cluster_id__in=cluster_ids)
        for zone in sdn_zones:
            zone_id = f"sdn-zone-{zone.cluster_id}-{zone.zone}"
            nodes_list.append({
                "id": zone_id,
                "type": "sdn_zone",
                "name": zone.zone,
                "zone_type": zone.zone_type,
                "nodes": zone.nodes,
                "cluster_id": zone.cluster_id,
            })
            edges_list.append({
                "source": f"cluster-{zone.cluster_id}",
                "target": zone_id,
                "type": "cluster-sdn",
            })

        # 选择特定资源时不显示 SDN vnets/subnets
        if resource_id and resource_type:
            sdn_vnets = SDNVNet.objects.none()
        else:
            sdn_vnets = SDNVNet.objects.filter(cluster_id__in=cluster_ids).select_related("zone")
        for vnet in sdn_vnets:
            vnet_id = f"sdn-vnet-{vnet.cluster_id}-{vnet.vnet}"
            nodes_list.append({
                "id": vnet_id,
                "type": "sdn_vnet",
                "name": vnet.vnet,
                "vnet_type": vnet.vnet_type,
                "vlan": vnet.vlan,
                "cluster_id": vnet.cluster_id,
            })
            if vnet.zone:
                zone_id = f"sdn-zone-{vnet.cluster_id}-{vnet.zone.zone}"
                edges_list.append({
                    "source": zone_id,
                    "target": vnet_id,
                    "type": "zone-vnet",
                })

        # 选择特定资源时不显示 SDN subnets
        if resource_id and resource_type:
            sdn_subnets = SDNSubnet.objects.none()
        else:
            sdn_subnets = SDNSubnet.objects.filter(cluster_id__in=cluster_ids).select_related("vnet")
        for subnet in sdn_subnets:
            subnet_id = f"sdn-subnet-{subnet.cluster_id}-{subnet.subnet}"
            nodes_list.append({
                "id": subnet_id,
                "type": "sdn_subnet",
                "name": subnet.subnet,
                "gateway": subnet.gateway,
                "dns_server": subnet.dns_server,
                "cluster_id": subnet.cluster_id,
            })
            if subnet.vnet:
                vnet_id = f"sdn-vnet-{subnet.cluster_id}-{subnet.vnet.vnet}"
                edges_list.append({
                    "source": vnet_id,
                    "target": subnet_id,
                    "type": "vnet-subnet",
                })

        return Response({"nodes": nodes_list, "edges": edges_list})



class ChangeTrackingView(APIView):
    """变更追踪 API — 对比相邻扫描记录，检测硬件/存储/网络/节点变化"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_id = request.query_params.get("cluster_id")
        days = int(request.query_params.get("days", 7))

        if not cluster_id:
            return Response({"error": "cluster_id is required"}, status=400)

        cutoff = timezone.now() - timedelta(days=days)
        changes: list[dict] = []

        # 1. 节点硬件变更（内存/根分区/CPU）
        self._detect_node_changes(cluster_id, cutoff, changes)

        # 2. 存储变更（存储池增减/容量变化）
        self._detect_storage_changes(cluster_id, cutoff, changes)

        # 3. 网络接口变更（网卡增减/IP变化）
        self._detect_network_changes(cluster_id, cutoff, changes)

        # 4. 节点增减
        self._detect_node_membership_changes(cluster_id, cutoff, changes)

        # 5. VM/LXC 数量变化（基于 ScanHistory）
        self._detect_vm_count_changes(cluster_id, cutoff, changes)

        # 按时间倒序排列
        changes.sort(key=lambda x: x["detected_at"], reverse=True)

        return Response({"changes": changes, "total": len(changes)})

    def _detect_node_changes(self, cluster_id, cutoff, changes):
        """检测节点内存/根分区/CPU 核心数变化"""
        nodes = (
            ClusterNode.objects.filter(cluster_id=cluster_id, scanned_at__gte=cutoff)
            .order_by("node_name", "scanned_at")
        )

        grouped: dict[str, list] = {}
        for n in nodes:
            grouped.setdefault(n.node_name, []).append(n)

        for node_name, records in grouped.items():
            if len(records) < 2:
                continue
            prev, curr = records[-2], records[-1]

            # 内存变化（MB → GB 显示）
            if prev.memory_total_mb != curr.memory_total_mb:
                delta = curr.memory_total_mb - prev.memory_total_mb
                changes.append({
                    "type": "memory",
                    "severity": "info",
                    "node": node_name,
                    "title": f"节点 {node_name} 内存{'增加' if delta > 0 else '减少'}",
                    "detail": f"{prev.memory_total_mb} MB → {curr.memory_total_mb} MB ({'+' if delta > 0 else ''}{delta} MB)",
                    "old_value": prev.memory_total_mb,
                    "new_value": curr.memory_total_mb,
                    "unit": "MB",
                    "detected_at": curr.scanned_at.isoformat(),
                })

            # 根分区变化
            if prev.rootfs_total_gb != curr.rootfs_total_gb:
                delta = round(curr.rootfs_total_gb - prev.rootfs_total_gb, 2)
                changes.append({
                    "type": "disk",
                    "severity": "info",
                    "node": node_name,
                    "title": f"节点 {node_name} 根分区{'扩容' if delta > 0 else '缩减'}",
                    "detail": f"{prev.rootfs_total_gb} GB → {curr.rootfs_total_gb} GB ({'+' if delta > 0 else ''}{delta} GB)",
                    "old_value": prev.rootfs_total_gb,
                    "new_value": curr.rootfs_total_gb,
                    "unit": "GB",
                    "detected_at": curr.scanned_at.isoformat(),
                })

            # CPU 核心数变化
            if prev.cpu_cores != curr.cpu_cores:
                changes.append({
                    "type": "cpu",
                    "severity": "warning",
                    "node": node_name,
                    "title": f"节点 {node_name} CPU 核心数变化",
                    "detail": f"{prev.cpu_cores} 核 → {curr.cpu_cores} 核",
                    "old_value": prev.cpu_cores,
                    "new_value": curr.cpu_cores,
                    "unit": "核",
                    "detected_at": curr.scanned_at.isoformat(),
                })

    def _detect_storage_changes(self, cluster_id, cutoff, changes):
        """检测存储池增减和容量变化"""
        node_ids = list(
            ClusterNode.objects.filter(cluster_id=cluster_id)
            .values_list("id", flat=True)
        )

        # 一次查询获取所有存储池的首次记录（用于新增检测）
        first_by_key: dict[tuple, Storage] = {}
        all_storages_qs = (
            Storage.objects.filter(node_id__in=node_ids)
            .select_related("node")
            .order_by("scanned_at")
        )
        for s in all_storages_qs:
            key = (s.node.node_name, s.storage_name)
            if key not in first_by_key:
                first_by_key[key] = s

        all_keys = set(first_by_key.keys())

        # cutoff 之前存在的存储池
        old_keys = set()
        old_qs = (Storage.objects.filter(node_id__in=node_ids, scanned_at__lt=cutoff)
            .select_related("node")
            .values_list("node__node_name", "storage_name").distinct())
        for s in old_qs:
            old_keys.add((s[0], s[1]))

        # 新增存储池（排除新节点自带的存储池）
        old_node_names = set(
            ClusterNode.objects.filter(cluster_id=cluster_id, scanned_at__lt=cutoff)
            .values_list("node_name", flat=True).distinct()
        )

        for node_name, storage_name in all_keys - old_keys:
            if node_name not in old_node_names:
                continue
            first = first_by_key[(node_name, storage_name)]
            changes.append({
                "type": "storage_added",
                "severity": "info",
                "node": node_name,
                "title": f"新增存储池 {storage_name}",
                "detail": f"类型: {first.type}, 容量: {first.total_gb} GB, 内容: {first.content_types}",
                "old_value": "",
                "new_value": first.total_gb,
                "unit": "GB",
                "detected_at": first.scanned_at.isoformat(),
            })

        # 移除存储池
        last_by_key: dict[tuple, Storage] = {}
        old_storage_qs = (Storage.objects.filter(node_id__in=node_ids, scanned_at__lt=cutoff)
            .select_related("node")
            .order_by("-scanned_at"))
        for s in old_storage_qs:
            key = (s.node.node_name, s.storage_name)
            if key not in last_by_key:
                last_by_key[key] = s

        for node_name, storage_name in old_keys - all_keys:
            last = last_by_key.get((node_name, storage_name))
            if last:
                changes.append({
                    "type": "storage_removed",
                    "severity": "warning",
                    "node": node_name,
                    "title": f"存储池 {storage_name} 已移除",
                    "detail": f"原容量: {last.total_gb} GB",
                    "old_value": last.total_gb,
                    "new_value": "",
                    "unit": "GB",
                    "detected_at": last.scanned_at.isoformat(),
                })

        # 容量变化
        storages = (
            Storage.objects.filter(node_id__in=node_ids, scanned_at__gte=cutoff)
            .select_related("node")
            .order_by("storage_name", "scanned_at")
        )
        grouped: dict[str, list] = {}
        for s in storages:
            key = f"{s.node.node_name}:{s.storage_name}"
            grouped.setdefault(key, []).append(s)

        for key, records in grouped.items():
            if len(records) < 2:
                continue
            prev, curr = records[-2], records[-1]
            node_name = curr.node.node_name

            if prev.total_gb != curr.total_gb:
                delta = round(curr.total_gb - prev.total_gb, 2)
                changes.append({
                    "type": "storage",
                    "severity": "info",
                    "node": node_name,
                    "title": f"存储 {curr.storage_name} 容量{'增加' if delta > 0 else '减少'}",
                    "detail": f"{prev.total_gb} GB → {curr.total_gb} GB ({'+' if delta > 0 else ''}{delta} GB)",
                    "old_value": prev.total_gb,
                    "new_value": curr.total_gb,
                    "unit": "GB",
                    "detected_at": curr.scanned_at.isoformat(),
                })

    def _detect_network_changes(self, cluster_id, cutoff, changes):
        """检测网卡增减和 IP 变化"""
        nets = (
            NetworkInterface.objects.filter(node__cluster_id=cluster_id, scanned_at__gte=cutoff)
            .select_related("node")
            .order_by("name", "scanned_at")
        )

        grouped: dict[str, list] = {}
        for n in nets:
            key = f"{n.node.node_name}:{n.name}"
            grouped.setdefault(key, []).append(n)

        for key, records in grouped.items():
            if len(records) < 2:
                continue
            prev, curr = records[-2], records[-1]
            node_name = curr.node.node_name

            if prev.address != curr.address:
                changes.append({
                    "type": "network",
                    "severity": "warning",
                    "node": node_name,
                    "title": f"网卡 {curr.name} IP 变化",
                    "detail": f"{prev.address or '无'} → {curr.address or '无'}",
                    "old_value": prev.address or "",
                    "new_value": curr.address or "",
                    "unit": "",
                    "detected_at": curr.scanned_at.isoformat(),
                })

    def _detect_node_membership_changes(self, cluster_id, cutoff, changes):
        """检测节点增减"""
        all_names = set(
            ClusterNode.objects.filter(cluster_id=cluster_id)
            .values_list("node_name", flat=True)
            .distinct()
        )
        old_names = set(
            ClusterNode.objects.filter(cluster_id=cluster_id, scanned_at__lt=cutoff)
            .values_list("node_name", flat=True)
            .distinct()
        )

        # 新增节点
        for name in all_names - old_names:
            first = ClusterNode.objects.filter(
                cluster_id=cluster_id, node_name=name
            ).order_by("scanned_at").first()
            if first:
                changes.append({
                    "type": "node_added",
                    "severity": "info",
                    "node": name,
                    "title": f"新增节点 {name}",
                    "detail": f"内存 {first.memory_total_mb} MB, 根分区 {first.rootfs_total_gb} GB",
                    "old_value": "",
                    "new_value": name,
                    "unit": "",
                    "detected_at": first.scanned_at.isoformat(),
                })

        # 移除节点
        for name in old_names - all_names:
            last = ClusterNode.objects.filter(
                cluster_id=cluster_id, node_name=name
            ).order_by("-scanned_at").first()
            if last:
                changes.append({
                    "type": "node_removed",
                    "severity": "critical",
                    "node": name,
                    "title": f"节点 {name} 已移除",
                    "detail": f"最后在线时间: {last.scanned_at.strftime('%Y-%m-%d %H:%M')}",
                    "old_value": name,
                    "new_value": "",
                    "unit": "",
                    "detected_at": last.scanned_at.isoformat(),
                })

    def _detect_vm_count_changes(self, cluster_id, cutoff, changes):
        """基于 ScanHistory.snapshot_data 检测 VM/LXC 数量变化"""
        histories = (
            ScanHistory.objects.filter(cluster_id=cluster_id, scanned_at__gte=cutoff)
            .order_by("scanned_at")
        )

        if histories.count() < 2:
            return

        prev, curr = histories.first(), histories.last()
        prev_data = prev.snapshot_data or {}
        curr_data = curr.snapshot_data or {}

        prev_vms = prev_data.get("total_vms", 0)
        curr_vms = curr_data.get("total_vms", 0)
        if prev_vms != curr_vms:
            delta = curr_vms - prev_vms
            changes.append({
                "type": "vm_count",
                "severity": "info" if delta > 0 else "warning",
                "node": "",
                "title": f"虚拟机数量{'增加' if delta > 0 else '减少'}",
                "detail": f"{prev_vms} 台 → {curr_vms} 台 ({'+' if delta > 0 else ''}{delta})",
                "old_value": prev_vms,
                "new_value": curr_vms,
                "unit": "台",
                "detected_at": curr.scanned_at.isoformat(),
            })

        prev_ct = prev_data.get("total_containers", 0)
        curr_ct = curr_data.get("total_containers", 0)
        if prev_ct != curr_ct:
            delta = curr_ct - prev_ct
            changes.append({
                "type": "container_count",
                "severity": "info" if delta > 0 else "warning",
                "node": "",
                "title": f"容器数量{'增加' if delta > 0 else '减少'}",
                "detail": f"{prev_ct} 个 → {curr_ct} 个 ({'+' if delta > 0 else ''}{delta})",
                "old_value": prev_ct,
                "new_value": curr_ct,
                "unit": "个",
                "detected_at": curr.scanned_at.isoformat(),
            })


class ResourceReclamationView(APIView):
    """GET /api/scanner/resource-reclamation/ — 资源回收建议"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()
        
        # 获取最新扫描的节点
        node_ids = _latest_node_ids()
        
        # 1. 僵尸VM检测（停止状态且运行时长为0）
        zombie_vms = self._detect_zombie_vms(node_ids, cluster_filter)
        
        # 2. 僵尸容器检测
        zombie_containers = self._detect_zombie_containers(node_ids, cluster_filter)
        
        # 3. 旧快照检测（超过30天）
        old_snapshots = self._detect_old_snapshots(cluster_ids, cluster_filter)
        
        # 4. 低使用率存储检测
        low_usage_storages = self._detect_low_usage_storages(node_ids, cluster_filter)
        
        # 5. 空闲资源检测（CPU和内存使用率都为0）
        idle_resources = self._detect_idle_resources(node_ids, cluster_filter)
        
        # 计算可回收空间
        reclaimable_space_gb = self._calculate_reclaimable_space(
            old_snapshots, zombie_vms, zombie_containers
        )
        
        # 计算总存储空间
        total_storage_gb = self._calculate_total_storage(node_ids, cluster_filter)
        
        return Response({
            "summary": {
                "zombie_vms_count": len(zombie_vms),
                "zombie_containers_count": len(zombie_containers),
                "old_snapshots_count": len(old_snapshots),
                "low_usage_storages_count": len(low_usage_storages),
                "idle_resources_count": len(idle_resources),
                "reclaimable_space_gb": reclaimable_space_gb,
                "total_storage_gb": total_storage_gb,
            },
            "zombie_vms": zombie_vms,
            "zombie_containers": zombie_containers,
            "old_snapshots": old_snapshots,
            "low_usage_storages": low_usage_storages,
            "idle_resources": idle_resources,
        })
    
    def _detect_zombie_vms(self, node_ids, cluster_filter):
        """检测僵尸VM（停止状态且运行时长为0）"""
        vms = VM.objects.filter(
            node_id__in=node_ids,
            status="stopped",
            uptime_seconds=0
        ).select_related("node", "node__cluster")
        
        if cluster_filter:
            vms = vms.filter(node__cluster_id=cluster_filter)
        
        now = timezone.now()
        result = []
        for vm in vms:
            # 计算停机天数（基于扫描时间）
            stopped_days = (now - vm.scanned_at).days if vm.scanned_at else 0
            
            # 风险等级判断
            risk_level = "low"
            if stopped_days > 90:
                risk_level = "high"
            elif stopped_days > 30:
                risk_level = "medium"
            
            # 回收建议
            suggestion = "确认业务不再需要后可删除"
            if stopped_days > 90:
                suggestion = "长期停机，建议确认后删除释放资源"
            elif stopped_days > 30:
                suggestion = "停机超过30天，建议评估是否需要"
            
            result.append({
                "id": vm.id,
                "vmid": vm.vmid,
                "name": vm.name,
                "node_name": vm.node.node_name,
                "cluster_name": vm.node.cluster.name,
                "cpu_cores": vm.cpu_cores,
                "memory_mb": vm.memory_mb,
                "disk_gb": vm.disk_gb,
                "status": vm.status,
                "scanned_at": vm.scanned_at.isoformat(),
                "stopped_days": stopped_days,
                "risk_level": risk_level,
                "suggestion": suggestion,
            })
        
        return result
    
    def _detect_zombie_containers(self, node_ids, cluster_filter):
        """检测僵尸容器"""
        containers = LXC.objects.filter(
            node_id__in=node_ids,
            status="stopped",
            uptime_seconds=0
        ).select_related("node", "node__cluster")
        
        if cluster_filter:
            containers = containers.filter(node__cluster_id=cluster_filter)
        
        now = timezone.now()
        result = []
        for ct in containers:
            # 计算停机天数（基于扫描时间）
            stopped_days = (now - ct.scanned_at).days if ct.scanned_at else 0
            
            # 风险等级判断
            risk_level = "low"
            if stopped_days > 90:
                risk_level = "high"
            elif stopped_days > 30:
                risk_level = "medium"
            
            # 回收建议
            suggestion = "确认业务不再需要后可删除"
            if stopped_days > 90:
                suggestion = "长期停机，建议确认后删除释放资源"
            elif stopped_days > 30:
                suggestion = "停机超过30天，建议评估是否需要"
            
            result.append({
                "id": ct.id,
                "vmid": ct.vmid,
                "name": ct.name,
                "node_name": ct.node.node_name,
                "cluster_name": ct.node.cluster.name,
                "cpu_cores": ct.cpu_cores,
                "memory_mb": ct.memory_mb,
                "disk_gb": ct.disk_gb,
                "status": ct.status,
                "scanned_at": ct.scanned_at.isoformat(),
                "stopped_days": stopped_days,
                "risk_level": risk_level,
                "suggestion": suggestion,
            })
        
        return result
    
    def _detect_old_snapshots(self, cluster_ids, cluster_filter):
        """检测旧快照（超过30天）"""
        cutoff_date = timezone.now() - timedelta(days=30)
        
        snapshots = VMSnapshot.objects.filter(
            vm__node__cluster_id__in=cluster_ids,
            snap_time__lt=cutoff_date
        ).select_related("vm", "vm__node", "vm__node__cluster")
        
        if cluster_filter:
            snapshots = snapshots.filter(vm__node__cluster_id=cluster_filter)
        
        now = timezone.now()
        result = []
        for snap in snapshots:
            # 计算快照年龄天数
            snap_age_days = (now - snap.snap_time).days if snap.snap_time else 0
            
            # 风险等级判断
            risk_level = "low"
            if snap_age_days > 180:
                risk_level = "high"
            elif snap_age_days > 90:
                risk_level = "medium"
            
            # 回收建议
            suggestion = "旧快照，建议清理"
            if snap_age_days > 180:
                suggestion = "超旧快照，强烈建议清理"
            elif snap_age_days > 90:
                suggestion = "快照超过90天，建议评估后清理"
            
            result.append({
                "id": snap.id,
                "snapid": snap.snapid,
                "name": snap.name,
                "vm_name": snap.vm.name,
                "vm_vmid": snap.vm.vmid,
                "node_name": snap.vm.node.node_name,
                "cluster_name": snap.vm.node.cluster.name,
                "snap_time": snap.snap_time.isoformat() if snap.snap_time else None,
                "size_mb": snap.size_mb,
                "size_gb": round(snap.size_mb / 1024, 2) if snap.size_mb else 0,
                "snap_age_days": snap_age_days,
                "risk_level": risk_level,
                "suggestion": suggestion,
            })
        
        return result
    
    def _detect_low_usage_storages(self, node_ids, cluster_filter):
        """检测低使用率存储（使用率<30%）"""
        storages = Storage.objects.filter(
            node_id__in=node_ids,
            used_fraction__lt=0.3
        ).select_related("node", "node__cluster")
        
        if cluster_filter:
            storages = storages.filter(node__cluster_id=cluster_filter)
        
        result = []
        for s in storages:
            # 风险等级判断（基于使用率）
            used_pct = (s.used_fraction or 0) * 100
            risk_level = "low"
            if used_pct < 5:
                risk_level = "high"
            elif used_pct < 15:
                risk_level = "medium"
            
            # 回收建议
            suggestion = "存储使用率低，可考虑优化或卸载"
            if used_pct < 5:
                suggestion = "几乎空闲，建议检查是否可卸载"
            elif used_pct < 15:
                suggestion = "使用率很低，建议评估存储用途"
            
            result.append({
                "id": s.id,
                "storage_name": s.storage_name,
                "type": s.type,
                "node_name": s.node.node_name,
                "cluster_name": s.node.cluster.name,
                "total_gb": s.total_gb,
                "used_gb": s.used_gb,
                "avail_gb": s.avail_gb,
                "used_fraction": s.used_fraction,
                "scanned_at": s.scanned_at.isoformat(),
                "risk_level": risk_level,
                "suggestion": suggestion,
            })
        
        return result
    
    def _detect_idle_resources(self, node_ids, cluster_filter):
        """检测空闲资源（CPU和内存使用率都为0）"""
        # 空闲VM
        idle_vms = VM.objects.filter(
            node_id__in=node_ids,
            cpu_usage=0,
            memory_used_mb=0,
            status="running"
        ).select_related("node", "node__cluster")
        
        if cluster_filter:
            idle_vms = idle_vms.filter(node__cluster_id=cluster_filter)
        
        idle_resources = []
        for vm in idle_vms:
            idle_resources.append({
                "id": vm.id,
                "type": "vm",
                "vmid": vm.vmid,
                "name": vm.name,
                "node_name": vm.node.node_name,
                "cluster_name": vm.node.cluster.name,
                "cpu_cores": vm.cpu_cores,
                "memory_mb": vm.memory_mb,
                "disk_gb": vm.disk_gb,
                "scanned_at": vm.scanned_at.isoformat(),
                "risk_level": "medium",
                "suggestion": "运行中但无负载，建议检查是否需要",
            })
        
        # 空闲容器
        idle_containers = LXC.objects.filter(
            node_id__in=node_ids,
            cpu_usage=0,
            memory_used_mb=0,
            status="running"
        ).select_related("node", "node__cluster")
        
        if cluster_filter:
            idle_containers = idle_containers.filter(node__cluster_id=cluster_filter)
        
        for ct in idle_containers:
            idle_resources.append({
                "id": ct.id,
                "type": "container",
                "vmid": ct.vmid,
                "name": ct.name,
                "node_name": ct.node.node_name,
                "cluster_name": ct.node.cluster.name,
                "cpu_cores": ct.cpu_cores,
                "memory_mb": ct.memory_mb,
                "disk_gb": ct.disk_gb,
                "scanned_at": ct.scanned_at.isoformat(),
                "risk_level": "medium",
                "suggestion": "运行中但无负载，建议检查是否需要",
            })
        
        return idle_resources
    
    def _calculate_reclaimable_space(self, old_snapshots, zombie_vms, zombie_containers):
        """计算可回收空间（GB）"""
        total_gb = 0
        
        # 旧快照空间
        for snap in old_snapshots:
            if snap.get("size_gb"):
                total_gb += snap["size_gb"]
        
        # 僵尸VM磁盘空间（假设可以回收）
        for vm in zombie_vms:
            if vm.get("disk_gb"):
                total_gb += vm["disk_gb"]
        
        # 僵尸容器磁盘空间
        for ct in zombie_containers:
            if ct.get("disk_gb"):
                total_gb += ct["disk_gb"]
        
        return round(total_gb, 2)
    
    def _calculate_total_storage(self, node_ids, cluster_filter):
        """计算总存储空间（GB）"""
        storages = Storage.objects.filter(
            node_id__in=node_ids,
            total_gb__isnull=False
        )
        
        if cluster_filter:
            storages = storages.filter(node__cluster_id=cluster_filter)
        
        total_gb = storages.aggregate(total=Sum("total_gb"))["total"] or 0
        return round(total_gb, 2)


class CpuCompatView(APIView):
    """GET /api/scanner/cpu-compat/ — 集群内 CPU 兼容性检测"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_id = request.query_params.get("cluster_id")
        node_ids = _latest_node_ids()
        nodes = ClusterNode.objects.filter(pk__in=node_ids)
        if cluster_id:
            nodes = nodes.filter(cluster_id=cluster_id)

        # 按集群分组
        clusters = {}
        for n in nodes.select_related("cluster"):
            cid = n.cluster_id
            if cid not in clusters:
                clusters[cid] = {"cluster_name": n.cluster.name, "nodes": []}
            clusters[cid]["nodes"].append(n)

        results = []
        for cid, info in clusters.items():
            vendors = {}
            for n in info["nodes"]:
                v = n.cpu_vendor or "unknown"
                if v not in vendors:
                    vendors[v] = []
                vendors[v].append(n.node_name)

            compatible = len(vendors) <= 1
            warning = ""
            if not compatible:
                parts = [f"{v}: {', '.join(names)}" for v, names in vendors.items()]
                warning = f"混合 CPU 厂商可能导致在线迁移失败 ({'; '.join(parts)})"

            # 检测 hvm 一致性
            hvm_set = set(n.cpu_hvm for n in info["nodes"])
            hvm_compatible = len(hvm_set) <= 1

            results.append({
                "cluster_id": cid,
                "cluster_name": info["cluster_name"],
                "compatible": compatible and hvm_compatible,
                "vendors": vendors,
                "hvm_consistent": hvm_compatible,
                "node_count": len(info["nodes"]),
                "warning": warning,
            })

        return Response(results)


class CpuFlagsCompareView(APIView):
    """GET /api/scanner/cpu-flags/compare/ — 集群内 CPU flags 对比"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_id = request.query_params.get("cluster_id")
        node_ids = _latest_node_ids()
        nodes = ClusterNode.objects.filter(pk__in=node_ids)
        if cluster_id:
            nodes = nodes.filter(cluster_id=cluster_id)

        node_flags = []
        for n in nodes:
            flags_set = set(n.cpu_flags.split()) if n.cpu_flags else set()
            node_flags.append({
                "node_name": n.node_name,
                "cluster_id": n.cluster_id,
                "cluster_name": n.cluster.name,
                "cpu_vendor": n.cpu_vendor,
                "cpu_model": n.cpu_model,
                "flags": sorted(flags_set),
                "flags_count": len(flags_set),
            })

        # 计算交集和差集
        all_flags_sets = [set(nf["flags"]) for nf in node_flags]
        if all_flags_sets:
            common = set.intersection(*all_flags_sets) if len(all_flags_sets) > 1 else all_flags_sets[0]
            unique_per_node = {}
            for nf in node_flags:
                node_set = set(nf["flags"])
                others = set()
                for other_nf in node_flags:
                    if other_nf["node_name"] != nf["node_name"]:
                        others |= set(other_nf["flags"])
                unique_per_node[nf["node_name"]] = sorted(node_set - others)
        else:
            common = set()
            unique_per_node = {}

        return Response({
            "nodes": node_flags,
            "common_flags": sorted(common),
            "common_flags_count": len(common),
            "unique_per_node": unique_per_node,
        })
