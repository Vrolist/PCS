from django.db import models

from apps.agent_api.models import ScanTask
from apps.clusters.models import Cluster


class ClusterNode(models.Model):
    """PVE 节点"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="nodes")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, verbose_name="扫描任务",
                             null=True, blank=True)

    node_name = models.CharField("节点名称", max_length=128, db_index=True)
    status = models.CharField("状态", max_length=32, default="unknown",
                              help_text="online / offline / unknown")
    pve_version = models.CharField("PVE版本", max_length=64, blank=True)
    kernel_version = models.CharField("内核版本", max_length=64, blank=True)

    # CPU
    cpu_model = models.CharField("CPU型号", max_length=256, blank=True)
    cpu_cores = models.IntegerField("CPU核心数", null=True, blank=True)
    cpu_sockets = models.IntegerField("CPU插槽数", null=True, blank=True)
    cpu_load = models.FloatField("CPU负载(0~1)", null=True, blank=True)

    # 内存
    memory_total_mb = models.BigIntegerField("内存总量(MB)", null=True, blank=True)
    memory_used_mb = models.BigIntegerField("内存已用(MB)", null=True, blank=True)
    memory_free_mb = models.BigIntegerField("内存剩余(MB)", null=True, blank=True)
    memory_usage_pct = models.FloatField("内存使用率(%)", null=True, blank=True)

    # 根分区
    rootfs_total_gb = models.BigIntegerField("根分区总量(GB)", null=True, blank=True)
    rootfs_used_gb = models.BigIntegerField("根分区已用(GB)", null=True, blank=True)
    rootfs_avail_gb = models.BigIntegerField("根分区可用(GB)", null=True, blank=True)

    # Swap
    swap_total_mb = models.BigIntegerField("Swap总量(MB)", null=True, blank=True)
    swap_used_mb = models.BigIntegerField("Swap已用(MB)", null=True, blank=True)

    # 网络
    ip_address = models.GenericIPAddressField("IP地址", null=True, blank=True)
    mac_address = models.CharField("MAC地址", max_length=32, blank=True)

    # 角色
    is_ceph_node = models.BooleanField("参与Ceph", default=False)
    is_ha_node = models.BooleanField("支持HA", default=False)
    uptime_seconds = models.BigIntegerField("运行时长(秒)", null=True, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "集群节点"
        verbose_name_plural = "集群节点"
        unique_together = ("cluster", "node_name", "scanned_at")
        ordering = ["node_name"]

    def __str__(self):
        return f"{self.node_name} ({self.cluster.name})"


class VM(models.Model):
    """虚拟机 (QEMU)"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所属节点",
                             related_name="vms")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    vmid = models.IntegerField("VM ID", db_index=True)
    name = models.CharField("名称", max_length=256)
    status = models.CharField("状态", max_length=32, help_text="running / stopped / paused")

    # CPU
    cpu_cores = models.IntegerField("CPU核心数", null=True, blank=True)
    cpu_sockets = models.IntegerField("CPU插槽数", null=True, blank=True)
    cpu_usage = models.FloatField("CPU使用率", null=True, blank=True)

    # 内存
    memory_mb = models.BigIntegerField("内存(MB)", null=True, blank=True)
    memory_used_mb = models.BigIntegerField("内存已用(MB)", null=True, blank=True)
    balloon_min_mb = models.BigIntegerField("Balloon下限(MB)", null=True, blank=True)
    balloon_max_mb = models.BigIntegerField("Balloon上限(MB)", null=True, blank=True)

    # 磁盘
    disk_gb = models.BigIntegerField("磁盘总量(GB)", null=True, blank=True)
    max_disk_gb = models.BigIntegerField("最大磁盘(GB)", null=True, blank=True)
    disk_write_iops = models.FloatField("磁盘写IOPS", null=True, blank=True)
    disk_read_iops = models.FloatField("磁盘读IOPS", null=True, blank=True)

    # 网络
    net_in_bps = models.BigIntegerField("网络入(bps)", null=True, blank=True)
    net_out_bps = models.BigIntegerField("网络出(bps)", null=True, blank=True)

    uptime_seconds = models.BigIntegerField("运行时长(秒)", null=True, blank=True)
    os_type = models.CharField("操作系统类型", max_length=64, blank=True)

    # 快照
    snapshot_count = models.IntegerField("快照数", default=0)
    has_template = models.BooleanField("是否为模板", default=False)

    tags = models.CharField("标签", max_length=256, blank=True)
    description = models.TextField("描述", blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "虚拟机"
        verbose_name_plural = "虚拟机"
        unique_together = ("node", "vmid", "scanned_at")
        ordering = ["node", "vmid"]

    def __str__(self):
        return f"{self.name} (VM {self.vmid})"


class LXC(models.Model):
    """LXC 容器"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所属节点",
                             related_name="containers")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    vmid = models.IntegerField("容器 ID", db_index=True)
    name = models.CharField("名称", max_length=256)
    status = models.CharField("状态", max_length=32, help_text="running / stopped")

    cpu_cores = models.FloatField("CPU核心数", null=True, blank=True)
    cpu_usage = models.FloatField("CPU使用率", null=True, blank=True)

    memory_mb = models.BigIntegerField("内存(MB)", null=True, blank=True)
    memory_used_mb = models.BigIntegerField("内存已用(MB)", null=True, blank=True)
    swap_mb = models.BigIntegerField("Swap(MB)", null=True, blank=True)
    swap_used_mb = models.BigIntegerField("Swap已用(MB)", null=True, blank=True)

    disk_gb = models.BigIntegerField("磁盘(GB)", null=True, blank=True)
    uptime_seconds = models.BigIntegerField("运行时长(秒)", null=True, blank=True)

    tags = models.CharField("标签", max_length=256, blank=True)
    description = models.TextField("描述", blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "LXC容器"
        verbose_name_plural = "LXC容器"
        unique_together = ("node", "vmid", "scanned_at")
        ordering = ["node", "vmid"]

    def __str__(self):
        return f"{self.name} (CT {self.vmid})"


class Storage(models.Model):
    """存储"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所属节点",
                             related_name="storages")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    storage_name = models.CharField("存储名称", max_length=128)
    type = models.CharField("类型", max_length=64,
                            help_text="dir / nfs / lvm / zfs / rbd / cephfs / ...")
    status = models.CharField("状态", max_length=32, default="available",
                              help_text="available / unavailable")
    active = models.BooleanField("活跃", default=True)

    used_gb = models.BigIntegerField("已用(GB)", null=True, blank=True)
    avail_gb = models.BigIntegerField("可用(GB)", null=True, blank=True)
    total_gb = models.BigIntegerField("总量(GB)", null=True, blank=True)
    used_fraction = models.FloatField("使用率", null=True, blank=True)

    content_types = models.CharField("内容类型", max_length=256, blank=True,
                                     help_text="images,rootdir,vztmpl,backup,iso")
    shared = models.BooleanField("共享存储", default=False)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "存储"
        verbose_name_plural = "存储"
        unique_together = ("node", "storage_name", "scanned_at")
        ordering = ["node", "storage_name"]

    def __str__(self):
        return f"{self.storage_name} ({self.type})"


