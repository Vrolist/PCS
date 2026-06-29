import logging
import platform
import time
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import (
    CephStatus,
    ClusterNode,
    LXC,
    NetworkInterface,
    ScanHistory,
    Storage,
    VM,
)

from .models import AgentInstance, ScanTask
from .serializers import (
    AgentHeartbeatSerializer,
    AgentRegisterSerializer,
    AgentTaskSerializer,
    AgentUnregisterSerializer,
    ScanUploadSerializer,
)

logger = logging.getLogger(__name__)


def _verify_agent(serializer_class):
    """从请求中验证 Agent 身份，返回 (agent, error_response)"""
    data = serializer_class().data  # just for type hint
    agent_id = data.get("agent_id")
    if not agent_id:
        return None, Response({"error": "agent_id is required"}, status=400)
    try:
        agent = AgentInstance.objects.get(agent_id=agent_id)
    except AgentInstance.DoesNotExist:
        return None, Response({"error": "Agent not found"}, status=404)
    return agent, None


class AgentRegisterView(APIView):
    """Agent 注册 — 无认证，通过 agent_token 鉴权"""
    permission_classes = [AllowAny]

    def post(self, request):
        ser = AgentRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # 验证 agent_token 对应的集群
        try:
            cluster = Cluster.objects.get(agent_token=d["agent_token"])
        except Cluster.DoesNotExist:
            return Response({"error": "Invalid agent_token"}, status=403)

        # 检查该集群下是否已注册过相同 hostname 的 Agent
        agent = AgentInstance.objects.filter(
            cluster=cluster, hostname=d["hostname"]
        ).first()

        if agent:
            # 已存在则更新
            agent.pve_api_endpoint = d["pve_api_endpoint"]
            agent.scan_interval = d["scan_interval"]
            agent.platform = platform.platform()
            agent.python_version = platform.python_version()
            agent.status = AgentInstance.Status.ONLINE
            agent.last_heartbeat_at = timezone.now()
            agent.save()
        else:
            # 新建
            agent = AgentInstance.objects.create(
                cluster=cluster,
                agent_id=uuid.uuid4().hex,
                version="1.0.0",
                hostname=d["hostname"],
                ip_address=request.META.get("REMOTE_ADDR"),
                platform=platform.platform(),
                python_version=platform.python_version(),
                pve_api_endpoint=d["pve_api_endpoint"],
                scan_interval=d["scan_interval"],
                status=AgentInstance.Status.ONLINE,
                last_heartbeat_at=timezone.now(),
            )

        # 集群状态更新为 active
        if cluster.status == Cluster.Status.PENDING:
            cluster.status = Cluster.Status.ACTIVE
            cluster.save(update_fields=["status"])

        return Response(
            {
                "agent_id": agent.agent_id,
                "scan_interval": agent.scan_interval,
                "status": agent.status,
            },
            status=201,
        )


class AgentHeartbeatView(APIView):
    """Agent 心跳 — 无认证，通过 agent_id 鉴权"""
    permission_classes = [AllowAny]

    def post(self, request):
        ser = AgentHeartbeatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            agent = AgentInstance.objects.get(agent_id=d["agent_id"])
        except AgentInstance.DoesNotExist:
            return Response({"error": "Agent not found"}, status=404)

        agent.last_heartbeat_at = timezone.now()
        agent.status = d["status"]
        agent.current_task = d.get("current_task", "")
        agent.save(update_fields=[
            "last_heartbeat_at", "status", "current_task", "updated_at"
        ])

        return Response({"ok": True})


