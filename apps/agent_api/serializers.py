from rest_framework import serializers

from .models import AgentInstance, ScanTask


class AgentRegisterSerializer(serializers.Serializer):
    """Agent 注册请求"""
    agent_token = serializers.CharField(help_text="集群的 Agent 令牌")
    pve_api_endpoint = serializers.URLField(help_text="PVE API 地址")
    pve_username = serializers.CharField(help_text="PVE 用户名")
    pve_password = serializers.CharField(write_only=True, help_text="PVE 密码")
    hostname = serializers.CharField(help_text="Agent 所在主机名")
    scan_interval = serializers.IntegerField(default=300, help_text="扫描间隔(秒)")
    version = serializers.CharField(required=False, default="0.1.0", help_text="Agent 版本")


class AgentRegisterResponseSerializer(serializers.ModelSerializer):
    """Agent 注册响应"""
    class Meta:
        model = AgentInstance
        fields = ["agent_id", "scan_interval", "status"]


class AgentHeartbeatSerializer(serializers.Serializer):
    """Agent 心跳请求"""
    agent_id = serializers.CharField(help_text="Agent 唯一标识")
    status = serializers.ChoiceField(
        choices=AgentInstance.Status.choices,
        default=AgentInstance.Status.ONLINE,
        help_text="当前状态"
    )
    current_task = serializers.CharField(required=False, default="", allow_blank=True, help_text="当前任务")
    error_message = serializers.CharField(required=False, default="", allow_blank=True, help_text="错误信息")
    version = serializers.CharField(required=False, default="0.0.0", help_text="Agent 版本号")


class ScanUploadSerializer(serializers.Serializer):
    """扫描数据上传请求"""
    agent_id = serializers.CharField(help_text="Agent 唯一标识")
    cluster_id = serializers.CharField(help_text="集群 ID")
    scanned_at = serializers.DateTimeField(help_text="扫描时间")
    version = serializers.CharField(help_text="PVE 版本")
    nodes = serializers.ListField(help_text="节点数据列表")
    ceph = serializers.DictField(required=False, default=None, allow_null=True, help_text="Ceph 状态")
    ha_resources = serializers.ListField(required=False, default=list, help_text="HA 资源列表")


class AgentTaskSerializer(serializers.ModelSerializer):
    """Agent 任务响应"""
    class Meta:
        model = ScanTask
        fields = ["id", "task_type", "status", "created_at"]


class AgentUnregisterSerializer(serializers.Serializer):
    """Agent 卸载请求"""
    agent_id = serializers.CharField(help_text="Agent 唯一标识")


class AgentVersionResponseSerializer(serializers.Serializer):
    """版本查询响应"""
    latest_version = serializers.CharField(help_text="最新版本号")
    download_url = serializers.URLField(help_text="下载地址")
    changelog = serializers.CharField(help_text="更新说明")
