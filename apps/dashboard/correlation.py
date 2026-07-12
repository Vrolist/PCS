"""性能关联分析 API — 多维度指标关联与可视化数据"""
import math
from collections import defaultdict

from django.db.models import Max
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, Storage


def _user_cluster_ids(user):
    return Cluster.objects.filter(user=user).values_list("id", flat=True)


class CorrelationView(APIView):
    """GET /api/dashboard/correlation/?cluster_id=X&days=7

    返回三组数据：
    1. node_trends  — 每节点时序指标（CPU/Memory/DiskIO/RootFS）
    2. current      — 当前快照（每节点最新值，用于散点/雷达图）
    3. storage      — 存储使用趋势
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = list(_user_cluster_ids(request.user))

        if not cluster_ids:
            return Response({"node_trends": [], "current": [], "storage": []})

        since = timezone.now() - timezone.timedelta(days=days)

        # ── 1. 节点时序数据 ──
        node_qs = ClusterNode.objects.filter(
            cluster_id__in=cluster_ids, scanned_at__gte=since,
        ).select_related("cluster")
        if cluster_filter:
            node_qs = node_qs.filter(cluster_id=cluster_filter)

        # 按节点名分组
        node_series = defaultdict(lambda: {
            "node_name": "", "cluster_name": "",
            "timestamps": [], "cpu_load": [], "memory_usage_pct": [],
            "disk_io_delay_ms": [], "rootfs_used_gb": [], "rootfs_total_gb": 0,
        })

        for node in node_qs.order_by("scanned_at"):
            key = f"{node.cluster_id}:{node.node_name}"
            s = node_series[key]
            s["node_name"] = node.node_name
            s["cluster_name"] = node.cluster.name
            ts = node.scanned_at.strftime("%m-%d %H:%M")
            s["timestamps"].append(ts)
            s["cpu_load"].append(_safe_float(node.cpu_load))
            s["memory_usage_pct"].append(_safe_float(node.memory_usage_pct))
            s["disk_io_delay_ms"].append(_safe_float(node.disk_io_delay_ms))
            s["rootfs_used_gb"].append(_safe_float(node.rootfs_used_gb))
            if node.rootfs_total_gb:
                s["rootfs_total_gb"] = float(node.rootfs_total_gb)

        # 对长序列做降采样（最多 300 点）
        node_trends = []
        for s in node_series.values():
            n = len(s["timestamps"])
            step = max(1, n // 300)
            if step > 1:
                s["timestamps"] = s["timestamps"][::step]
                s["cpu_load"] = s["cpu_load"][::step]
                s["memory_usage_pct"] = s["memory_usage_pct"][::step]
                s["disk_io_delay_ms"] = s["disk_io_delay_ms"][::step]
                s["rootfs_used_gb"] = s["rootfs_used_gb"][::step]
            node_trends.append(s)

        # ── 2. 当前快照（每节点最新记录）──
        latest = (
            ClusterNode.objects.filter(cluster_id__in=cluster_ids)
            .values("cluster_id", "node_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        if cluster_filter:
            latest = latest.filter(cluster_id=cluster_filter)

        snapshot_map = {}
        for item in latest:
            snapshot_map[(item["cluster_id"], item["node_name"])] = item["last_scan"]

        current = []
        if snapshot_map:
            nodes = ClusterNode.objects.filter(
                cluster_id__in=cluster_ids,
            ).select_related("cluster")
            if cluster_filter:
                nodes = nodes.filter(cluster_id=cluster_filter)

            for node in nodes:
                key = (node.cluster_id, node.node_name)
                if snapshot_map.get(key) != node.scanned_at:
                    continue

                # 统计该节点 VM/LXC 数量
                vm_count = node.vms.count() if hasattr(node, 'vms') else 0
                lxc_count = node.containers.count() if hasattr(node, 'containers') else 0

                current.append({
                    "node_name": node.node_name,
                    "cluster_name": node.cluster.name,
                    "cpu_load": _safe_float(node.cpu_load),
                    "memory_usage_pct": _safe_float(node.memory_usage_pct),
                    "disk_io_delay_ms": _safe_float(node.disk_io_delay_ms),
                    "rootfs_used_gb": _safe_float(node.rootfs_used_gb),
                    "rootfs_total_gb": _safe_float(node.rootfs_total_gb),
                    "total_vms": vm_count,
                    "total_lxc": lxc_count,
                    "ip_address": node.ip_address or "",
                    "status": node.status,
                })

        # ── 3. 存储趋势 ──
        storage_qs = Storage.objects.filter(
            node__cluster_id__in=cluster_ids, scanned_at__gte=since,
        )
        if cluster_filter:
            storage_qs = storage_qs.filter(node__cluster_id=cluster_filter)

        storage_series = defaultdict(lambda: {
            "storage_name": "", "node_name": "", "type": "",
            "timestamps": [], "used_gb": [], "total_gb": 0, "used_fraction": [],
        })

        for st in storage_qs.order_by("scanned_at"):
            key = f"{st.node_id}:{st.storage_name}"
            s = storage_series[key]
            s["storage_name"] = st.storage_name
            s["node_name"] = st.node.node_name if st.node else ""
            s["type"] = st.type
            ts = st.scanned_at.strftime("%m-%d %H:%M")
            s["timestamps"].append(ts)
            s["used_gb"].append(_safe_float(st.used_gb))
            s["used_fraction"].append(_safe_float(st.used_fraction))
            if st.total_gb:
                s["total_gb"] = float(st.total_gb)

        storage_trends = []
        for s in storage_series.values():
            n = len(s["timestamps"])
            step = max(1, n // 300)
            if step > 1:
                s["timestamps"] = s["timestamps"][::step]
                s["used_gb"] = s["used_gb"][::step]
                s["used_fraction"] = s["used_fraction"][::step]
            storage_trends.append(s)

        return Response({
            "node_trends": node_trends,
            "current": current,
            "storage": storage_trends,
        })


def _safe_float(val):
    if val is None:
        return None
    try:
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else round(v, 2)
    except (TypeError, ValueError):
        return None
