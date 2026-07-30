"""
PVE 数据上下文构建模块
根据用户消息关键词，从数据库查询对应 PVE 数据，注入到 LLM 上下文中。
"""

import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# 关键词 → 数据层映射
LAYER_KEYWORDS = {
    'nodes': ['节点', 'node', 'cpu', '内存', '负载', 'load', '磁盘', 'disk', '运行时长', 'uptime'],
    'vms': ['虚拟机', 'vm', 'qemu', '虚拟', '实例'],
    'containers': ['容器', 'lxc', 'container'],
    'storage': ['存储', 'storage', 'ceph', '磁盘容量', '存储池'],
    'network': ['网络', 'network', 'sdn', 'ip', '网卡', '接口', 'bridge', 'bond', 'vlan'],
    'ha': ['ha', '高可用', '高可', 'failover', 'crm'],
    'summary': [],  # 始终注入
}


def build_pve_context(cluster_id: int, user_message: str) -> str:
    """
    根据 cluster_id 和用户消息，构建 PVE 数据上下文。
    返回注入到 system prompt 的文本。
    """
    if not cluster_id:
        return ''

    from apps.scanner.models import (
        ClusterNode, VM, LXC, Storage, NetworkInterface,
        CephStatus, HAResource, SDNZone, SDNVNet, SDNSubnet,
    )
    from apps.clusters.models import Cluster

    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return ''

    msg_lower = user_message.lower()
    context_parts = []

    # 确定需要加载哪些层
    active_layers = set()
    for layer, keywords in LAYER_KEYWORDS.items():
        if layer == 'summary':
            active_layers.add(layer)
        elif any(kw in msg_lower for kw in keywords):
            active_layers.add(layer)

    # 如果没有匹配到任何关键词，默认加载摘要层
    if len(active_layers) <= 1:
        active_layers.update(['nodes', 'vms', 'containers'])

    # ===== 集群摘要（始终注入） =====
    cutoff = timezone.now() - timedelta(days=7)

    node_count = ClusterNode.objects.filter(
        cluster=cluster, scanned_at__gte=cutoff
    ).values('node_name').distinct().count()

    vm_count = VM.objects.filter(
        node__cluster=cluster, scanned_at__gte=cutoff
    ).values('vmid').distinct().count()

    lxc_count = LXC.objects.filter(
        node__cluster=cluster, scanned_at__gte=cutoff
    ).values('vmid').distinct().count()

    context_parts.append(
        f"## 集群概览: {cluster.name}\n"
        f"- PVE 版本: {cluster.pve_version or '未知'}\n"
        f"- 节点数: {node_count}, 虚拟机: {vm_count}, 容器: {lxc_count}\n"
        f"- 集群状态: {cluster.status}"
    )

    # ===== 节点数据 =====
    if 'nodes' in active_layers:
        latest_nodes = _get_latest_nodes(cluster, cutoff)
        if latest_nodes:
            lines = ["## 节点状态"]
            for n in latest_nodes:
                cpu_pct = f"{n.cpu_load * 100:.1f}%" if n.cpu_load is not None else "N/A"
                mem_pct = f"{n.memory_usage_pct:.1f}%" if n.memory_usage_pct is not None else "N/A"
                mem_total = f"{n.memory_total_mb}MB" if n.memory_total_mb else "N/A"
                disk_total = f"{n.rootfs_total_gb}GB" if n.rootfs_total_gb else "N/A"
                uptime_h = f"{n.uptime_seconds // 3600}h" if n.uptime_seconds else "N/A"
                lines.append(
                    f"- {n.node_name}: 状态={n.status}, CPU={cpu_pct}, "
                    f"内存={mem_pct}({mem_total}), 磁盘={disk_total}, "
                    f"运行={uptime_h}, IP={n.ip_address or 'N/A'}"
                )
            context_parts.append("\n".join(lines))

    # ===== 虚拟机数据 =====
    if 'vms' in active_layers:
        latest_scan_ids = _get_latest_scan_ids(cluster, cutoff)
        if latest_scan_ids:
            vms = VM.objects.filter(
                node__cluster=cluster, scanned_at__gte=cutoff
            ).select_related('node').order_by('-scanned_at', 'vmid')[:50]
            if vms:
                lines = ["## 虚拟机列表"]
                for v in vms:
                    cpu_pct = f"{v.cpu_usage * 100:.1f}%" if v.cpu_usage is not None else "N/A"
                    mem = f"{v.memory_mb}MB" if v.memory_mb else "N/A"
                    lines.append(
                        f"- [{v.vmid}] {v.name}: 状态={v.status}, "
                        f"CPU={cpu_pct}, 内存={mem}, 节点={v.node.node_name}"
                    )
                context_parts.append("\n".join(lines))

    # ===== 容器数据 =====
    if 'containers' in active_layers:
        lxcs = LXC.objects.filter(
            node__cluster=cluster, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'vmid')[:50]
        if lxcs:
            lines = ["## LXC 容器列表"]
            for c in lxcs:
                cpu_pct = f"{c.cpu_usage * 100:.1f}%" if c.cpu_usage is not None else "N/A"
                mem = f"{c.memory_mb}MB" if c.memory_mb else "N/A"
                lines.append(
                    f"- [{c.vmid}] {c.name}: 状态={c.status}, "
                    f"CPU={cpu_pct}, 内存={mem}, 节点={c.node.node_name}"
                )
            context_parts.append("\n".join(lines))

    # ===== 存储数据 =====
    if 'storage' in active_layers:
        storages = Storage.objects.filter(
            node__cluster=cluster, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'storage_name')[:30]
        if storages:
            lines = ["## 存储列表"]
            for s in storages:
                total = f"{s.total_gb}GB" if s.total_gb else "N/A"
                used = f"{s.used_gb}GB" if s.used_gb else "N/A"
                pct = f"{s.used_fraction * 100:.1f}%" if s.used_fraction else "N/A"
                lines.append(
                    f"- {s.storage_name}({s.type}): 已用={used}/{total}({pct}), "
                    f"节点={s.node.node_name}"
                )
            context_parts.append("\n".join(lines))

        # Ceph 状态
        ceph = CephStatus.objects.filter(
            cluster=cluster, scanned_at__gte=cutoff
        ).order_by('-scanned_at').first()
        if ceph:
            total = f"{ceph.total_space_gb}GB" if ceph.total_space_gb else "N/A"
            avail = f"{ceph.total_avail_gb}GB" if ceph.total_avail_gb else "N/A"
            context_parts.append(
                f"## Ceph 状态\n"
                f"- 健康: {ceph.health}, OSD: {ceph.up_osds}/{ceph.total_osds}(up/total)\n"
                f"- 存储池: {ceph.pool_count}, 总空间: {total}, 可用: {avail}"
            )

    # ===== 网络数据 =====
    if 'network' in active_layers:
        nets = NetworkInterface.objects.filter(
            node__cluster=cluster, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'name')[:30]
        if nets:
            lines = ["## 网络接口"]
            for ni in nets:
                speed = f"{ni.speed_mbps}Mbps" if ni.speed_mbps else "N/A"
                lines.append(
                    f"- {ni.name}({ni.type}): 地址={ni.address or 'N/A'}, "
                    f"速率={speed}, 节点={ni.node.node_name}"
                )
            context_parts.append("\n".join(lines))

        # SDN 数据
        sdn_zones = SDNZone.objects.filter(
            cluster=cluster, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:10]
        if sdn_zones:
            lines = ["## SDN 区域"]
            for z in sdn_zones:
                lines.append(f"- {z.zone}: 类型={z.zone_type}, 节点={z.nodes or 'N/A'}")
            context_parts.append("\n".join(lines))

    # ===== HA 数据 =====
    if 'ha' in active_layers:
        ha_resources = HAResource.objects.filter(
            cluster=cluster, scanned_at__gte=cutoff
        ).order_by('-scanned_at', 'sid')[:30]
        if ha_resources:
            lines = ["## HA 高可用资源"]
            for h in ha_resources:
                lines.append(
                    f"- {h.sid}: 类型={h.resource_type}, 状态={h.ha_status}, "
                    f"CRM={h.crm_state}, 组={h.ha_group or 'N/A'}"
                )
            context_parts.append("\n".join(lines))

    return "\n\n".join(context_parts)


def _get_latest_nodes(cluster, cutoff):
    """获取每个节点的最新快照"""
    from apps.scanner.models import ClusterNode
    from django.db.models import Max

    latest_times = (
        ClusterNode.objects.filter(cluster=cluster, scanned_at__gte=cutoff)
        .values('node_name')
        .annotate(latest=Max('scanned_at'))
    )
    nodes = []
    for item in latest_times:
        node = ClusterNode.objects.filter(
            cluster=cluster,
            node_name=item['node_name'],
            scanned_at=item['latest']
        ).first()
        if node:
            nodes.append(node)
    return nodes


def _get_latest_scan_ids(cluster, cutoff):
    """获取最新的扫描任务 ID 列表"""
    from apps.scanner.models import ClusterNode
    return list(
        ClusterNode.objects.filter(cluster=cluster, scanned_at__gte=cutoff)
        .values_list('scan_id', flat=True).distinct()[:5]
    )
