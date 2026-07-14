"""性能关联分析 API — 多维度指标关联与可视化数据

优化策略：
- .only() 限制查询字段，减少 IO
- select_related / Subquery 避免 N+1
- 后端计算 Pearson 相关系数，前端零计算
- 降采样在服务端完成，减少传输数据量
"""
import math
from collections import defaultdict

from django.db.models import Count, Max, OuterRef, Subquery
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode

# 节点时序查询只需要的字段
_NODE_FIELDS = [
    "cluster_id", "node_name", "scanned_at",
    "cpu_load", "memory_usage_pct", "disk_io_delay_ms", "rootfs_used_gb", "rootfs_total_gb",
]
# 快照查询额外需要的字段
_SNAPSHOT_EXTRA = [
    "ip_address", "status",
]


def _all_cluster_ids():
    return list(Cluster.objects.filter(user=user).values_list("id", flat=True))


def _safe(val):
    if val is None:
        return None
    try:
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else round(v, 2)
    except (TypeError, ValueError):
        return None


def _downsample(arr, max_points=300):
    """返回 (step, arr)，step > 1 时需要对 timestamps 等做同样切片"""
    n = len(arr)
    return max(1, n // max_points)


def _pearson(xs, ys):
    """计算两个 (number|null) 数组的 Pearson 相关系数"""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return 0.0
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    sx2 = sum(p[0] ** 2 for p in pairs)
    sy2 = sum(p[1] ** 2 for p in pairs)
    denom = math.sqrt((n * sx2 - sx ** 2) * (n * sy2 - sy ** 2))
    if denom == 0:
        return 0.0
    return round((n * sxy - sx * sy) / denom, 4)


class CorrelationView(APIView):
    """GET /api/dashboard/correlation/?cluster_id=X&days=7"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _all_cluster_ids()

        if not cluster_ids:
            return Response({"node_trends": [], "current": [], "correlation_matrix": []})

        since = timezone.now() - timezone.timedelta(days=days)
        cid_filter = {"cluster_id": cluster_filter} if cluster_filter else {"cluster_id__in": cluster_ids}

        # ── 1. 节点时序 ──
        node_qs = (
            ClusterNode.objects
            .filter(**cid_filter, scanned_at__gte=since)
            .select_related("cluster")
            .only(*_NODE_FIELDS, "cluster__name")
            .order_by("scanned_at")
        )

        node_series = defaultdict(lambda: {
            "node_name": "", "cluster_name": "",
            "timestamps": [], "cpu_load": [], "memory_usage_pct": [],
            "disk_io_delay_ms": [], "rootfs_used_gb": [], "rootfs_total_gb": 0,
        })
        # 顺便缓存 cluster name
        cluster_names = {}

        for node in node_qs:
            key = f"{node.cluster_id}:{node.node_name}"
            s = node_series[key]
            s["node_name"] = node.node_name
            if node.cluster_id not in cluster_names:
                cluster_names[node.cluster_id] = node.cluster.name
            s["cluster_name"] = cluster_names.get(node.cluster_id, "")
            s["timestamps"].append(node.scanned_at.strftime("%m-%d %H:%M"))
            s["cpu_load"].append(_safe(node.cpu_load))
            s["memory_usage_pct"].append(_safe(node.memory_usage_pct))
            s["disk_io_delay_ms"].append(_safe(node.disk_io_delay_ms))
            s["rootfs_used_gb"].append(_safe(node.rootfs_used_gb))
            if node.rootfs_total_gb:
                s["rootfs_total_gb"] = float(node.rootfs_total_gb)

        node_trends = []
        for s in node_series.values():
            step = _downsample(s["timestamps"])
            if step > 1:
                for k in ("timestamps", "cpu_load", "memory_usage_pct", "disk_io_delay_ms", "rootfs_used_gb"):
                    s[k] = s[k][::step]
            node_trends.append(s)

        # ── 2. 当前快照（子查询，避免全表扫描 + Python 过滤）──
        latest_sub = (
            ClusterNode.objects
            .filter(cluster_id=OuterRef("cluster_id"), node_name=OuterRef("node_name"))
            .values("cluster_id", "node_name")
            .annotate(m=Max("scanned_at"))
            .values("m")[:1]
        )
        snapshot_qs = (
            ClusterNode.objects
            .filter(**cid_filter, scanned_at=Subquery(latest_sub))
            .select_related("cluster")
            .annotate(total_vms=Count("vms", distinct=True), total_lxc=Count("containers", distinct=True))
            .only("cluster_id", "node_name", "cpu_load", "memory_usage_pct",
                  "disk_io_delay_ms", "rootfs_used_gb", "rootfs_total_gb",
                  "ip_address", "status")
        )

        current = []
        for node in snapshot_qs:
            current.append({
                "node_name": node.node_name,
                "cluster_name": node.cluster.name,
                "cpu_load": _safe(node.cpu_load),
                "memory_usage_pct": _safe(node.memory_usage_pct),
                "disk_io_delay_ms": _safe(node.disk_io_delay_ms),
                "rootfs_used_gb": _safe(node.rootfs_used_gb),
                "rootfs_total_gb": _safe(node.rootfs_total_gb),
                "total_vms": node.total_vms,
                "total_lxc": node.total_lxc,
                "ip_address": node.ip_address or "",
                "status": node.status,
            })

        # ── 3. 后端计算 Pearson 相关系数 ──
        metric_keys = ["cpu_load", "memory_usage_pct", "disk_io_delay_ms", "rootfs_used_gb"]
        all_series = {k: [] for k in metric_keys}
        for nt in node_trends:
            for k in metric_keys:
                all_series[k].extend(nt[k])

        n_metrics = len(metric_keys)
        corr_matrix = []
        for i in range(n_metrics):
            row = []
            for j in range(n_metrics):
                if i == j:
                    row.append(1.0)
                else:
                    row.append(_pearson(all_series[metric_keys[i]], all_series[metric_keys[j]]))
            corr_matrix.append(row)

        return Response({
            "node_trends": node_trends,
            "current": current,
            "correlation_matrix": corr_matrix,
        })
