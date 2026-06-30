import logging
import platform
import time
import uuid
from datetime import timedelta
from pathlib import Path

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
    VMConfig,
    LXCConfig,
    HAResource,
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

        # 集群已停用，拒绝注册
        if not cluster.is_active:
            return Response({"error": "Cluster is deactivated, registration rejected"}, status=423)

        # 检查该集群下是否已注册过相同 hostname 的 Agent
        agent = AgentInstance.objects.filter(
            cluster=cluster, hostname=d["hostname"]
        ).first()

        if agent:
            # 已存在则更新
            agent.pve_api_endpoint = d["pve_api_endpoint"]
            agent.scan_interval = d["scan_interval"]
            agent.version = d.get("version", agent.version)
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
                version=d.get("version", "0.1.0"),
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
                "cluster_id": agent.cluster_id,
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
        agent.error_message = d.get("error_message", "")
        agent.save(update_fields=[
            "last_heartbeat_at", "status", "current_task", "error_message", "updated_at"
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

        # 集群已停用，拒绝数据上传
        if not cluster.is_active:
            return Response(
                {"error": "Cluster is deactivated, data upload rejected"},
                status=423,
            )

        scanned_at = d["scanned_at"]
        nodes_data = d["nodes"]
        ceph_data = d.get("ceph")
        ha_data = d.get("ha_resources", [])

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
                if ha_data:
                    self._save_ha(cluster, scan_task, ha_data, scanned_at)
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

            # 清理过期历史数据（事务外，失败不影响上传）
            try:
                self._cleanup_expired(cluster)
            except Exception as e:
                logger.warning(f"清理过期数据失败: {e}")

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

    def _cleanup_expired(self, cluster):
        """清理过期历史数据"""
        now = timezone.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        total = 0

        # 7 天保留：节点/存储/网络/Ceph 快照
        for qs in [
            ClusterNode.objects.filter(cluster=cluster, scanned_at__lt=cutoff_7d),
            Storage.objects.filter(node__cluster=cluster, scanned_at__lt=cutoff_7d),
            NetworkInterface.objects.filter(node__cluster=cluster, scanned_at__lt=cutoff_7d),
            CephStatus.objects.filter(cluster=cluster, scanned_at__lt=cutoff_7d),
        ]:
            count, _ = qs.delete()
            total += count

        # 30 天保留：扫描历史/任务记录
        for qs in [
            ScanHistory.objects.filter(cluster=cluster, scanned_at__lt=cutoff_30d),
            ScanTask.objects.filter(cluster=cluster, started_at__lt=cutoff_30d),
        ]:
            count, _ = qs.delete()
            total += count

        if total > 0:
            logger.info(f"集群 {cluster.name} 清理了 {total} 条过期历史数据")

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

            # VM + VMConfig
            vm_configs = node_data.get("vm_configs", {})
            for vm_data in node_data.get("vms", []):
                vm, _ = VM.objects.update_or_create(
                    node=node, vmid=vm_data["vmid"],
                    defaults={
                        "scan": scan_task,
                        "name": vm_data.get("name", ""),
                        "status": vm_data.get("status", "unknown"),
                        "cpu_cores": vm_data.get("cpu_cores"),
                        "cpu_sockets": vm_data.get("cpu_sockets"),
                        "cpu_usage": vm_data.get("cpu_usage"),
                        "memory_mb": vm_data.get("memory_mb"),
                        "memory_used_mb": vm_data.get("memory_used_mb"),
                        "balloon_min_mb": vm_data.get("balloon_min_mb"),
                        "balloon_max_mb": vm_data.get("balloon_max_mb"),
                        "disk_gb": vm_data.get("disk_gb"),
                        "max_disk_gb": vm_data.get("max_disk_gb"),
                        "disk_write_iops": vm_data.get("disk_write_iops"),
                        "disk_read_iops": vm_data.get("disk_read_iops"),
                        "net_in_bps": vm_data.get("net_in_bps"),
                        "net_out_bps": vm_data.get("net_out_bps"),
                        "uptime_seconds": vm_data.get("uptime_seconds"),
                        "os_type": vm_data.get("os_type", ""),
                        "snapshot_count": vm_data.get("snapshot_count", 0),
                        "has_template": vm_data.get("has_template", False),
                        "tags": vm_data.get("tags", ""),
                        "description": vm_data.get("description", ""),
                        "scanned_at": scanned_at,
                    },
                )
                cfg = vm_configs.get(str(vm_data["vmid"]), {})
                if cfg:
                    VMConfig.objects.update_or_create(
                        vm=vm,
                        defaults={
                            "scan": scan_task,
                            "cpu_type": cfg.get("cpu_type", ""),
                            "cpu_cores": cfg.get("cpu_cores"),
                            "cpu_sockets": cfg.get("cpu_sockets"),
                            "memory_mb": cfg.get("memory_mb"),
                            "balloon_min_mb": cfg.get("balloon_min_mb"),
                            "os_type": cfg.get("os_type", ""),
                            "boot_order": cfg.get("boot_order", ""),
                            "scsi_disks": cfg.get("scsi_disks", []),
                            "ide_disks": cfg.get("ide_disks", []),
                            "net_devices": cfg.get("net_devices", []),
                            "agent_enabled": cfg.get("agent_enabled", False),
                            "description": cfg.get("description", ""),
                            "tags": cfg.get("tags", ""),
                            "raw_config": cfg,
                            "scanned_at": scanned_at,
                        },
                    )

            # LXC + LXCConfig
            lxc_configs = node_data.get("lxc_configs", {})
            for lxc_data in node_data.get("containers", []):
                ct, _ = LXC.objects.update_or_create(
                    node=node, vmid=lxc_data["vmid"],
                    defaults={
                        "scan": scan_task,
                        "name": lxc_data.get("name", ""),
                        "status": lxc_data.get("status", "unknown"),
                        "cpu_cores": lxc_data.get("cpu_cores"),
                        "cpu_usage": lxc_data.get("cpu_usage"),
                        "memory_mb": lxc_data.get("memory_mb"),
                        "memory_used_mb": lxc_data.get("memory_used_mb"),
                        "swap_mb": lxc_data.get("swap_mb"),
                        "swap_used_mb": lxc_data.get("swap_used_mb"),
                        "disk_gb": lxc_data.get("disk_gb"),
                        "uptime_seconds": lxc_data.get("uptime_seconds"),
                        "tags": lxc_data.get("tags", ""),
                        "description": lxc_data.get("description", ""),
                        "has_template": lxc_data.get("has_template", False),
                        "scanned_at": scanned_at,
                    },
                )
                cfg = lxc_configs.get(str(lxc_data["vmid"]), {})
                if cfg:
                    LXCConfig.objects.update_or_create(
                        container=ct,
                        defaults={
                            "scan": scan_task,
                            "hostname": cfg.get("hostname", ""),
                            "cpu_cores": cfg.get("cpu_cores"),
                            "memory_mb": cfg.get("memory_mb"),
                            "swap_mb": cfg.get("swap_mb"),
                            "os_type": cfg.get("os_type", ""),
                            "rootfs": cfg.get("rootfs", {}),
                            "mount_points": cfg.get("mount_points", []),
                            "net_devices": cfg.get("net_devices", []),
                            "description": cfg.get("description", ""),
                            "tags": cfg.get("tags", ""),
                            "startup_order": cfg.get("startup_order", ""),
                            "raw_config": cfg,
                            "scanned_at": scanned_at,
                        },
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

    def _save_ha(self, cluster, scan_task, ha_data, scanned_at):
        """保存 HA 资源"""
        for r in ha_data:
            HAResource.objects.create(
                cluster=cluster,
                sid=r.get("sid", ""),
                resource_type=r.get("type", ""),
                vmid=r.get("vmid"),
                node_name=r.get("node", ""),
                state=r.get("state", ""),
                ha_group=r.get("ha_group", ""),
                ha_status=r.get("ha_status", ""),
                crm_state=r.get("crm_state", ""),
                max_restarts=r.get("max_restarts"),
                max_shutdown=r.get("max_shutdown"),
                raw_data=r.get("raw", {}),
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

AGENT_LATEST_VERSION = "0.2.0"
AGENT_DOWNLOAD_URL = "/api/agent/install.sh"  # 从平台下载
AGENT_CHANGELOG = "v0.2.0: 简化为单文件，零依赖"


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


class AgentPVEInfoView(APIView):
    """根据 agent_token 查询集群的 PVE 连接信息（供 install.sh 调用）"""
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        if not token:
            return Response({"error": "token is required"}, status=400)

        from apps.clusters.models import Cluster
        try:
            cluster = Cluster.objects.get(agent_token=token)
        except Cluster.DoesNotExist:
            return Response({"error": "invalid token"}, status=404)

        if not cluster.is_active:
            return Response({"error": "Cluster is deactivated"}, status=423)

        return Response({
            "pve_endpoint": cluster.pve_endpoint,
            "pve_username": "root@pam",
            "pve_token": cluster.pve_token,
        })


class AgentInstallScriptView(APIView):
    """返回一键安装脚本或 agent.py 源码"""
    permission_classes = [AllowAny]

    def get(self, request):
        # ?agent=1 → 返回 agent.py 源码（供 install.sh 下载）
        if request.query_params.get("agent") == "1":
            return self._agent_source()

        token = request.query_params.get("token", "")
        # platform_url 从请求中自动推导，不再需要参数
        host = request.get_host()
        scheme = "https" if request.is_secure() else "http"
        platform_url = f"{scheme}://{host}"
        uninstall = "uninstall" in request.query_params

        if uninstall:
            script = self._uninstall_script()
        else:
            script = self._install_script(token, platform_url)

        from django.http import HttpResponse
        return HttpResponse(script, content_type="text/plain; charset=utf-8")

    def _agent_source(self):
        """返回 agent.py 源码"""
        from django.http import HttpResponse
        agent_path = Path(__file__).resolve().parent.parent.parent / "agent" / "agent.py"
        if not agent_path.exists():
            return HttpResponse("agent.py not found", status=404)
        return HttpResponse(agent_path.read_text(), content_type="text/x-python; charset=utf-8")

    def _install_script(self, token: str, platform_url: str) -> str:
        return f"""#!/bin/bash
set -e

TOKEN="{token}"
PLATFORM_URL="{platform_url}"
AGENT_NAME="pcs-agent"
INSTALL_DIR="/opt/$AGENT_NAME"

echo "=============================="
echo "  PVE Cluster Scan Agent"
echo "  安装程序 v0.2.0"
echo "=============================="
echo ""

# 参数检查
if [ -z "$TOKEN" ]; then
    echo "用法: curl -fsSL '$PLATFORM_URL/api/agent/install.sh?token=<TOKEN>' | bash"
    exit 1
fi

# 1. 检查 root
if [ "$(id -u)" -ne 0 ]; then
    echo "错误: 需要 root 权限，请使用 sudo"
    exit 1
fi

# 2. 检查 Python3
if ! command -v python3 &>/dev/null; then
    echo "安装 python3..."
    if [ -f /etc/debian_version ]; then
        apt-get update -qq && apt-get install -y -qq python3
    elif [ -f /etc/redhat-release ]; then
        yum install -y python3
    fi
fi

PYTHON=$(command -v python3)
echo "Python: $PYTHON"

# 3. 创建安装目录
mkdir -p "$INSTALL_DIR"

# 3.5 如果已安装，先停止并清理旧 Agent
if [ -f "$INSTALL_DIR/config.env" ]; then
    echo "检测到已安装 Agent，正在清理..."
    OLD_AGENT_ID=$(grep '^agent_id=' "$INSTALL_DIR/config.env" | cut -d'"' -f2 || true)
    systemctl stop $AGENT_NAME 2>/dev/null || true
    if [ -n "$OLD_AGENT_ID" ]; then
        curl -s -X POST "$PLATFORM_URL/api/agent/unregister/" \\
            -H "Content-Type: application/json" \\
            -d "{{
                \\"agent_id\\": \\"$OLD_AGENT_ID\\"
            }}" || true
        echo "已通知平台卸载旧 Agent: $OLD_AGENT_ID"
    fi
fi

# 4. 下载 agent.py
echo "下载 agent..."
curl -fsSL "$PLATFORM_URL/api/agent/install.sh?agent=1" -o "$INSTALL_DIR/agent.py"
chmod +x "$INSTALL_DIR/agent.py"
echo "已下载: $INSTALL_DIR/agent.py"

# 5. 从平台查询 PVE 连接信息
echo "查询 PVE 信息..."
PVE_INFO=$(curl -s "$PLATFORM_URL/api/agent/pve-info/?token=$TOKEN")

PVE_ENDPOINT=$(echo "$PVE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pve_endpoint',''))" 2>/dev/null || true)
PVE_USER=$(echo "$PVE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pve_username','root@pam'))" 2>/dev/null || true)
PVE_TOKEN=$(echo "$PVE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pve_token',''))" 2>/dev/null || true)

if [ -z "$PVE_ENDPOINT" ] || [ -z "$PVE_TOKEN" ]; then
    echo "错误: 无法获取 PVE 信息，请检查 token 是否正确"
    echo "返回: $PVE_INFO"
    exit 1
fi
echo "PVE 地址: $PVE_ENDPOINT"
echo "PVE Token: ${{PVE_TOKEN:0:20}}..."

# 6. 注册到平台
echo "注册到平台..."
HOSTNAME=$(hostname)
REGISTER_RESULT=$(curl -s -X POST "$PLATFORM_URL/api/agent/register/" \\
    -H "Content-Type: application/json" \\
    -d "{{
        \\"agent_token\\": \\"$TOKEN\\",
        \\"pve_api_endpoint\\": \\"$PVE_ENDPOINT\\",
        \\"pve_username\\": \\"$PVE_USER\\",
        \\"pve_password\\": \\"$PVE_TOKEN\\",
        \\"hostname\\": \\"$HOSTNAME\\",
        \\"scan_interval\\": 300,
        \\"version\\": \\"0.2.0\\"
    }}")

AGENT_ID=$(echo "$REGISTER_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_id',''))" 2>/dev/null || true)
CLUSTER_ID=$(echo "$REGISTER_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cluster_id',''))" 2>/dev/null || true)

if [ -z "$AGENT_ID" ] || [ -z "$CLUSTER_ID" ]; then
    echo "注册失败: $REGISTER_RESULT"
    exit 1
fi
echo "注册成功: $AGENT_ID"

# 7. 保存配置
cat > "$INSTALL_DIR/config.env" << CFGEOF
platform_url="$PLATFORM_URL"
agent_token="$TOKEN"
agent_id="$AGENT_ID"
cluster_id="$CLUSTER_ID"
pve_endpoint="$PVE_ENDPOINT"
pve_username="$PVE_USER"
pve_password="$PVE_TOKEN"
scan_interval=300
heartbeat_interval=300
CFGEOF
chmod 600 "$INSTALL_DIR/config.env"
echo "配置已保存: $INSTALL_DIR/config.env"

# 8. 安装 systemd 服务
cat > /etc/systemd/system/$AGENT_NAME.service << SVCEOF
[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart=$PYTHON $INSTALL_DIR/agent.py run
Restart=always
RestartSec=10
WorkingDirectory=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable $AGENT_NAME
systemctl start $AGENT_NAME

# 9. 验证
sleep 2
AGENT_STATUS=$(systemctl is-active $AGENT_NAME 2>/dev/null || echo "unknown")

echo ""
echo "=============================="
echo "  安装完成!"
echo ""
if [ "$AGENT_STATUS" = "active" ]; then
    echo "  状态:     运行中"
else
    echo "  状态:     $AGENT_STATUS"
    echo "  排查:     journalctl -u $AGENT_NAME -n 20"
fi
echo ""
echo "  Agent ID: $AGENT_ID"
echo "  安装目录: $INSTALL_DIR"
echo "  配置文件: $INSTALL_DIR/config.env"
echo "  日志文件: $INSTALL_DIR/agent.log"
echo ""
echo "  管理命令:"
echo "    systemctl status $AGENT_NAME    # 查看状态"
echo "    systemctl restart $AGENT_NAME   # 重启"
echo "    systemctl stop $AGENT_NAME      # 停止"
echo "    journalctl -u $AGENT_NAME -f    # 实时日志"
echo "    curl -fsSL '$PLATFORM_URL/api/agent/install.sh?uninstall' | bash  # 卸载"
echo "=============================="
"""

    def _uninstall_script(self) -> str:
        return """#!/bin/bash
set -e

AGENT_NAME="pcs-agent"
INSTALL_DIR="/opt/$AGENT_NAME"

echo "=============================="
echo "  PVE Cluster Scan Agent"
echo "  卸载程序"
echo "=============================="
echo ""

# 1. 通知平台
if [ -f "$INSTALL_DIR/config.env" ]; then
    AGENT_ID=$(grep '^agent_id=' "$INSTALL_DIR/config.env" | cut -d'"' -f2)
    PLATFORM_URL=$(grep '^platform_url=' "$INSTALL_DIR/config.env" | cut -d'"' -f2)
    if [ -n "$AGENT_ID" ] && [ -n "$PLATFORM_URL" ]; then
        echo "1. 通知平台..."
        curl -s -X POST "$PLATFORM_URL/api/agent/unregister/" \\
            -H "Content-Type: application/json" \\
            -d "{\"agent_id\": \"$AGENT_ID\"}" || true
    fi
fi

# 2. 停止服务
echo "2. 停止服务..."
systemctl stop $AGENT_NAME 2>/dev/null || true
systemctl disable $AGENT_NAME 2>/dev/null || true

# 3. 删除 systemd 服务
echo "3. 删除 systemd 服务..."
rm -f /etc/systemd/system/$AGENT_NAME.service
systemctl daemon-reload

# 4. 删除文件
echo "4. 清理文件..."
rm -rf "$INSTALL_DIR"

echo ""
echo "=============================="
echo "  卸载完成!"
echo "=============================="
"""