class NetworkInterface(models.Model):
    """节点网络接口"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所属节点",
                             related_name="interfaces")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField("接口名", max_length=64, help_text="vmbr0 / bond0 / eno1")
    type = models.CharField("类型", max_length=32, help_text="bridge / bond / eth")
    active = models.BooleanField("启用", default=True)
    method = models.CharField("寻址方式", max_length=32, blank=True,
                              help_text="static / dhcp")
    address = models.CharField("地址", max_length=64, blank=True, help_text="192.168.1.1/24")
    gateway = models.CharField("网关", max_length=64, blank=True)
    speed_mbps = models.IntegerField("速率(Mbps)", null=True, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "网络接口"
        verbose_name_plural = "网络接口"
        ordering = ["node", "name"]

    def __str__(self):
        return f"{self.name} ({self.node.node_name})"


class CephStatus(models.Model):
    """Ceph 集群状态快照"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="ceph_statuses")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    health = models.CharField("健康状态", max_length=32,
                              help_text="HEALTH_OK / HEALTH_WARN / HEALTH_ERR")
    total_osds = models.IntegerField("OSD总数", null=True, blank=True)
    up_osds = models.IntegerField("在线OSD", null=True, blank=True)
    in_osds = models.IntegerField("参与OSD", null=True, blank=True)
    pool_count = models.IntegerField("存储池数", null=True, blank=True)

    total_used_gb = models.BigIntegerField("已用空间(GB)", null=True, blank=True)
    total_avail_gb = models.BigIntegerField("可用空间(GB)", null=True, blank=True)
    total_space_gb = models.BigIntegerField("总空间(GB)", null=True, blank=True)

    # Ceph 详细状态 JSON
    extra_data = models.JSONField("扩展数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "Ceph状态"
        verbose_name_plural = "Ceph状态"
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"{self.cluster.name} - {self.health} ({self.scanned_at})"


class ScanHistory(models.Model):
    """每次扫描的快照汇总（用于趋势图表）"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="scan_histories")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    snapshot_data = models.JSONField("快照数据", default=dict, blank=True,
        help_text='{"total_nodes":3,"total_vms":25,"avg_cpu_usage":0.35,...}')

    scanned_at = models.DateTimeField("扫描时间", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "扫描历史"
        verbose_name_plural = "扫描历史"
        ordering = ["-scanned_at"]
        indexes = [
            models.Index(fields=["cluster", "-scanned_at"]),
        ]

    def __str__(self):
        return f"{self.cluster.name} @ {self.scanned_at}"


class DetectionRule(models.Model):
    """自动检测规则（可配置）"""
    class Severity(models.TextChoices):
        INFO = "info", "信息"
        WARNING = "warning", "警告"
        CRITICAL = "critical", "严重"

    class Category(models.TextChoices):
        RESOURCE = "resource", "资源"
        SECURITY = "security", "安全"
        PERFORMANCE = "performance", "性能"
        BACKUP = "backup", "备份"
        HEALTH = "health", "健康"

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                null=True, blank=True, related_name="detection_rules")
    name = models.CharField("规则名称", max_length=128)
    category = models.CharField("分类", max_length=64, choices=Category.choices,
                                default=Category.RESOURCE)
    severity = models.CharField("严重级别", max_length=32, choices=Severity.choices,
                                default=Severity.WARNING)
    condition_config = models.JSONField("条件配置", default=dict,
        help_text='{"field": "cpu_load", "operator": "gt", "value": 0.8}')
    description = models.TextField("描述", blank=True)
    suggestion = models.TextField("修复建议", blank=True)
    is_enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "检测规则"
        verbose_name_plural = "检测规则"

    def __str__(self):
        return f"{self.name} ({self.severity})"


class DetectionResult(models.Model):
    """检测结果"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="detection_results")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)
    rule = models.ForeignKey(DetectionRule, on_delete=models.SET_NULL, null=True, blank=True)

    category = models.CharField("分类", max_length=64)
    severity = models.CharField("严重级别", max_length=32)
    title = models.CharField("标题", max_length=256)
    detail = models.TextField("详情")
    affected_resource = models.CharField("影响资源", max_length=256, blank=True,
                                         help_text="节点/VM/容器的标识")
    suggestion = models.TextField("修复建议", blank=True)
    is_resolved = models.BooleanField("已解决", default=False)
    resolved_at = models.DateTimeField("解决时间", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "检测结果"
        verbose_name_plural = "检测结果"
        ordering = ["-severity", "-created_at"]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