class ScanUploadView(APIView):
    """扫描数据上传 — 无认证，通过 agent_id 鉴权"""
    permission_classes = [AllowAny]

    def post(self, request):
        ser = ScanUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # 验证 Agent
        try:
            agent = AgentInstance.objects.get(agent_id=d["agent_id"])
        except AgentInstance.DoesNotExist:
            return Response({"error": "Agent not found"}, status=404)

        # 验证集群
        try:
            cluster = Cluster.objects.get(id=d["cluster_id"])
        except Cluster.DoesNotExist:
            return Response({"error": "Cluster not found"}, status=404)

        scanned_at = d["scanned_at"]
        nodes_data = d["nodes"]
        ceph_data = d.get("ceph")

        # 创建扫描任务记录
        # raw_data 需要序列化为 JSON 兼容格式（datetime → str）
        import json
        raw_data_serializable = json.loads(json.dumps(d, default=str))

        scan_task = ScanTask.objects.create(
            agent=agent,
            cluster=cluster,
            task_type="full_scan",
            status=ScanTask.Status.RUNNING,
            total_nodes=len(nodes_data),
            raw_data_size_kb=len(str(d)) // 1024,
            raw_data=raw_data_serializable,
        )

        try:
            with transaction.atomic():
                self._save_nodes(cluster, scan_task, nodes_data, scanned_at)
                if ceph_data:
                    self._save_ceph(cluster, scan_task, ceph_data, scanned_at)
                self._save_scan_history(cluster, scan_task, nodes_data, scanned_at)
                self._update_cluster_stats(cluster, nodes_data)

            # 更新扫描任务状态
            scan_task.status = ScanTask.Status.COMPLETED
            scan_task.completed_at = timezone.now()
            scan_task.duration_seconds = (
                scan_task.completed_at - scan_task.started_at
            ).total_seconds()
            scan_task.save(update_fields=[
                "status", "completed_at", "duration_seconds"
            ])

            # 更新 Agent 统计
            agent.last_scan_at = timezone.now()
            agent.total_scans = F("total_scans") + 1
            agent.current_task = ""
            agent.save(update_fields=["last_scan_at", "total_scans", "current_task"])

            # 更新集群最后扫描时间
            cluster.last_scanned_at = scanned_at
            cluster.pve_version = d["version"]
            cluster.save(update_fields=["last_scanned_at", "pve_version"])

            return Response({"ok": True, "scan_task_id": scan_task.id})

        except Exception as e:
            scan_task.status = ScanTask.Status.FAILED
            scan_task.error_message = str(e)
            scan_task.save(update_fields=["status", "error_message"])
            agent.failed_scans = F("failed_scans") + 1
            agent.error_message = str(e)
            agent.save(update_fields=["failed_scans", "error_message"])
            logger.exception("Scan upload failed")
            return Response({"error": str(e)}, status=500)

    def _save_nodes(self, cluster, scan_task, nodes_data, scanned_at):
        """保存节点及其子资源"""
        for node_data in nodes_data:
            node = ClusterNode.objects.create(
                cluster=cluster,
                scan=scan_task,
                node_name=node_data["name"],
                status=node_data.get("status", "online"),
                pve_version=node_data.get("pve_version", ""),
                kernel_version=node_data.get("kernel_version", ""),
                cpu_model=node_data.get("cpu_model", ""),
                cpu_cores=node_data.get("cpu_cores"),
                cpu_sockets=node_data.get("cpu_sockets"),
                cpu_load=node_data.get("cpu_load"),
                memory_total_mb=node_data.get("memory_total_mb"),
                memory_used_mb=node_data.get("memory_used_mb"),
                memory_free_mb=node_data.get("memory_free_mb"),
                memory_usage_pct=node_data.get("memory_usage_pct"),
                rootfs_total_gb=node_data.get("rootfs_total_gb"),
                rootfs_used_gb=node_data.get("rootfs_used_gb"),
                rootfs_avail_gb=node_data.get("rootfs_avail_gb"),
                swap_total_mb=node_data.get("swap_total_mb"),
                swap_used_mb=node_data.get("swap_used_mb"),
                disk_io_delay_ms=node_data.get("disk_io_delay_ms"),
                diskstat=node_data.get("diskstat", []),
                ip_address=node_data.get("ip_address"),
                mac_address=node_data.get("mac_address", ""),
                is_ceph_node=node_data.get("is_ceph_node", False),
                is_ha_node=node_data.get("is_ha_node", False),
                uptime_seconds=node_data.get("uptime_seconds"),
                scanned_at=scanned_at,
            )

            # VM
            for vm_data in node_data.get("vms", []):
                VM.objects.create(
                    node=node,
                    scan=scan_task,
                    vmid=vm_data["vmid"],
                    name=vm_data.get("name", ""),
                    status=vm_data.get("status", "unknown"),
                    cpu_cores=vm_data.get("cpu_cores"),
                    cpu_sockets=vm_data.get("cpu_sockets"),
                    cpu_usage=vm_data.get("cpu_usage"),
                    memory_mb=vm_data.get("memory_mb"),
                    memory_used_mb=vm_data.get("memory_used_mb"),
                    balloon_min_mb=vm_data.get("balloon_min_mb"),
                    balloon_max_mb=vm_data.get("balloon_max_mb"),
                    disk_gb=vm_data.get("disk_gb"),
                    max_disk_gb=vm_data.get("max_disk_gb"),
                    disk_write_iops=vm_data.get("disk_write_iops"),
                    disk_read_iops=vm_data.get("disk_read_iops"),
                    net_in_bps=vm_data.get("net_in_bps"),
                    net_out_bps=vm_data.get("net_out_bps"),
                    uptime_seconds=vm_data.get("uptime_seconds"),
                    os_type=vm_data.get("os_type", ""),
                    snapshot_count=vm_data.get("snapshot_count", 0),
                    has_template=vm_data.get("has_template", False),
                    tags=vm_data.get("tags", ""),
                    description=vm_data.get("description", ""),
                    scanned_at=scanned_at,
                )

            # LXC
            for lxc_data in node_data.get("containers", []):
                LXC.objects.create(
                    node=node,
                    scan=scan_task,
                    vmid=lxc_data["vmid"],
                    name=lxc_data.get("name", ""),
                    status=lxc_data.get("status", "unknown"),
                    cpu_cores=lxc_data.get("cpu_cores"),
                    cpu_usage=lxc_data.get("cpu_usage"),
                    memory_mb=lxc_data.get("memory_mb"),
                    memory_used_mb=lxc_data.get("memory_used_mb"),
                    swap_mb=lxc_data.get("swap_mb"),
                    swap_used_mb=lxc_data.get("swap_used_mb"),
                    disk_gb=lxc_data.get("disk_gb"),
                    uptime_seconds=lxc_data.get("uptime_seconds"),
                    tags=lxc_data.get("tags", ""),
                    description=lxc_data.get("description", ""),
                    scanned_at=scanned_at,
                )

            # Storage
            for st_data in node_data.get("storages", []):
                Storage.objects.create(
                    node=node,
                    scan=scan_task,
                    storage_name=st_data.get("name", ""),
                    type=st_data.get("type", ""),
                    status="available" if st_data.get("active", True) else "unavailable",
                    active=st_data.get("active", True),
                    used_gb=st_data.get("used_gb"),
                    avail_gb=st_data.get("avail_gb"),
                    total_gb=st_data.get("total_gb"),
                    used_fraction=st_data.get("used_fraction"),
                    content_types=st_data.get("content_types", ""),
                    shared=st_data.get("shared", False),
                    scanned_at=scanned_at,
                )

            # Network
            for net_data in node_data.get("networks", []):
                NetworkInterface.objects.create(
                    node=node,
                    scan=scan_task,
                    name=net_data.get("name", ""),
                    type=net_data.get("type", ""),
                    active=net_data.get("active", True),
                    method=net_data.get("method", ""),
                    address=net_data.get("address", ""),
                    gateway=net_data.get("gateway", ""),
                    speed_mbps=net_data.get("speed_mbps"),
                    scanned_at=scanned_at,
                )

    def _save_ceph(self, cluster, scan_task, ceph_data, scanned_at):
        """保存 Ceph 状态"""
        CephStatus.objects.create(
            cluster=cluster,
            scan=scan_task,
            health=ceph_data.get("health", "UNKNOWN"),
            total_osds=ceph_data.get("total_osds"),
            up_osds=ceph_data.get("up_osds"),
            in_osds=ceph_data.get("in_osds"),
            pool_count=ceph_data.get("pool_count"),
            total_used_gb=ceph_data.get("total_used_gb"),
            total_avail_gb=ceph_data.get("total_avail_gb"),
            total_space_gb=ceph_data.get("total_space_gb"),
            extra_data=ceph_data,
            scanned_at=scanned_at,
        )

    def _save_scan_history(self, cluster, scan_task, nodes_data, scanned_at):
        """保存扫描历史快照"""
        total_vms = sum(len(n.get("vms", [])) for n in nodes_data)
        total_lxc = sum(len(n.get("containers", [])) for n in nodes_data)
        total_storage = sum(len(n.get("storages", [])) for n in nodes_data)

        cpu_loads = [n["cpu_load"] for n in nodes_data if n.get("cpu_load") is not None]
        avg_cpu = round(sum(cpu_loads) / len(cpu_loads), 2) if cpu_loads else 0

        mem_totals = [n["memory_total_mb"] for n in nodes_data if n.get("memory_total_mb")]
        mem_used = [n["memory_used_mb"] for n in nodes_data if n.get("memory_used_mb")]
        total_mem = sum(mem_totals) if mem_totals else 0
        used_mem = sum(mem_used) if mem_used else 0
        avg_mem = round(used_mem / total_mem, 2) if total_mem > 0 else 0

        ScanHistory.objects.create(
            cluster=cluster,
            scan=scan_task,
            snapshot_data={
                "total_nodes": len(nodes_data),
                "total_vms": total_vms,
                "total_lxc": total_lxc,
                "total_storage": total_storage,
                "avg_cpu_usage": avg_cpu,
                "avg_memory_usage": avg_mem,
                "total_memory_mb": total_mem,
                "used_memory_mb": used_mem,
            },
            scanned_at=scanned_at,
        )

    def _update_cluster_stats(self, cluster, nodes_data):
        """更新集群汇总字段"""
        total_vms = sum(len(n.get("vms", [])) for n in nodes_data)
        total_lxc = sum(len(n.get("containers", [])) for n in nodes_data)
        total_storage = sum(len(n.get("storages", [])) for n in nodes_data)
        Cluster.objects.filter(id=cluster.id).update(
            total_nodes=len(nodes_data),
            total_vms=total_vms,
            total_lxc=total_lxc,
            total_storage=total_storage,
        )


