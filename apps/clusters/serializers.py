"""集群 API 序列化器"""
from rest_framework import serializers

from apps.agent_api.models import AgentInstance

from .models import Cluster


class ClusterListSerializer(serializers.ModelSerializer):
    """集群列表响应"""
    agent_count = serializers.SerializerMethodField()
    online_agents = serializers.SerializerMethodField()

    class Meta:
        model = Cluster
        fields = [
            "id", "name", "description", "status", "pve_version",
            "total_nodes", "total_vms", "total_lxc", "total_storage",
            "agent_count", "online_agents",
            "last_scanned_at", "created_at",
        ]

    def get_agent_count(self, obj):
        return obj.agents.count()

    def get_online_agents(self, obj):
        return obj.agents.filter(status=AgentInstance.Status.ONLINE).count()


class ClusterCreateSerializer(serializers.ModelSerializer):
    """创建集群请求"""
    agent_token = serializers.CharField(read_only=True)

    class Meta:
        model = Cluster
        fields = ["id", "name", "description", "agent_token"]

    def validate_name(self, value):
        user = self.context["request"].user
        if Cluster.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("已存在同名集群")
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ClusterDetailSerializer(serializers.ModelSerializer):
    """集群详情（含 Agent 列表 + 安装命令）"""
    agents = serializers.SerializerMethodField()
    install_command = serializers.SerializerMethodField()

    class Meta:
        model = Cluster
        fields = [
            "id", "name", "description", "status", "agent_token",
            "pve_version", "cluster_id",
            "total_nodes", "total_vms", "total_lxc", "total_storage",
            "agents", "install_command",
            "last_scanned_at", "created_at", "updated_at",
        ]

    def get_agents(self, obj):
        agents = obj.agents.all().order_by("-last_heartbeat_at")
        return AgentBriefSerializer(agents, many=True).data

    def get_install_command(self, obj):
        request = self.context.get("request")
        if request:
            host = request.get_host()
            scheme = "https" if request.is_secure() else "http"
            platform_url = f"{scheme}://{host}"
        else:
            platform_url = "https://your-platform:8000"
        return (
            f"curl -fsSL '{platform_url}/api/agent/install.sh"
            f"?token={obj.agent_token}"
            f"&platform={platform_url}' | bash"
        )


class AgentBriefSerializer(serializers.ModelSerializer):
    """Agent 简要信息"""
    class Meta:
        model = AgentInstance
        fields = [
            "id", "agent_id", "hostname", "status",
            "pve_api_endpoint", "version",
            "total_scans", "error_message",
            "last_heartbeat_at", "created_at",
        ]
