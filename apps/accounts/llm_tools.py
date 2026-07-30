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
            sockets = f"{n.cpu_sockets}路" if n.cpu_sockets else "N/A"
            freq = f"{n.cpu_mhz:.0f}MHz" if n.cpu_mhz else "N/A"
            hvm = "已启用" if n.cpu_hvm else "未启用"

            line = (
                f"- {n.node_name}: 状态={n.status}\n"
                f"  CPU: 负载={cpu}, 型号={n.cpu_model or '未知'}, "
                f"厂商={n.cpu_vendor or '未知'}, {sockets}×{cores}, 频率={freq}\n"
                f"  虚拟化: VT-x/AMD-V={hvm}, CPU特性={n.cpu_flags or '未知'}\n"
                f"  内核: {n.kernel_version or '未知'}\n"
                f"  内存: {mem_pct}({mem_total}), 磁盘: {disk}, "
                f"运行: {uptime}, IP: {n.ip_address or 'N/A'}"
            )
            lines.append(line)

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

    # ── 工具 9: VM 详细配置 ──

    @tool
    def get_vm_config(vmid: int) -> str:
        """查询指定虚拟机的详细配置，包括CPU类型、磁盘、网卡、启动顺序、QEMU Agent等。vmid为必填参数"""
        from apps.scanner.models import VMConfig

        cutoff = _cutoff()
        cfg = VMConfig.objects.filter(
            vm__node__cluster_id=cluster_id,
            vm__vmid=vmid,
            scanned_at__gte=cutoff,
        ).select_related('vm__node').order_by('-scanned_at').first()

        if not cfg:
            return f"未找到 VMID={vmid} 的配置数据"

        v = cfg.vm
        disks = "\n    ".join(
            f"{d.get('slot','?')}: {d.get('storage','?')} {d.get('size','?')}"
            for d in (cfg.scsi_disks or [])
        ) or "无"
        nets = "\n    ".join(
            f"{n.get('slot','?')}: {n.get('model','?')} → {n.get('bridge','?')}"
            for n in (cfg.net_devices or [])
        ) or "无"
        ide = "\n    ".join(
            f"{d.get('slot','?')}: {d.get('storage','?')} {d.get('file','?')}"
            for d in (cfg.ide_disks or [])
        ) or "无"

        return (
            f"VM [{v.vmid}] {v.name} @ {v.node.node_name}\n"
            f"  CPU: 类型={cfg.cpu_type or '未知'}, {cfg.cpu_sockets or '?'}路×{cfg.cpu_cores or '?'}核\n"
            f"  内存: {cfg.memory_mb or '?'}MB (Balloon下限: {cfg.balloon_min_mb or 'N/A'}MB)\n"
            f"  系统: {cfg.os_type or '未知'}, 启动顺序: {cfg.boot_order or '未知'}\n"
            f"  SCSI 磁盘:\n    {disks}\n"
            f"  IDE 设备:\n    {ide}\n"
            f"  网卡:\n    {nets}\n"
            f"  QEMU Agent: {'启用' if cfg.agent_enabled else '未启用'}\n"
            f"  HA: {'启用' if cfg.ha_enabled else '未启用'}"
        )

    # ── 工具 10: LXC 容器配置 ──

    @tool
    def get_container_config(vmid: int) -> str:
        """查询指定LXC容器的详细配置，包括IP地址、挂载点、根文件系统、特权模式等。vmid为必填参数"""
        from apps.scanner.models import LXCConfig

        cutoff = _cutoff()
        cfg = LXCConfig.objects.filter(
            container__node__cluster_id=cluster_id,
            container__vmid=vmid,
            scanned_at__gte=cutoff,
        ).select_related('container__node').order_by('-scanned_at').first()

        if not cfg:
            return f"未找到 VMID={vmid} 的容器配置数据"

        c = cfg.container
        mounts = "\n    ".join(
            f"{m.get('mp','?')}: {m.get('storage','?')} {m.get('size','?')}"
            for m in (cfg.mount_points or [])
        ) or "无"
        nets = "\n    ".join(
            f"{n.get('slot','?')}: {n.get('name','?')} → {n.get('bridge','?')} ({n.get('ip','dhcp')})"
            for n in (cfg.net_devices or [])
        ) or "无"
        rootfs = cfg.rootfs or {}
        rootfs_str = f"{rootfs.get('storage','?')} {rootfs.get('size','?')}" if rootfs else "未知"

        return (
            f"LXC [{c.vmid}] {c.name} @ {c.node.node_name}\n"
            f"  主机名: {cfg.hostname or '未知'}\n"
            f"  CPU: {cfg.cpu_cores or '?'}核, 内存: {cfg.memory_mb or '?'}MB, Swap: {cfg.swap_mb or '?'}MB\n"
            f"  系统: {cfg.os_type or '未知'}\n"
            f"  根文件系统: {rootfs_str}\n"
            f"  挂载点:\n    {mounts}\n"
            f"  网卡:\n    {nets}\n"
            f"  HA: {'启用(' + cfg.ha_group + ')' if cfg.ha_enabled else '未启用'}\n"
            f"  描述: {cfg.description or '无'}"
        )

    # ── 工具 11: 扫描历史趋势 ──

    @tool
    def get_scan_history(days: int = 7) -> str:
        """查询集群扫描历史趋势数据，用于分析资源使用变化趋势。days参数指定天数（默认7天，最大30天）"""
        from apps.scanner.models import ScanHistory

        days = min(max(days, 1), 30)
        cutoff = timezone.now() - timedelta(days=days)
        history = ScanHistory.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('scanned_at')[:200]

        if not history:
            return "未找到扫描历史数据"

        lines = []
        for h in history:
            d = h.snapshot_data or {}
            ts = h.scanned_at.strftime("%m-%d %H:%M")
            parts = [f"时间={ts}"]
            for k, v in d.items():
                if isinstance(v, (int, float)):
                    parts.append(f"{k}={v}")
                elif isinstance(v, str):
                    parts.append(f"{k}={v}")
            lines.append("  " + ", ".join(parts))

        return f"最近 {days} 天扫描历史（共 {len(lines)} 条，每条代表一次扫描快照）:\n" + "\n".join(lines)

    # ── 工具 12: 检测规则与结果 ──

    @tool
    def get_detection_results(severity: str = "") -> str:
        """查询自动检测规则的执行结果，包括告警、性能问题、安全问题等。可按严重级别筛选（info/warning/critical）"""
        from apps.scanner.models import DetectionResult

        cutoff = _cutoff()
        qs = DetectionResult.objects.filter(
            cluster_id=cluster_id, created_at__gte=cutoff
        ).order_by('-created_at')

        if severity:
            qs = qs.filter(severity=severity)

        results = qs[:30]

        if not results:
            return "未找到检测结果"

        lines = []
        for r in results:
            resolved = "已解决" if r.is_resolved else "未解决"
            lines.append(
                f"- [{r.severity}] {r.title}\n"
                f"  分类={r.category}, 影响资源={r.affected_resource or 'N/A'}, "
                f"状态={resolved}\n"
                f"  详情: {r.detail[:200]}"
                + (f"\n  建议: {r.suggestion[:200]}" if r.suggestion else "")
            )

        return f"检测结果（共 {len(lines)} 条）:\n" + "\n".join(lines)

    # ── 工具 13: 备份历史 ──

    @tool
    def get_backup_history() -> str:
        """查询备份执行历史，包括备份状态、开始/完成时间、存储位置等"""
        from apps.scanner.models import BackupHistory

        cutoff = _cutoff()
        backups = BackupHistory.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-started_at')[:30]

        if not backups:
            return "未找到备份历史数据"

        lines = []
        for b in backups:
            start = b.started_at.strftime("%m-%d %H:%M") if b.started_at else "N/A"
            end = b.finished_at.strftime("%m-%d %H:%M") if b.finished_at else "N/A"
            lines.append(
                f"- [{b.status}] {b.resource_type or ''}:{b.vmid or '?'} "
                f"节点={b.node_name or 'N/A'}, 存储={b.storage_name or 'N/A'}\n"
                f"  模式={b.mode or 'N/A'}, 开始={start}, 完成={end}"
            )

        return f"备份历史（共 {len(lines)} 条）:\n" + "\n".join(lines)

    # ── 工具 14: 复制任务 ──

    @tool
    def get_replication_jobs() -> str:
        """查询存储复制任务的配置和状态，包括源/目标节点、调度规则、速率限制等"""
        from apps.scanner.models import ReplicationJob

        cutoff = _cutoff()
        jobs = ReplicationJob.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:20]

        if not jobs:
            return "未找到复制任务数据"

        lines = []
        for j in jobs:
            enabled = "启用" if j.enabled else "禁用"
            lines.append(
                f"- [{j.status}] {j.job_id}: {j.resource_type or ''}:{j.vmid or '?'}\n"
                f"  {j.source_node or '?'} → {j.target_node or '?'}, "
                f"调度={j.schedule or 'N/A'}, 速率限制={j.rate_limit or 'N/A'}MB/s, {enabled}"
                + (f"\n  备注: {j.comment}" if j.comment else "")
            )

        return f"复制任务（共 {len(lines)} 条）:\n" + "\n".join(lines)

    # ── 工具 15: 防火墙规则 ──

    @tool
    def get_firewall_rules(scope: str = "") -> str:
        """查询防火墙规则，包括动作、方向、协议、端口、源/目标地址等。可按作用域筛选（cluster/node/vm/ct）"""
        from apps.scanner.models import FirewallRule

        cutoff = _cutoff()
        qs = FirewallRule.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('scope', 'pos')

        if scope:
            qs = qs.filter(scope=scope)

        rules = qs[:50]

        if not rules:
            return "未找到防火墙规则数据"

        lines = []
        for r in rules:
            target = ""
            if r.scope == "vm" and r.vmid:
                target = f" VM:{r.vmid}"
            elif r.scope == "ct" and r.vmid:
                target = f" CT:{r.vmid}"
            elif r.node_name:
                target = f" 节点:{r.node_name}"

            lines.append(
                f"[{r.pos}] {r.action} {r.direction} {r.proto or 'any'} "
                f"{r.source or '*'}:{r.sport or '*'} → {r.dest or '*'}:{r.dport or '*'}"
                f"  作用域={r.scope}{target}"
                + (f"  ({r.comment})" if r.comment else "")
            )

        return f"防火墙规则（共 {len(lines)} 条）:\n" + "\n".join(lines)

    # ── 工具 16: 集群任务日志 ──

    @tool
    def get_cluster_tasks() -> str:
        """查询集群任务和日志，包括迁移、HA切换、备份、存储操作等任务的执行状态"""
        from apps.scanner.models import ClusterTask, ClusterLog

        cutoff = _cutoff()
        parts = []

        # 集群任务
        tasks = ClusterTask.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-started_at')[:20]

        if tasks:
            lines = ["-- 集群任务 --"]
            for t in tasks:
                start = t.started_at.strftime("%m-%d %H:%M") if t.started_at else "N/A"
                lines.append(
                    f"  [{t.status}] {t.task_type}: {t.node_name or 'N/A'} "
                    f"退出={t.exit_status or 'N/A'}, 开始={start}"
                    + (f"\n    UPID: {t.upid}" if t.upid else "")
                )
            parts.append("\n".join(lines))

        # 集群日志
        logs = ClusterLog.objects.filter(
            cluster_id=cluster_id, scanned_at__gte=cutoff
        ).order_by('-scanned_at')[:20]

        if logs:
            lines = ["-- 集群日志 --"]
            for lg in logs:
                ts = lg.scanned_at.strftime("%m-%d %H:%M") if lg.scanned_at else "N/A"
                lines.append(
                    f"  [{lg.level}] {lg.message[:120]}  (来源={lg.source or 'N/A'}, 时间={ts})"
                )
            parts.append("\n".join(lines))

        return "\n\n".join(parts) if parts else "未找到集群任务/日志数据"

    # ── 工具 17: Agent 运行状态 ──

    @tool
    def get_agent_status() -> str:
        """查询所有Agent进程的运行状态，包括版本、IP、扫描间隔、心跳时间、总扫描次数等"""
        from apps.agent_api.models import AgentInstance

        agents = AgentInstance.objects.filter(
            cluster_id=cluster_id
        ).order_by('-last_heartbeat')

        if not agents:
            return "未找到Agent数据"

        lines = []
        for a in agents:
            hb = a.last_heartbeat.strftime("%m-%d %H:%M") if a.last_heartbeat else "从未"
            lines.append(
                f"- {a.hostname} [{a.status}]: 版本={a.version}, IP={a.ip_address or 'N/A'}, "
                f"平台={a.platform or 'N/A'}, Python={a.python_version or 'N/A'}\n"
                f"  扫描间隔={a.scan_interval}s, 总扫描={a.total_scans}次, "
                f"最后心跳={hb}, PVE={a.pve_api_endpoint or 'N/A'}"
            )

        return f"Agent 状态（共 {len(lines)} 个）:\n" + "\n".join(lines)

    return [
        get_cluster_summary,
        get_node_status,
        get_vm_list,
        get_container_list,
        get_storage_list,
        get_ceph_status,
        get_network_info,
        get_ha_resources,
        get_vm_config,
        get_container_config,
        get_scan_history,
        get_detection_results,
        get_backup_history,
        get_replication_jobs,
        get_firewall_rules,
        get_cluster_tasks,
        get_agent_status,
    ]