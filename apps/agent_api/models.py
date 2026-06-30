from django.db import models
from django.utils import timezone

from apps.clusters.models import Cluster


class AgentInstance(models.Model):
    """Agent 进程实例 — 支持多 Agent 部署"""
    class Status(models.TextChoices):
        ONLINE = "online", "在线"
        OFFLINE = "offline", "离线"
        ERROR = "error", "错误"
        PAUSED = "paused", "暂停"

    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name="所属集群", related_name="agents")
    agent_id = models.CharField("Agent ID", max_length=64, unique=True, db_index=True,
                                help_text="Agent自生成唯一标识 (如 hostname+pid)")
    version = models.CharField("Agent版本", max_length=32)
    hostname = models.CharField("主机名", max_length=128)
    ip_address = models.GenericIPAddressField("IP地址", blank=True, null=True)
    platform = models.CharField("平台", max_length=64, blank=True,
                                help_text="Linux x86_64 / Darwin arm64 / ...")
    python_version = models.CharField("Python版本", max_length=32, blank=True)

    # 配置
    pve_api_endpoint = models.CharField("PVE API地址", max_length=256, blank=True,
                                        help_text="如: https://192.168.1.100:8006")
    scan_interval = models.IntegerField("扫描间隔(秒)", default=3600)
    status = models.CharField("状态", max_length=32, choices=Status.choices,
                              default=Status.ONLINE)

    # 心跳
    last_heartbeat_at = models.DateTimeField("最后心跳时间", null=True, blank=True)
    last_scan_at = models.DateTimeField("最后扫描时间", null=True, blank=True)
    current_task = models.CharField("当前任务", max_length=64, blank=True,
                                    help_text="当前正在执行的任务类型")

    # 统计
    total_scans = models.IntegerField("总扫描次数", default=0)
    failed_scans = models.IntegerField("失败次数", default=0)
    error_message = models.TextField("错误信息", blank=True)

    started_at = models.DateTimeField("启动时间", auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent实例"
        verbose_name_plural = "Agent实例"
        ordering = ["-last_heartbeat_at"]

    def __str__(self):
        return f"{self.hostname} ({self.agent_id})"


class ScanTask(models.Model):
    """Agent 的每次扫描任务记录"""
    class Status(models.TextChoices):
        RUNNING = "running", "运行中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"
        PARTIAL = "partial", "部分成功"

    agent = models.ForeignKey(AgentInstance, on_delete=models.CASCADE, verbose_name="Agent",
                              related_name="scans")
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, verbose_name="集群",
                                related_name="scan_tasks")
    task_type = models.CharField("任务类型", max_length=64, default="full_scan",
                                 help_text="full_scan / quick_scan / health_check / ...")
    status = models.CharField("状态", max_length=32, choices=Status.choices,
                              default=Status.RUNNING)

    # 数据概览
    total_nodes = models.IntegerField("节点数", default=0)
    total_vms = models.IntegerField("虚拟机数", default=0)
    total_lxc = models.IntegerField("容器数", default=0)
    total_storages = models.IntegerField("存储数", default=0)
    raw_data_size_kb = models.IntegerField("原始数据大小(KB)", null=True, blank=True)
    raw_data = models.JSONField("原始数据", default=dict, blank=True,
                                help_text="Agent上报的完整JSON数据")

    # 时间
    started_at = models.DateTimeField("开始时间", default=timezone.now)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    duration_seconds = models.FloatField("耗时(秒)", null=True, blank=True)

    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "扫描任务"
        verbose_name_plural = "扫描任务"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["cluster", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.cluster.name} - {self.task_type} ({self.get_status_display()})"