class AgentTasksView(APIView):
    """查询下发给 Agent 的任务"""
    permission_classes = [AllowAny]

    def get(self, request):
        agent_id = request.query_params.get("agent_id")
        if not agent_id:
            return Response({"error": "agent_id is required"}, status=400)

        try:
            agent = AgentInstance.objects.get(agent_id=agent_id)
        except AgentInstance.DoesNotExist:
            return Response({"error": "Agent not found"}, status=404)

        # 查询该集群下待执行的任务
        tasks = ScanTask.objects.filter(
            cluster=agent.cluster,
            status__in=[ScanTask.Status.RUNNING],
        ).exclude(agent=agent).order_by("-created_at")[:10]

        return Response(AgentTaskSerializer(tasks, many=True).data)


# ============================================================
# Agent 版本常量（平台侧维护）
# ============================================================

AGENT_LATEST_VERSION = "0.1.0"
AGENT_DOWNLOAD_URL = "https://pypi.org/project/pcs-agent/"
AGENT_CHANGELOG = "初始版本：支持集群扫描、心跳、数据上报"


class AgentUnregisterView(APIView):
    """Agent 卸载通知"""
    permission_classes = [AllowAny]

    def post(self, request):
        ser = AgentUnregisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        agent_id = ser.validated_data["agent_id"]

        try:
            agent = AgentInstance.objects.get(agent_id=agent_id)
        except AgentInstance.DoesNotExist:
            return Response({"error": "Agent not found"}, status=404)

        # 标记为 offline
        agent.status = AgentInstance.Status.OFFLINE
        agent.save(update_fields=["status", "updated_at"])

        return Response({"ok": True})


