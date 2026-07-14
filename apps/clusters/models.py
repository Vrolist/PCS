import uuid

from django.db import models


def generate_agent_token():
    return uuid.uuid4().hex


class Cluster(models.Model):
    """PVE 集群（公共）"""
    class Status(models.TextChoices):
        PENDING = "pending", "待激活"
        ACTIVE = "active", "活跃"
        ERROR = "error", "错误"
        ARCHIVED = "archived", "已归档"

    name = models.CharField("集群名称", max_length=128)
    description = models.TextField("描述", blank=True)

    # Agent 鉴权
    agent_token = models.CharField("Agent令牌", max_length=64, unique=True,
                                   default=generate_agent_token, db_index=True)

    # PVE 连接信息（用户创建集群时填入，供 Agent 非交互式安装）
    pve_endpoint = models.CharField("PVE API 地址", max_length=256,
                                    help_text="如 https://192.168.1.200:8006")
    pve_token = models.CharField("PVE API Token", max_length=256,
                                 help_text="如 root@pam!monitor:xxxxxxxxxxxx")

    # 集群信息（由 Agent 上报填充）
    status = models.CharField("状态", max_length=32, choices=Status.choices,
                              default=Status.PENDING)
    pve_version = models.CharField("PVE版本", max_length=64, blank=True)
    cluster_id = models.CharField("集群ID", max_length=64, blank=True, db_index=True)

    # 统计概览
    total_nodes = models.IntegerField("节点总数", default=0)
    total_vms = models.IntegerField("虚拟机总数", default=0)
    total_lxc = models.IntegerField("容器总数", default=0)
    total_storage = models.IntegerField("存储总数", default=0)

    # 时间
    last_scanned_at = models.DateTimeField("最后扫描时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "集群"
        verbose_name_plural = "集群"
        ordering = ["-created_at"]

    def regenerate_token(self):
        """重新生成 Agent token"""
        self.agent_token = generate_agent_token()
        self.save(update_fields=["agent_token"])

    def __str__(self):
        return self.name
