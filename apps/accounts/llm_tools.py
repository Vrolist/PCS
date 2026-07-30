"""
PVE 数据查询工具（LangChain Tool Calling）
为 LLM 提供按需查询 PVE 集群数据的能力，替代静态上下文注入。
"""

import logging
from datetime import timedelta

from django.utils import timezone
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _cutoff():
    """7 天数据截止时间"""
    return timezone.now() - timedelta(days=7)


def make_pve_tools(cluster_id: int):
    """
    创建绑定 cluster_id 的 PVE 数据查询工具列表。

    每次调用返回新的工具实例，确保 cluster_id 闭包绑定正确。
    LLM 根据工具名和描述自主决定何时调用哪个工具。
    """

    # ── 工具 1: 集群概览 ──

    @tool
    def get_cluster_summary() -> str:
        """获取集群概览信息，包括PVE版本、节点数、虚拟机数、容器数和集群状态"""
        from apps.clusters.models import Cluster
        from apps.scanner.models import ClusterNode, VM, LXC

        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            return "集群不存在"

        cutoff = _cutoff()
        node_count = ClusterNode.objects.filter(
            cluster=cluster, scanned_at__gte=cutoff
        ).values('node_name').distinct().count()

        vm_count = VM.objects.filter(
            node__cluster=cluster, scanned_at__gte=cutoff
        ).values('vmid').distinct().count()

        lxc_count = LXC.objects.filter(
            node__cluster=cluster, scanned_at__gte=cutoff
        ).values('vmid').distinct().count()

        return (
            f"集群: {cluster.name}\n"
            f"PVE 版本: {cluster.pve_version or '未知'}\n"
            f"状态: {cluster.status}\n"
            f"节点数: {node_count}\n"
            f"虚拟机: {vm_count}\n"
            f"容器: {lxc_count}"
        )

    # ── 工具 2: 节点状态 ──

    @tool
    def get_node_status(node_name: str = "") -> str:
        """查询PVE节点的CPU、内存、磁盘、运行状态等信息。不传node_name时返回所有节点，传入指定节点名则只返回该节点"""
        from apps.scanner.models import ClusterNode
        from django.db.models import Max

        cutoff = _cutoff()
        qs = ClusterNode.objects.filter(cluster_id=cluster_id, scanned_at__gte=cutoff)

        if node_name:
            qs = qs.filter(node_name=node_name)

        latest_times = qs.values('node_name').annotate(latest=Max('scanned_at'))

        lines = []
        for item in latest_times:
            n = ClusterNode.objects.filter(
                cluster_id=cluster_id,
                node_name=item['node_name'],
                scanned_at=item['latest'],
            ).first()
            if not n:
                continue

            cpu = f"{n.cpu_load:.1f}%" if n.cpu_load is not None else "N/A"
            mem_pct = f"{n.memory_usage_pct:.1f}%" if n.memory_usage_pct is not None else "N/A"
            mem_total = f"{n.memory_total_mb}MB" if n.memory_total_mb else "N/A"
            disk = f"{n.rootfs_total_gb}GB" if n.rootfs_total_gb else "N/A"
            uptime = f"{n.uptime_seconds // 3600}h" if n.uptime_seconds else "N/A"
            cores = f"{n.cpu_cores}核" if n.cpu_cores else "N/A"

            lines.append(
                f"- {n.node_name}: 状态={n.status}, CPU={cpu}({cores}), "
                f"内存={mem_pct}({mem_total}), 磁盘={disk}, "
                f"运行={uptime}, IP={n.ip_address or 'N/A'}"
            )

        return "\n".join(lines) if lines else "未找到节点数据"

    # ── 工具 3: 虚拟机列表 ──

    @tool
    def get_vm_list(vmid: int = None) -> str:
        """查询虚拟机列表或指定虚拟机详情。不传vmid时返回所有虚拟机(最多50个)，传入vmid则返回指定虚拟机详情"""
        from apps.scanner.models import VM

        cutoff = _cutoff()
        qs = VM.objects.filter(
            node__cluster_id=cluster_id, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'vmid')

        if vmid is not None:
            qs = qs.filter(vmid=vmid)[:1]
        else:
            qs = qs[:50]

        lines = []
        for v in qs:
            cpu = f"{v.cpu_usage:.1f}%" if v.cpu_usage is not None else "N/A"
            mem = f"{v.memory_mb}MB" if v.memory_mb else "N/A"
            cores = f"{v.cpu_cores}核" if v.cpu_cores else "N/A"
            disk = f"{v.disk_gb}GB" if v.disk_gb else "N/A"
            uptime = f"{v.uptime_seconds // 3600}h" if v.uptime_seconds else "N/A"
            tags = v.tags or "N/A"

            lines.append(
                f"- [{v.vmid}] {v.name}: 状态={v.status}, "
                f"CPU={cpu}({cores}), 内存={mem}, 磁盘={disk}, "
                f"运行={uptime}, 标签={tags}, 节点={v.node.node_name}"
            )

        return "\n".join(lines) if lines else "未找到虚拟机数据"

    # ── 工具 4: 容器列表 ──

    @tool
    def get_container_list(vmid: int = None) -> str:
        """查询LXC容器列表或指定容器详情。不传vmid时返回所有容器(最多50个)，传入vmid则返回指定容器详情"""
        from apps.scanner.models import LXC

        cutoff = _cutoff()
        qs = LXC.objects.filter(
            node__cluster_id=cluster_id, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'vmid')

        if vmid is not None:
            qs = qs.filter(vmid=vmid)[:1]
        else:
            qs = qs[:50]

        lines = []
        for c in qs:
            cpu = f"{c.cpu_usage:.1f}%" if c.cpu_usage is not None else "N/A"
            mem = f"{c.memory_mb}MB" if c.memory_mb else "N/A"
            swap = f"{c.swap_used_mb}MB/{c.swap_mb}MB" if c.swap_mb else "N/A"
            disk = f"{c.disk_gb}GB" if c.disk_gb else "N/A"
            uptime = f"{c.uptime_seconds // 3600}h" if c.uptime_seconds else "N/A"
            tags = c.tags or "N/A"

            lines.append(
                f"- [{c.vmid}] {c.name}: 状态={c.status}, "
                f"CPU={cpu}, 内存={mem}, Swap={swap}, 磁盘={disk}, "
                f"运行={uptime}, 标签={tags}, 节点={c.node.node_name}"
            )

        return "\n".join(lines) if lines else "未找到容器数据"

    # ── 工具 5: 存储列表 ──

    @tool
    def get_storage_list() -> str:
        """查询所有存储的容量和使用情况（最多30条）"""
        from apps.scanner.models import Storage

        cutoff = _cutoff()
        storages = Storage.objects.filter(
            node__cluster_id=cluster_id, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'storage_name')[:30]

        lines = []
        for s in storages:
            total = f"{s.total_gb}GB" if s.total_gb else "N/A"
            used = f"{s.used_gb}GB" if s.used_gb else "N/A"
            pct = f"{s.used_fraction * 100:.1f}%" if s.used_fraction is not None else "N/A"
            shared = "共享" if s.shared else "本地"
            lines.append(
                f"- {s.storage_name}({s.type}): 已用={used}/{total}({pct}), "
                f"{shared}, 节点={s.node.node_name}"
            )

        return "\n".join(lines) if lines else "未找到存储数据"

    # ── 工具 6: Ceph 状态 ──

    @tool
    def get_ceph_status() -> str:
        """查询Ceph集群健康状态、OSD数量和存储池用量"""
        from apps.scanner.models import CephStatus

        cutoff = _cutoff()
        ceph = CephStatus.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at').first()

        if not ceph:
            return "未找到Ceph数据（可能未部署Ceph）"

        total = f"{ceph.total_space_gb}GB" if ceph.total_space_gb else "N/A"
        avail = f"{ceph.total_avail_gb}GB" if ceph.total_avail_gb else "N/A"
        used = f"{ceph.total_used_gb}GB" if ceph.total_used_gb else "N/A"

        return (
            f"健康状态: {ceph.health}\n"
            f"OSD: {ceph.up_osds}/{ceph.total_osds} (在线/总数)\n"
            f"参与OSD: {ceph.in_osds}\n"
            f"存储池数: {ceph.pool_count}\n"
            f"总空间: {total}\n"
            f"已用: {used}\n"
            f"可用: {avail}"
        )

    # ── 工具 7: 网络信息 ──

    @tool
    def get_network_info() -> str:
        """查询网络接口信息（含类型、IP、速率）和SDN虚拟网络配置（区域、VNet、子网）"""
        from apps.scanner.models import NetworkInterface, SDNZone, SDNVNet, SDNSubnet

        cutoff = _cutoff()
        parts = []

        # 网络接口
        nets = NetworkInterface.objects.filter(
            node__cluster_id=cluster_id, scanned_at__gte=cutoff
        ).select_related('node').order_by('-scanned_at', 'name')[:30]

        if nets:
            lines = ["-- 网络接口 --"]
            for ni in nets:
                speed = f"{ni.speed_mbps}Mbps" if ni.speed_mbps else "N/A"
                lines.append(
                    f"  {ni.name}({ni.type}): 地址={ni.address or 'N/A'}, "
                    f"速率={speed}, 节点={ni.node.node_name}"
                )
            parts.append("\n".join(lines))

        # SDN 区域
        zones = SDNZone.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:10]

        if zones:
            lines = ["-- SDN 区域 --"]
            for z in zones:
                lines.append(f"  {z.zone}: 类型={z.zone_type}, 节点={z.nodes or 'N/A'}")
            parts.append("\n".join(lines))

        # SDN VNet
        vnets = SDNVNet.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:20]

        if vnets:
            lines = ["-- SDN 虚拟网络 --"]
            for v in vnets:
                vlan = f"VLAN {v.vlan}" if v.vlan is not None else "N/A"
                lines.append(f"  {v.vnet}: 类型={v.vnet_type}, VLAN={vlan}, 区域={v.zone_name}")
            parts.append("\n".join(lines))

        # SDN 子网
        subnets = SDNSubnet.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:20]

        if subnets:
            lines = ["-- SDN 子网 --"]
            for s in subnets:
                lines.append(
                    f"  {s.subnet}: 网关={s.gateway or 'N/A'}, "
                    f"DNS={s.dns_server or 'N/A'}, VNet={s.vnet_name}"
                )
            parts.append("\n".join(lines))

        return "\n\n".join(parts) if parts else "未找到网络数据"

    # ── 工具 8: HA 资源 ──

    @tool
    def get_ha_resources() -> str:
        """查询HA高可用资源的状态和配置信息"""
        from apps.scanner.models import HAResource

        cutoff = _cutoff()
        ha = HAResource.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at', 'sid')[:30]

        if not ha:
            return "未找到HA资源数据（可能未配置HA）"

        lines = []
        for h in ha:
            lines.append(
                f"- {h.sid}: 类型={h.resource_type}, 状态={h.ha_status}, "
                f"CRM={h.crm_state}, 组={h.ha_group or 'N/A'}, "
                f"所在节点={h.node_name or 'N/A'}"
            )

        return "\n".join(lines)

    return [
        get_cluster_summary,
        get_node_status,
        get_vm_list,
        get_container_list,
        get_storage_list,
        get_ceph_status,
        get_network_info,
        get_ha_resources,
    ]