class AgentVersionView(APIView):
    """查询 Agent 最新版本"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "latest_version": AGENT_LATEST_VERSION,
            "download_url": AGENT_DOWNLOAD_URL,
            "changelog": AGENT_CHANGELOG,
        })


class AgentInstallScriptView(APIView):
    """返回一键安装脚本"""
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        platform_url = request.query_params.get("platform", "")
        uninstall = "uninstall" in request.query_params

        if uninstall:
            script = self._uninstall_script()
        else:
            script = self._install_script(token, platform_url)

        from django.http import HttpResponse
        return HttpResponse(script, content_type="text/plain; charset=utf-8")

    def _install_script(self, token: str, platform_url: str) -> str:
        return f"""#!/bin/bash
set -e

TOKEN="{token}"
PLATFORM_URL="{platform_url}"
AGENT_NAME="pcs-agent"
INSTALL_DIR="/opt/$AGENT_NAME"
CONFIG_DIR="$HOME/.config/$AGENT_NAME"

echo "=============================="
echo "  PVE Cluster Scan Agent"
echo "  安装程序 v0.1.0"
echo "=============================="
echo ""

# 参数检查
if [ -z "$TOKEN" ] || [ -z "$PLATFORM_URL" ]; then
    echo "用法: curl -fsSL '$PLATFORM_URL/api/agent/install.sh?token=<TOKEN>&platform=$PLATFORM_URL' | bash"
    exit 1
