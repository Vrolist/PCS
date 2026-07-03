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

    # 磁盘 I/O
    disk_io_delay_ms = models.FloatField("I/O延迟(ms)", null=True, blank=True,
        help_text="节点级 I/O 延迟（毫秒），从 diskstat 汇总")
    diskstat = models.JSONField("磁盘I/O统计", default=list, blank=True,
        help_text='每个磁盘设备的 I/O 统计，如 [{"dev":"sda","read":123,"write":456,"read_ios":10,"write_ios":20,"io_ms":50}]')

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
        unique_together = ("node", "vmid")
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
    has_template = models.BooleanField("是否为模板", default=False)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "LXC容器"
        verbose_name_plural = "LXC容器"
        unique_together = ("node", "vmid")
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
    type = models.CharField("类型", max_length=32, help_text="eth / bond / bridge / vlan")
    active = models.BooleanField("启用", default=True)
    method = models.CharField("寻址方式", max_length=32, blank=True,
                              help_text="static / dhcp")
    address = models.CharField("地址", max_length=64, blank=True, help_text="192.168.1.1/24")
    gateway = models.CharField("网关", max_length=64, blank=True)
    speed_mbps = models.IntegerField("速率(Mbps)", null=True, blank=True)

    # 拓扑关系
    bridge_ports = models.CharField("Bridge端口", max_length=256, blank=True,
        help_text="bridge 包含的物理端口，如 eno1 eno2")
    bond_mode = models.CharField("Bond模式", max_length=32, blank=True,
        help_text="balance-rr / 802.3ad / balance-xor / ...")
    bond_slaves = models.CharField("Bond从接口", max_length=256, blank=True,
        help_text="bond 包含的物理端口，如 eno1 eno2")
    vlan_id = models.IntegerField("VLAN ID", null=True, blank=True)
    mtu = models.IntegerField("MTU", null=True, blank=True)

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


