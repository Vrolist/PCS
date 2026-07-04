"""定期健康报告 API"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Max, Q, Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import (
    ClusterNode, VM, LXC, Storage, CephStatus, HAResource,
    ScanHistory, DetectionResult, BackupJob, BackupHistory,
)


def _user_cluster_ids(user):
    return list(Cluster.objects.filter(user=user).values_list("id", flat=True))


def _score_node_health(cluster_ids, since):
    """节点健康评分（0-100）：在线率 + I/O 延迟"""
    nodes = ClusterNode.objects.filter(
        cluster_id__in=cluster_ids, scanned_at__gte=since
    ).values("cluster_id", "node_name").annotate(
        last_scan=Max("scanned_at")
    )
    if not nodes:
        return 100, [], 0

    # 获取最新记录
    q = Q()
    for n in nodes:
        q |= Q(cluster_id=n["cluster_id"], node_name=n["node_name"], scanned_at=n["last_scan"])
    latest = ClusterNode.objects.filter(q)

    total = latest.count()
    online = latest.filter(status="online").count()
    online_rate = (online / total * 100) if total else 100

    issues = []
    for n in latest:
        if n.status != "online":
            issues.append({
                "type": "node_offline", "severity": "critical",
                "resource": n.node_name,
                "detail": f"节点 {n.node_name} 离线",
            })
        elif n.disk_io_delay_ms and n.disk_io_delay_ms > 50:
            issues.append({
                "type": "high_io_delay", "severity": "warning",
                "resource": n.node_name,
                "detail": f"节点 {n.node_name} I/O 延迟 {n.disk_io_delay_ms:.0f}ms",
            })

    score = online_rate
    if issues:
        penalty = sum(10 if i["severity"] == "critical" else 3 for i in issues)
        score = max(0, score - penalty)

    return round(score), issues, total


def _score_resource_usage(cluster_ids, since):
    """资源使用评分（0-100）：CPU/内存/存储使用率"""
    nodes = ClusterNode.objects.filter(
        cluster_id__in=cluster_ids, scanned_at__gte=since
    ).values("cluster_id", "node_name").annotate(last_scan=Max("scanned_at"))

    if not nodes:
        return 100, [], 0, 0, 0

    q = Q()
    for n in nodes:
        q |= Q(cluster_id=n["cluster_id"], node_name=n["node_name"], scanned_at=n["last_scan"])
    latest = ClusterNode.objects.filter(q)

    total = latest.count()
    if total == 0:
        return 100, [], 0, 0, 0

    cpu_sum = 0
    mem_sum = 0
    issues = []
    cpu_count = 0
    mem_count = 0

    for n in latest:
        if n.cpu_load is not None:
            cpu_sum += n.cpu_load
            cpu_count += 1
        if n.memory_usage_pct is not None:
            mem_sum += n.memory_usage_pct
            mem_count += 1

        if n.cpu_load and n.cpu_load > 85:
            issues.append({
                "type": "high_cpu", "severity": "warning",
                "resource": n.node_name,
                "detail": f"节点 {n.node_name} CPU 使用率 {n.cpu_load:.1f}%",
            })
        if n.memory_usage_pct and n.memory_usage_pct > 90:
            issues.append({
                "type": "high_memory", "severity": "warning",
                "resource": n.node_name,
                "detail": f"节点 {n.node_name} 内存使用率 {n.memory_usage_pct:.1f}%",
            })

    # 存储
    storages = Storage.objects.filter(
        node__cluster_id__in=cluster_ids, scanned_at__gte=since
    ).values("node__cluster_id", "node__node_name", "storage_name").annotate(
        last_scan=Max("scanned_at")
    )
    storage_issues = []
    if storages:
        sq = Q()
        for s in storages:
            sq |= Q(
                node__cluster_id=s["node__cluster_id"],
                node__node_name=s["node__node_name"],
                storage_name=s["storage_name"],
                scanned_at=s["last_scan"],
            )
        for s in Storage.objects.filter(sq):
            if s.used_fraction and s.used_fraction > 0.9:
                storage_issues.append({
                    "type": "high_storage", "severity": "critical" if s.used_fraction > 0.95 else "warning",
                    "resource": f"{s.node.node_name}/{s.storage_name}",
                    "detail": f"存储 {s.storage_name} 使用率 {s.used_fraction * 100:.1f}%",
                })
    issues.extend(storage_issues)

    avg_cpu = (cpu_sum / cpu_count) if cpu_count else 0
    avg_mem = (mem_sum / mem_count) if mem_count else 0

    # 评分：使用率越低越好，85% 以上扣分
    score = 100
    if avg_cpu > 85:
        score -= (avg_cpu - 85) * 2
    if avg_mem > 85:
        score -= (avg_mem - 85) * 2
    score -= len(storage_issues) * 5
    score = max(0, min(100, round(score)))

    return score, issues, round(avg_cpu, 1), round(avg_mem, 1), len(storage_issues)


def _score_alert_health(cluster_ids, since):
    """告警健康评分（0-100）：未解决告警数量和严重程度"""
    alerts = DetectionResult.objects.filter(
        cluster_id__in=cluster_ids, created_at__gte=since
    )
    total = alerts.count()
    unresolved = alerts.filter(is_resolved=False).count()
    critical = alerts.filter(is_resolved=False, severity="critical").count()
    warning = alerts.filter(is_resolved=False, severity="warning").count()

    issues = []
    for a in alerts.filter(is_resolved=False).order_by("-severity", "-created_at")[:10]:
        issues.append({
            "type": "alert",
            "severity": a.severity,
            "resource": a.affected_resource or a.title,
            "detail": a.title,
        })

    score = 100
    score -= critical * 15
    score -= warning * 5
    score = max(0, min(100, round(score)))

    return score, issues, total, unresolved


def _score_backup_health(cluster_ids):
    """备份健康评分（0-100）：备份任务配置和执行状态"""
    jobs = BackupJob.objects.filter(cluster_id__in=cluster_ids)
    total_jobs = jobs.count()
    if total_jobs == 0:
        return 100, [], 0, 0

    enabled_jobs = jobs.filter(enabled=True).count()
    failed_jobs = jobs.filter(last_status="error").count()

    issues = []
    for j in jobs.filter(last_status="error"):
        issues.append({
            "type": "backup_failed", "severity": "warning",
            "resource": j.job_id,
            "detail": f"备份任务 {j.job_id} 上次执行失败",
        })

    score = 100
    if failed_jobs > 0:
        score -= failed_jobs * 10
    score = max(0, min(100, round(score)))

    return score, issues, total_jobs, enabled_jobs


def _score_completeness(cluster_ids, since):
    """数据完整性评分（0-100）：扫描覆盖率"""
    histories = ScanHistory.objects.filter(cluster_id__in=cluster_ids, scanned_at__gte=since)
    scan_count = histories.count()

    if scan_count == 0:
        return 0, 0

    # 计算天数跨度
    earliest = histories.order_by("scanned_at").first()
    latest = histories.order_by("-scanned_at").first()
    if earliest and latest:
        span_days = max(1, (latest.scanned_at - earliest.scanned_at).days)
    else:
        span_days = 1

    # 理想扫描频率：每天 1 次
    expected = span_days
    ratio = min(1.0, scan_count / max(1, expected))

    score = round(ratio * 100)
    return score, scan_count


def _get_trend_data(cluster_ids, days):
    """获取趋势数据，根据时间范围动态选择聚合粒度"""
    since = timezone.now() - timedelta(days=days)
    histories = ScanHistory.objects.filter(
        cluster_id__in=cluster_ids, scanned_at__gte=since
    ).order_by("scanned_at")

    # 根据时间范围选择聚合粒度
    # Agent 每 5分钟上报一次，一天约 288 条记录
    # 目标：保持图表数据点在 50-200 之间，兼顾细节和可读性
    if days <= 1:
        # 1天内：按10分钟聚合（约144个点）
        fmt = "%m-%d %H:%M"
        bucket_minutes = 10
    elif days <= 3:
        # 3天：按30分钟聚合（约144个点）
        fmt = "%m-%d %H:%M"
        bucket_minutes = 30
    elif days <= 7:
        # 7天：按小时聚合（约168个点）
        fmt = "%m-%d %H:00"
        bucket_minutes = 60
    elif days <= 14:
        # 14天：按2小时聚合（约168个点）
        fmt = "%m-%d %H:00"
        bucket_minutes = 120
    else:
        # 30天：按6小时聚合（约120个点）
        fmt = "%m-%d %H:00"
        bucket_minutes = 360

    # 按时间桶聚合
    # avg_cpu_usage 已是百分比值（35.0 表示 35%），avg_memory_usage 是 0~1 值
    buckets = defaultdict(lambda: {"cpu_sum": 0, "mem_sum": 0, "count": 0})
    for h in histories:
        # 将时间对齐到桶
        if bucket_minutes > 60:
            # 按多小时聚合：对齐到整点
            hour = (h.scanned_at.hour // (bucket_minutes // 60)) * (bucket_minutes // 60)
            dt = h.scanned_at.replace(hour=hour, minute=0, second=0, microsecond=0)
        else:
            # 按分钟聚合：对齐到桶边界
            minute = (h.scanned_at.minute // bucket_minutes) * bucket_minutes
            dt = h.scanned_at.replace(minute=minute, second=0, microsecond=0)

        date_key = dt.strftime(fmt)
        snap = h.snapshot_data or {}
        cpu = snap.get("avg_cpu_usage")
        mem = snap.get("avg_memory_usage")
        if cpu is not None:
            buckets[date_key]["cpu_sum"] += float(cpu)
        if mem is not None:
            buckets[date_key]["mem_sum"] += float(mem) * 100
        buckets[date_key]["count"] += 1

    dates = []
    cpu_data = []
    mem_data = []
    for date_key in sorted(buckets.keys()):
        entry = buckets[date_key]
        if entry["count"] > 0:
            dates.append(date_key)
            cpu_data.append(round(entry["cpu_sum"] / entry["count"], 1))
            mem_data.append(round(entry["mem_sum"] / entry["count"], 1))

    return {"dates": dates, "cpu": cpu_data, "memory": mem_data}


def _get_asset_overview(cluster_ids):
    """资产概览 - 使用最新扫描快照数据"""
    # 优先使用最近一次 ScanHistory 的快照数据（数据最准确）
    latest_history = ScanHistory.objects.filter(
        cluster_id__in=cluster_ids
    ).order_by("-scanned_at").first()

    if latest_history and latest_history.snapshot_data:
        snap = latest_history.snapshot_data
        total_vms = snap.get("total_vms", 0)
        total_lxc = snap.get("total_lxc", 0)
        total_storage_gb = snap.get("total_storage_gb", 0)
        used_storage_gb = snap.get("used_storage_gb", 0)

        # running_vms/running_lxc 需要从 VM/LXC 表查询（快照中没有）
        from apps.scanner.models import VM, LXC
        running_vms = VM.objects.filter(node__cluster_id__in=cluster_ids, status="running").count()
        running_lxc = LXC.objects.filter(node__cluster_id__in=cluster_ids, status="running").count()

        # 节点数据从 ClusterNode 最新记录获取
        latest_nodes = ClusterNode.objects.filter(
            cluster_id__in=cluster_ids
        ).values("cluster_id", "node_name").annotate(last_scan=Max("scanned_at"))

        q = Q()
        for n in latest_nodes:
            q |= Q(cluster_id=n["cluster_id"], node_name=n["node_name"], scanned_at=n["last_scan"])
        nodes = ClusterNode.objects.filter(q) if latest_nodes else ClusterNode.objects.none()

        total_nodes = nodes.count()
        online_nodes = nodes.filter(status="online").count()
    else:
        # 无快照数据时，回退到直接查询
        from apps.scanner.models import VM, LXC
        total_vms = VM.objects.filter(node__cluster_id__in=cluster_ids).count()
        running_vms = VM.objects.filter(node__cluster_id__in=cluster_ids, status="running").count()
        total_lxc = LXC.objects.filter(node__cluster_id__in=cluster_ids).count()
        running_lxc = LXC.objects.filter(node__cluster_id__in=cluster_ids, status="running").count()

        latest_storage = Storage.objects.filter(
            node__cluster_id__in=cluster_ids
        ).values("node__cluster_id", "node__node_name", "storage_name").annotate(
            last_scan=Max("scanned_at")
        )
        sq = Q()
        for s in latest_storage:
            sq |= Q(
                node__cluster_id=s["node__cluster_id"],
                node__node_name=s["node__node_name"],
                storage_name=s["storage_name"],
                scanned_at=s["last_scan"],
            )
        storages = Storage.objects.filter(sq) if latest_storage else Storage.objects.none()
        total_storage_gb = sum(s.total_gb or 0 for s in storages)
        used_storage_gb = sum(s.used_gb or 0 for s in storages)

        latest_nodes = ClusterNode.objects.filter(
            cluster_id__in=cluster_ids
        ).values("cluster_id", "node_name").annotate(last_scan=Max("scanned_at"))

        q = Q()
        for n in latest_nodes:
            q |= Q(cluster_id=n["cluster_id"], node_name=n["node_name"], scanned_at=n["last_scan"])
        nodes = ClusterNode.objects.filter(q) if latest_nodes else ClusterNode.objects.none()

        total_nodes = nodes.count()
        online_nodes = nodes.filter(status="online").count()

    return {
        "total_nodes": total_nodes,
        "online_nodes": online_nodes,
        "total_vms": total_vms,
        "running_vms": running_vms,
        "total_lxc": total_lxc,
        "running_lxc": running_lxc,
        "total_storage_gb": round(total_storage_gb, 1),
        "used_storage_gb": round(used_storage_gb, 1),
    }


class HealthReportView(APIView):
    """GET /api/dashboard/health-report/?cluster_id=X&days=7"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 0))
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)

        if cluster_filter:
            cluster_ids = [int(cluster_filter)]

        if not cluster_ids:
            return Response({"error": "no_cluster"}, status=400)

        # 自动探测可用数据范围
        earliest = ScanHistory.objects.filter(
            cluster_id__in=cluster_ids
        ).order_by("scanned_at").first()

        actual_days = 0
        if earliest:
            actual_days = max(1, (timezone.now() - earliest.scanned_at).days)

        if days <= 0:
            # 自动模式
            if actual_days <= 0:
                days = 1
            elif actual_days <= 7:
                days = actual_days
            elif actual_days <= 14:
                days = 7
            else:
                days = 14

        since = timezone.now() - timedelta(days=days)

        # === 5 维评分 ===
        node_score, node_issues, node_count = _score_node_health(cluster_ids, since)
        resource_score, resource_issues, avg_cpu, avg_mem, storage_issue_count = _score_resource_usage(cluster_ids, since)
        alert_score, alert_issues, total_alerts, unresolved_alerts = _score_alert_health(cluster_ids, since)
        backup_score, backup_issues, backup_total, backup_enabled = _score_backup_health(cluster_ids)
        completeness_score, scan_count = _score_completeness(cluster_ids, since)

        # 动态权重：数据完整性为 0 时，分摊到其他维度
        weights = {
            "node": 0.25,
            "resource": 0.25,
            "alert": 0.20,
            "backup": 0.15,
            "completeness": 0.15,
        }
        if completeness_score == 0:
            weights = {"node": 0.30, "resource": 0.30, "alert": 0.25, "backup": 0.15, "completeness": 0.0}

        total_score = round(
            node_score * weights["node"]
            + resource_score * weights["resource"]
            + alert_score * weights["alert"]
            + backup_score * weights["backup"]
            + completeness_score * weights["completeness"]
        )

        # 合并所有 issues
        all_issues = node_issues + resource_issues + alert_issues + backup_issues

        # === 趋势数据 ===
        trends = _get_trend_data(cluster_ids, days)

        # === 资产概览 ===
        assets = _get_asset_overview(cluster_ids)

        # === 数据充足度 ===
        data_adequacy = "sufficient"
        if actual_days < 1:
            data_adequacy = "insufficient"
        elif actual_days < 3:
            data_adequacy = "limited"
        elif actual_days < 7:
            data_adequacy = "moderate"

        return Response({
            "overall_score": total_score,
            "scores": {
                "node": {"score": node_score, "weight": weights["node"]},
                "resource": {"score": resource_score, "weight": weights["resource"]},
                "alert": {"score": alert_score, "weight": weights["alert"]},
                "backup": {"score": backup_score, "weight": weights["backup"]},
                "completeness": {"score": completeness_score, "weight": weights["completeness"]},
            },
            "issues": all_issues,
            "trends": trends,
            "assets": assets,
            "summary": {
                "days": days,
                "actual_days": actual_days,
                "data_adequacy": data_adequacy,
                "scan_count": scan_count,
                "node_count": node_count,
                "avg_cpu": avg_cpu,
                "avg_mem": avg_mem,
                "total_alerts": total_alerts,
                "unresolved_alerts": unresolved_alerts,
                "backup_total": backup_total,
                "backup_enabled": backup_enabled,
                "storage_issue_count": storage_issue_count,
            },
        })