fi

# 1. 检测系统
detect_os() {{
    if [ -f /etc/debian_version ]; then
        echo "debian"
    elif [ -f /etc/redhat-release ]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}}

OS=$(detect_os)
echo "检测到系统: $OS"

# 2. 安装依赖
echo "安装系统依赖..."
if [ "$OS" = "debian" ]; then
    apt-get update -qq 2>/dev/null || true
    apt-get install -y -qq python3 python3-pip python3-venv curl 2>/dev/null
elif [ "$OS" = "redhat" ]; then
    yum install -y python3 python3-pip curl 2>/dev/null || true
else
    echo "不支持的系统，请手动安装 python3 和 pip"
    exit 1
fi

# 3. 创建安装目录
echo "创建安装目录: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# 4. 创建虚拟环境
echo "创建 Python 虚拟环境..."
python3 -m venv "$INSTALL_DIR/venv"

# 5. 安装 Agent
echo "安装 $AGENT_NAME..."
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet $AGENT_NAME

# 6. 初始化（注册到平台）
echo "注册 Agent..."
mkdir -p "$CONFIG_DIR"
"$INSTALL_DIR/venv/bin/$AGENT_NAME" init \\
    --platform-url "$PLATFORM_URL" \\
    --token "$TOKEN" \\
    --no-input

# 7. 安装 systemd 服务
echo "安装 systemd 服务..."
cat > /etc/systemd/system/$AGENT_NAME.service << 'EOF'
[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/venv/bin/$AGENT_NAME start --foreground
Restart=always
RestartSec=10
WorkingDirectory=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $AGENT_NAME
systemctl start $AGENT_NAME

# 8. 验证
sleep 2
AGENT_STATUS=$(systemctl is-active $AGENT_NAME 2>/dev/null || echo "unknown")

echo ""
echo "=============================="
echo "  安装完成！"
echo ""
if [ "$AGENT_STATUS" = "active" ]; then
    echo "  状态:    运行中 ✓"
else
    echo "  状态:    $AGENT_STATUS"
    echo "  启动失败? 查看日志: journalctl -u $AGENT_NAME -n 20"
fi
echo ""
echo "  管理命令:"
echo "    查看状态: systemctl status $AGENT_NAME"
echo "    查看日志: journalctl -u $AGENT_NAME -f"
echo "    停止服务: systemctl stop $AGENT_NAME"
echo "    重启服务: systemctl restart $AGENT_NAME"
echo "    卸载:     $AGENT_NAME uninstall"
echo "=============================="
"""

    def _uninstall_script(self) -> str:
        return """#!/bin/bash
set -e

AGENT_NAME="pcs-agent"
INSTALL_DIR="/opt/$AGENT_NAME"
CONFIG_DIR="$HOME/.config/$AGENT_NAME"

echo "=============================="
echo "  PVE Cluster Scan Agent"
echo "  卸载程序"
echo "=============================="
echo ""

# 1. 停止服务
echo "1. 停止服务..."
systemctl stop $AGENT_NAME 2>/dev/null || true

# 2. 禁用开机自启
echo "2. 禁用开机自启..."
systemctl disable $AGENT_NAME 2>/dev/null || true

# 3. 删除 systemd 服务
echo "3. 删除 systemd 服务..."
rm -f /etc/systemd/system/$AGENT_NAME.service
systemctl daemon-reload

# 4. 删除文件
echo "4. 清理文件..."
rm -rf "$INSTALL_DIR"
rm -rf "$CONFIG_DIR"

echo ""
echo "=============================="
echo "  卸载完成！"
echo "=============================="
"""