class VMSnapshot(models.Model):
    """VM 快照（从 /nodes/{node}/qemu/{vmid}/snapshot 获取）"""
    vm = models.ForeignKey(VM, on_delete=models.CASCADE, verbose_name="所属VM",
                           related_name="snapshots")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    snapid = models.CharField("快照ID", max_length=128, help_text="PVE 快照标识，如 snap1")
    name = models.CharField("快照名称", max_length=256, blank=True)
    description = models.TextField("描述", blank=True)
    snap_time = models.DateTimeField("快照时间", null=True, blank=True)
    parent = models.CharField("父快照", max_length=128, blank=True,
                              help_text="上一级快照标识，空表示根快照")
    ram = models.BooleanField("保存内存", default=False,
                              help_text="创建快照时是否保存内存状态")
    vmstate = models.BooleanField("保存运行状态", default=False)
    snap_type = models.CharField("快照类型", max_length=32, blank=True,
                                 help_text="如 snapshot / qemu / vztmpl")
    size_mb = models.BigIntegerField("快照大小(MB)", null=True, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "VM快照"
        verbose_name_plural = "VM快照"
        unique_together = ("vm", "snapid")
        ordering = ["-snap_time"]

    def __str__(self):
        return f"{self.vm.name} - {self.snapid}"


class VMConfig(models.Model):
    """VM 详细配置（从 /nodes/{node}/qemu/{vmid}/config 获取）"""
    vm = models.ForeignKey(VM, on_delete=models.CASCADE, verbose_name="所属VM",
                           related_name="configs")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    # 基本配置
    cpu_type = models.CharField("CPU类型", max_length=64, blank=True, help_text="host / qemu65 / ...")
    cpu_cores = models.IntegerField("CPU核心数", null=True, blank=True)
    cpu_sockets = models.IntegerField("CPU插槽数", null=True, blank=True)
    memory_mb = models.IntegerField("内存(MB)", null=True, blank=True)
    balloon_min_mb = models.IntegerField("Balloon下限(MB)", null=True, blank=True)
    os_type = models.CharField("系统类型", max_length=64, blank=True)
    boot_order = models.CharField("启动顺序", max_length=256, blank=True)

    # 存储配置
    scsi_disks = models.JSONField("SCSI磁盘", default=list, blank=True,
        help_text='[{"slot":"scsi0","storage":"local-lvm","size":"32G"}]')
    ide_disks = models.JSONField("IDE设备", default=list, blank=True,
        help_text='[{"slot":"ide0","storage":"local","file":"win10.iso","media":"cdrom"}]')
    net_devices = models.JSONField("网卡", default=list, blank=True,
        help_text='[{"slot":"net0","model":"virtio","bridge":"vmbr0"}]')

    # 高级配置
    agent_enabled = models.BooleanField("QEMU Agent", default=False)
    ha_enabled = models.BooleanField("HA启用", default=False)
    ha_group = models.CharField("HA组", max_length=64, blank=True)
    description = models.TextField("描述", blank=True)
    tags = models.CharField("标签", max_length=256, blank=True)

    # 原始配置 JSON
    raw_config = models.JSONField("原始配置", default=dict, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "VM配置"
        verbose_name_plural = "VM配置"
        unique_together = ("vm",)
        ordering = ["vm"]

    def __str__(self):
        return f"Config: {self.vm.name}"


class LXCConfig(models.Model):
    """LXC 容器详细配置（从 /nodes/{node}/lxc/{vmid}/config 获取）"""
    container = models.ForeignKey(LXC, on_delete=models.CASCADE, verbose_name="所属容器",
                                  related_name="configs")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    # 基本配置
    hostname = models.CharField("主机名", max_length=256, blank=True)
    cpu_cores = models.IntegerField("CPU核心数", null=True, blank=True)
    memory_mb = models.IntegerField("内存(MB)", null=True, blank=True)
    swap_mb = models.IntegerField("Swap(MB)", null=True, blank=True)
    os_type = models.CharField("系统类型", max_length=64, blank=True)

    # 存储配置
    rootfs = models.JSONField("根文件系统", default=dict, blank=True,
        help_text='{"storage":"local-lvm","size":"8G"}')
    mount_points = models.JSONField("挂载点", default=list, blank=True)

    # 网络配置
    net_devices = models.JSONField("网卡", default=list, blank=True,
        help_text='[{"slot":"net0","name":"eth0","bridge":"vmbr0","hwaddr":"...","ip":"dhcp"}]')

    # 高级配置
    ha_enabled = models.BooleanField("HA启用", default=False)
    ha_group = models.CharField("HA组", max_length=64, blank=True)
    description = models.TextField("描述", blank=True)
    tags = models.CharField("标签", max_length=256, blank=True)
    startup_order = models.CharField("启动顺序", max_length=64, blank=True)

    # 原始配置 JSON
    raw_config = models.JSONField("原始配置", default=dict, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "LXC配置"
        verbose_name_plural = "LXC配置"
        unique_together = ("container",)
        ordering = ["container"]

    def __str__(self):
        return f"Config: {self.container.name}"


class HAResource(models.Model):
    """HA 高可用资源"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="ha_resources")

    sid = models.CharField("资源ID", max_length=64, help_text="vm:101 / ct:201")
    resource_type = models.CharField("类型", max_length=16, help_text="vm / ct")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    node_name = models.CharField("所在节点", max_length=128, blank=True)
    state = models.CharField("状态", max_length=32, blank=True,
                             help_text="started / stopped / ...")
    ha_group = models.CharField("HA组", max_length=64, blank=True)
    ha_status = models.CharField("HA状态", max_length=32, blank=True,
                                 help_text="active / inactive / ...")
    crm_state = models.CharField("CRM状态", max_length=32, blank=True,
                                 help_text="started / stopped / ...")
    max_restarts = models.IntegerField("最大重启次数", null=True, blank=True)
    max_shutdown = models.IntegerField("最大关机时间", null=True, blank=True)
    raw_data = models.JSONField("原始数据", default=dict, blank=True)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "HA资源"
        verbose_name_plural = "HA资源"
        ordering = ["sid"]

    def __str__(self):
        return f"{self.sid} ({self.state})"


class SDNZone(models.Model):
    """SDN 区域"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="sdn_zones")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    zone = models.CharField("区域名", max_length=64, db_index=True)
    zone_type = models.CharField("类型", max_length=32, blank=True, help_text="vlan / vxlan / qinq / ...")
    nodes = models.CharField("节点", max_length=256, blank=True, help_text="关联节点列表")

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "SDN区域"
        verbose_name_plural = "SDN区域"
        unique_together = ("cluster", "zone")
        ordering = ["zone"]

    def __str__(self):
        return self.zone


class SDNVNet(models.Model):
    """SDN 虚拟网络"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="sdn_vnets")
    zone = models.ForeignKey(SDNZone, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="所属区域", related_name="vnets")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    vnet = models.CharField("虚拟网络名", max_length=64, db_index=True)
    vnet_type = models.CharField("类型", max_length=32, blank=True, help_text="vlan / vxlan / ...")
    vlan = models.IntegerField("VLAN ID", null=True, blank=True)
    zone_name = models.CharField("区域名", max_length=64, blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "SDN虚拟网络"
        verbose_name_plural = "SDN虚拟网络"
        unique_together = ("cluster", "vnet")
        ordering = ["vnet"]

    def __str__(self):
        return self.vnet


class SDNSubnet(models.Model):
    """SDN 子网"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="sdn_subnets")
    vnet = models.ForeignKey(SDNVNet, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="所属虚拟网络", related_name="subnets")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    subnet = models.CharField("子网", max_length=64, help_text="10.0.0.0/24")
    vnet_name = models.CharField("虚拟网络名", max_length=64, blank=True)
    gateway = models.CharField("网关", max_length=64, blank=True)
    dns_server = models.CharField("DNS服务器", max_length=128, blank=True)
    dns_zone_prefix = models.CharField("DNS区域前缀", max_length=128, blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "SDN子网"
        verbose_name_plural = "SDN子网"
        unique_together = ("cluster", "subnet")
        ordering = ["subnet"]

    def __str__(self):
        return self.subnet


class ReplicationJob(models.Model):
    """PVE 存储复制任务"""
    class Status(models.TextChoices):
        ACTIVE = "active", "活跃"
        DISABLED = "disabled", "禁用"
        ERROR = "error", "错误"
        SYNCING = "syncing", "同步中"

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="replication_jobs")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    job_id = models.CharField("任务ID", max_length=128, db_index=True,
                              help_text="PVE 复制任务标识，如 1-0")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    resource_type = models.CharField("资源类型", max_length=16, blank=True,
                                     help_text="vm / ct")
    source_node = models.CharField("源节点", max_length=128, blank=True)
    target_node = models.CharField("目标节点", max_length=128, blank=True)
    schedule = models.CharField("调度规则", max_length=128, blank=True,
                                help_text="如 */15 (每15分钟)")
    rate_limit = models.IntegerField("速率限制(MB/s)", null=True, blank=True)
    comment = models.TextField("备注", blank=True)
    enabled = models.BooleanField("启用", default=True)

    state = models.CharField("状态", max_length=32, blank=True,
                             help_text="active / disabled / error / syncing")
    last_sync = models.DateTimeField("上次同步时间", null=True, blank=True)
    last_try = models.DateTimeField("上次尝试时间", null=True, blank=True)
    last_duration = models.IntegerField("上次同步耗时(秒)", null=True, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    sync_count = models.IntegerField("成功同步次数", default=0)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "复制任务"
        verbose_name_plural = "复制任务"
        unique_together = ("cluster", "job_id")
        ordering = ["cluster", "job_id"]

    def __str__(self):
        return f"{self.job_id} (VMID {self.vmid})"


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


class BackupStorage(models.Model):
    """备份存储"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="backup_storages")
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所属节点",
                             related_name="backup_storages", null=True, blank=True)
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    storage_name = models.CharField("存储名称", max_length=128)
    storage_type = models.CharField("类型", max_length=32, blank=True,
                                    help_text="local / nfs / cifs / pbs / ...")
    path = models.CharField("路径", max_length=512, blank=True)
    content_types = models.CharField("内容类型", max_length=256, blank=True)
    active = models.BooleanField("活跃", default=True)
    shared = models.BooleanField("共享", default=False)

    total_gb = models.BigIntegerField("总容量(GB)", null=True, blank=True)
    used_gb = models.BigIntegerField("已用(GB)", null=True, blank=True)
    avail_gb = models.BigIntegerField("可用(GB)", null=True, blank=True)
    used_fraction = models.FloatField("使用率", null=True, blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "备份存储"
        verbose_name_plural = "备份存储"
        ordering = ["cluster", "storage_name"]

    def __str__(self):
        return f"{self.storage_name} ({self.storage_type})"


class BackupJob(models.Model):
    """备份任务（从 PVE vzdump 配置获取）"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="backup_jobs")
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所在节点",
                             related_name="backup_jobs", null=True, blank=True)
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    job_id = models.CharField("任务ID", max_length=128, db_index=True,
                              help_text="PVE 备份任务标识，如 vzdump-100-xxx")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    resource_type = models.CharField("资源类型", max_length=16, blank=True,
                                     help_text="vm / ct / all")
    node_name = models.CharField("所在节点", max_length=128, blank=True)
    storage_name = models.CharField("备份存储", max_length=128, blank=True)
    mode = models.CharField("模式", max_length=32, blank=True,
                            help_text="snapshot / suspend / stop")
    schedule = models.CharField("调度规则", max_length=128, blank=True,
                                help_text="cron 表达式，如 '02:00'")
    retention = models.CharField("保留策略", max_length=64, blank=True,
                                 help_text="keep-last=3, keep-daily=7, ...")
    enabled = models.BooleanField("启用", default=True)
    compress = models.CharField("压缩", max_length=32, blank=True,
                                help_text="zstd / lzo / gzip / 0")
    notes = models.TextField("备注", blank=True)

    last_run = models.DateTimeField("上次执行", null=True, blank=True)
    last_status = models.CharField("上次状态", max_length=32, blank=True,
                                   help_text="ok / error")
    next_run = models.DateTimeField("下次执行", null=True, blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "备份任务"
        verbose_name_plural = "备份任务"
        unique_together = ("cluster", "job_id")
        ordering = ["cluster", "job_id"]

    def __str__(self):
        return f"{self.job_id} (VMID {self.vmid})"


class BackupHistory(models.Model):
    """备份执行历史（从 PVE 任务历史获取）"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="backup_histories")
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, verbose_name="所在节点",
                             related_name="backup_histories", null=True, blank=True)
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    task_id = models.CharField("任务ID", max_length=128, db_index=True, blank=True,
                               help_text="PVE 任务 UPID")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    resource_type = models.CharField("资源类型", max_length=16, blank=True,
                                     help_text="vm / ct")
    node_name = models.CharField("所在节点", max_length=128, blank=True)
    storage_name = models.CharField("备份存储", max_length=128, blank=True)
    mode = models.CharField("模式", max_length=32, blank=True,
                            help_text="snapshot / suspend / stop")

    status = models.CharField("状态", max_length=32, help_text="ok / error / running")
    started_at = models.DateTimeField("开始时间", null=True, blank=True)
    finished_at = models.DateTimeField("完成时间", null=True, blank=True)
    duration_seconds = models.IntegerField("耗时(秒)", null=True, blank=True)
    size_bytes = models.BigIntegerField("备份大小(字节)", null=True, blank=True)
    filename = models.CharField("文件名", max_length=512, blank=True)
    error_message = models.TextField("错误信息", blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "备份历史"
        verbose_name_plural = "备份历史"
        ordering = ["-started_at"]

    def __str__(self):
        return f"VMID {self.vmid} - {self.status} ({self.started_at})"


class FirewallOptions(models.Model):
    """防火墙选项（集群/节点/VM/CT 各一条，原地更新）"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="firewall_options")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    scope = models.CharField("作用域", max_length=16,
                             help_text="cluster / node / vm / ct")
    node_name = models.CharField("节点名称", max_length=128, blank=True)
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)

    enabled = models.BooleanField("启用防火墙", default=False)
    policy_in = models.CharField("入站策略", max_length=16, default="ACCEPT",
                                 help_text="ACCEPT / DROP / REJECT")
    policy_out = models.CharField("出站策略", max_length=16, default="ACCEPT")
    policy_forward = models.CharField("转发策略", max_length=16, default="ACCEPT",
                                      help_text="仅 nftables 支持 forward 规则")
    log_level_in = models.CharField("入站日志级别", max_length=16, blank=True,
                                    help_text="nolog / info / warning / err / crit")
    log_level_out = models.CharField("出站日志级别", max_length=16, blank=True)
    dhcp = models.BooleanField("DHCP", default=False)
    ipfilter = models.BooleanField("IP过滤", default=False)
    ndp = models.BooleanField("NDP", default=False)
    macfilter = models.BooleanField("MAC过滤", default=False)
    raw_options = models.JSONField("原始选项", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "防火墙选项"
        verbose_name_plural = "防火墙选项"
        unique_together = ("cluster", "scope", "node_name", "vmid")
        ordering = ["scope", "node_name", "vmid"]

    def __str__(self):
        if self.scope == "cluster":
            return f"{self.cluster.name} - 集群防火墙"
        if self.scope == "node":
            return f"节点 {self.node_name} 防火墙"
        return f"{self.scope.upper()} {self.vmid} 防火墙"


class FirewallRule(models.Model):
    """防火墙规则"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="firewall_rules")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    scope = models.CharField("作用域", max_length=16,
                             help_text="cluster / node / vm / ct / group")
    group_name = models.CharField("安全组名", max_length=64, blank=True)
    node_name = models.CharField("节点名称", max_length=128, blank=True)
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)

    pos = models.IntegerField("规则位置", default=0)
    action = models.CharField("动作", max_length=16, help_text="ACCEPT / DROP / REJECT")
    direction = models.CharField("方向", max_length=8, help_text="in / out / forward")
    proto = models.CharField("协议", max_length=16, blank=True, help_text="tcp / udp / icmp")
    source = models.CharField("源地址", max_length=128, blank=True)
    dest = models.CharField("目标地址", max_length=128, blank=True)
    dport = models.CharField("目标端口", max_length=128, blank=True)
    sport = models.CharField("源端口", max_length=128, blank=True)
    comment = models.CharField("备注", max_length=256, blank=True)
    enabled = models.BooleanField("启用", default=True)
    log = models.CharField("日志", max_length=16, blank=True,
                           help_text="nolog / info / warning / err / crit")
    iface = models.CharField("接口", max_length=32, blank=True)
    macro = models.CharField("宏", max_length=64, blank=True)
    raw_rule = models.JSONField("原始规则", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "防火墙规则"
        verbose_name_plural = "防火墙规则"
        unique_together = ("cluster", "scope", "node_name", "vmid", "group_name", "pos")
        ordering = ["scope", "node_name", "vmid", "pos"]

    def __str__(self):
        prefix = f"[{self.direction.upper()}] {self.action}"
        if self.dport:
            prefix += f" :{self.dport}"
        return f"{prefix} ({self.scope})"


class FirewallIPSet(models.Model):
    """防火墙 IPSet 地址池"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="firewall_ipsets")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    scope = models.CharField("作用域", max_length=16, help_text="cluster / vm")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    name = models.CharField("IPSet名称", max_length=64, help_text="如 management / blacklist")
    comment = models.CharField("备注", max_length=256, blank=True)
    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "防火墙IPSet"
        verbose_name_plural = "防火墙IPSet"
        unique_together = ("cluster", "scope", "vmid", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.scope})"


class FirewallIPSetEntry(models.Model):
    """防火墙 IPSet 条目"""
    ipset = models.ForeignKey(FirewallIPSet, on_delete=models.CASCADE,
                              verbose_name="所属IPSet", related_name="entries")

    cidr = models.CharField("IP/CIDR", max_length=64, help_text="如 192.168.1.0/24")
    comment = models.CharField("备注", max_length=256, blank=True)
    nomatch = models.BooleanField("反向匹配", default=False)
    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "IPSet条目"
        verbose_name_plural = "IPSet条目"
        unique_together = ("ipset", "cidr")
        ordering = ["cidr"]

    def __str__(self):
        return f"{self.cidr} ({self.ipset.name})"


class FirewallAlias(models.Model):
    """防火墙别名"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="所属集群",
                                related_name="firewall_aliases")
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL, null=True, blank=True)

    scope = models.CharField("作用域", max_length=16, help_text="cluster / vm")
    vmid = models.IntegerField("VM/CT ID", null=True, blank=True)
    name = models.CharField("别名", max_length=64)
    cidr = models.CharField("IP/CIDR", max_length=128, blank=True,
                            help_text="如 192.168.1.0/24 或 10.0.0.1")
    alias_type = models.CharField("类型", max_length=16, help_text="ip / net / mac")
    comment = models.CharField("备注", max_length=256, blank=True)
    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "防火墙别名"
        verbose_name_plural = "防火墙别名"
        unique_together = ("cluster", "scope", "vmid", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} = {self.cidr}"
