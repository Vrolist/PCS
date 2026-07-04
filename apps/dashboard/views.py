from collections import defaultdict

from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, ScanHistory, DetectionResult


def _user_cluster_ids(user):
    """返回当前用户拥有的集群 ID 列表"""
    return Cluster.objects.filter(user=user).values_list("id", flat=True)


class StatsView(APIView):
    """GET /api/dashboard/stats/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)

        total_clusters = len(cluster_ids)
        cluster_agg = Cluster.objects.filter(id__in=cluster_ids).aggregate(
            total_nodes=Sum("total_nodes"),
            total_vms=Sum("total_vms"),
            total_containers=Sum("total_lxc"),
        )

        online_nodes = ClusterNode.objects.filter(
            cluster_id__in=cluster_ids, status="online",
        ).values("node_name").distinct().count()

        active_alerts = DetectionResult.objects.filter(
            cluster_id__in=cluster_ids, is_resolved=False,
        ).count()

        return Response({
            "total_clusters": total_clusters,
            "total_nodes": cluster_agg["total_nodes"] or 0,
            "online_nodes": online_nodes,
            "total_vms": cluster_agg["total_vms"] or 0,
            "total_containers": cluster_agg["total_containers"] or 0,
            "active_alerts": active_alerts,
        })


class AlertsView(APIView):
    """GET /api/dashboard/alerts/?limit=10"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)
        limit = int(request.query_params.get("limit", 10))

        qs = DetectionResult.objects.filter(cluster_id__in=cluster_ids, is_resolved=False)
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)

        results = qs.select_related("cluster").order_by("-created_at")[:limit]

        data = [
            {
                "id": r.id,
                "title": r.title,
                "severity": r.severity,
                "category": r.category,
                "affected_resource": r.affected_resource,
                "detail": r.detail,
                "created_at": r.created_at,
                "cluster_name": r.cluster.name,
            }
            for r in results
        ]

        return Response(data)


class TrendsView(APIView):
    """GET /api/dashboard/trends/?days=7"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        cluster_filter = request.query_params.get("cluster_id")
        since = timezone.now() - timezone.timedelta(days=days)
        cluster_ids = _user_cluster_ids(request.user)

        qs = ScanHistory.objects.filter(cluster_id__in=cluster_ids, scanned_at__gte=since)
        if cluster_filter:
            qs = qs.filter(cluster_id=cluster_filter)
        histories = qs.order_by("scanned_at")

        # 根据时间范围选择聚合粒度
        # Agent 每 5分钟上报一次，一天约 288 条记录
        if days <= 1:
            fmt = "%m-%d %H:%M"
            bucket_minutes = 10
        elif days <= 3:
            fmt = "%m-%d %H:%M"
            bucket_minutes = 30
        elif days <= 7:
            fmt = "%m-%d %H:00"
            bucket_minutes = 60
        elif days <= 14:
            fmt = "%m-%d %H:00"
            bucket_minutes = 120
        else:
            fmt = "%m-%d %H:00"
            bucket_minutes = 360

        # 按时间桶聚合
        # avg_cpu_usage 已是百分比值（35.0 表示 35%），avg_memory_usage 是 0~1 值
        buckets = defaultdict(lambda: {"cpu_sum": 0.0, "mem_sum": 0.0, "count": 0})
        for h in histories:
            # 将时间对齐到桶
            if bucket_minutes > 60:
                hour = (h.scanned_at.hour // (bucket_minutes // 60)) * (bucket_minutes // 60)
                dt = h.scanned_at.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                minute = (h.scanned_at.minute // bucket_minutes) * bucket_minutes
                dt = h.scanned_at.replace(minute=minute, second=0, microsecond=0)

            date_key = dt.strftime(fmt)
            snapshot = h.snapshot_data or {}
            cpu = snapshot.get("avg_cpu_usage")
            mem = snapshot.get("avg_memory_usage")
            if cpu is not None or mem is not None:
                buckets[date_key]["cpu_sum"] += float(cpu or 0)
                buckets[date_key]["mem_sum"] += float(mem or 0) * 100
                buckets[date_key]["count"] += 1

        dates = []
        cpu_avg = []
        memory_avg = []
        for date_key in sorted(buckets.keys()):
            entry = buckets[date_key]
            if entry["count"] > 0:
                dates.append(date_key)
                cpu_avg.append(round(entry["cpu_sum"] / entry["count"], 1))
                memory_avg.append(round(entry["mem_sum"] / entry["count"], 1))

        return Response({
            "dates": dates,
            "cpu_avg": cpu_avg,
            "memory_avg": memory_avg,
        })


class NodesView(APIView):
    """GET /api/dashboard/nodes/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)

        # 获取用户每个集群下每个节点的最新扫描记录
        from django.db.models import Max

        base_qs = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            base_qs = base_qs.filter(cluster_id=cluster_filter)

        latest = (
            base_qs
            .values("cluster_id", "node_name")
            .annotate(last_scan=Max("scanned_at"))
        )

        node_map = {}
        for item in latest:
            key = (item["cluster_id"], item["node_name"])
            node_map[key] = item["last_scan"]

        if not node_map:
            return Response([])

        # 批量获取最新的节点记录
        nodes = base_qs.select_related("cluster")

        # 按 (cluster_id, node_name, scanned_at) 匹配
        result_map = {}
        for node in nodes:
            key = (node.cluster_id, node.node_name)
            expected_time = node_map.get(key)
            if expected_time and node.scanned_at == expected_time:
                result_map[key] = node

        data = []
        for (cluster_id, node_name), node in result_map.items():
            data.append({
                "name": node.node_name,
                "status": node.status,
                "cpu_load": node.cpu_load,
                "memory_total_mb": node.memory_total_mb,
                "memory_used_mb": node.memory_used_mb,
                "memory_usage_pct": node.memory_usage_pct,
                "rootfs_total_gb": node.rootfs_total_gb,
                "rootfs_used_gb": node.rootfs_used_gb,
                "pve_version": node.pve_version,
                "ip_address": node.ip_address,
                "cluster_name": node.cluster.name,
                "disk_io_delay_ms": node.disk_io_delay_ms,
                "last_scan": node.scanned_at,
            })

        return Response(data)
