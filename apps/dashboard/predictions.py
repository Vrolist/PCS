"""容量规划与趋势预测 API"""
import math
from collections import defaultdict
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, ScanHistory, Storage


def _all_cluster_ids():
    return Cluster.objects.values_list("id", flat=True)


def _linear_regression(points):
    """最小二乘法线性回归
    points: [(x, y), ...]  x 为天数偏移, y 为指标值
    返回 (slope, intercept)，数据不足返回 (None, None)
    """
    n = len(points)
    if n < 2:
        return None, None
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_x2 = sum(p[0] ** 2 for p in points)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return 0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _classify_trend(slope, threshold=0.1):
    """根据斜率判断趋势"""
    if slope is None:
        return "unknown"
    if abs(slope) < threshold:
        return "stable"
    return "rising" if slope > 0 else "declining"


def _holt_damped(values, alpha=0.3, beta=0.15, phi=0.85, horizon=30):
    """Holt's Damped Trend 指数平滑
    适合基础设施资源监控：趋势会随时间自然衰减，不会无限外推。
    - alpha: 水平平滑系数 (0~1)，越大越跟近期数据
    - beta: 趋势平滑系数 (0~1)，越大趋势越敏感
    - phi: 趋势阻尼系数 (0~1)，越小趋势衰减越快
    返回 (forecasts, level, trend_per_day)
    """
    n = len(values)
    if n < 2:
        return [], values[-1] if values else 0, 0

    # 初始化：水平取第一个值，趋势取前两个值之差
    level = values[0]
    trend = values[1] - values[0]

    # 拟合历史数据
    for i in range(1, n):
        prev_level = level
        level = alpha * values[i] + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - prev_level) + (1 - beta) * phi * trend

    # 预测未来（趋势衰减：phi^h 效应递减）
    forecasts = []
    for h in range(1, horizon + 1):
        damped_sum = sum(phi ** j for j in range(1, h + 1))
        forecasts.append(level + damped_sum * trend)

    return forecasts, level, trend


def _predict_full_date(current_value, capacity, slope, today):
    """预测满载日期"""
    if slope is None or slope <= 0 or capacity <= current_value:
        return None, None
    remaining = capacity - current_value
    days = remaining / slope
    if days > 3650:  # 超过10年不预测
        return None, None
    full_date = today + timedelta(days=days)
    return full_date.strftime("%Y-%m-%d"), round(days)


def _aggregate_daily(histories, fields):
    """按天聚合 ScanHistory 数据
    返回 {date_key: {field: avg_value, ...}, ...}
    """
    daily = defaultdict(lambda: {f: {"sum": 0.0, "cnt": 0} for f in fields})
    for h in histories:
        date_key = h.scanned_at.strftime("%Y-%m-%d")
        snap = h.snapshot_data or {}
        for f in fields:
            val = snap.get(f)
            if val is not None:
                daily[date_key][f]["sum"] += float(val)
                daily[date_key][f]["cnt"] += 1
    # 计算均值
    result = {}
    for date_key in sorted(daily.keys()):
        result[date_key] = {}
        for f in fields:
            entry = daily[date_key][f]
            result[date_key][f] = round(entry["sum"] / entry["cnt"], 2) if entry["cnt"] > 0 else None
    return result


def _build_dimension(daily_data, field, capacity=None, unit="pct", display_multiplier=1):
    """构建单个维度的预测结果
    unit: "pct" 表示百分比, "gb" 表示 GB
    display_multiplier: 显示时的乘数 (如 CPU 0~1 → 100)

    算法选择：
    - 百分比指标（CPU/内存）→ Holt's Damped Trend 指数平滑
        趋势会随时间自然衰减，预测曲线弯曲，不会穿过 0%/100%
    - 容量指标（存储/根分区）→ 短期线性回归（最近 7 个数据点）
        更贴近近期趋势，不会被旧数据带偏，到达容量上限自动截断
    """
    dates = []
    values = []
    for date_key, snap in daily_data.items():
        val = snap.get(field)
        if val is not None:
            dates.append(date_key)
            values.append(val)

    if not dates:
        return {
            "current": None, "trend": "unknown", "slope_per_day": None,
            "days_until_full": None, "predicted_full_date": None,
            "data_points": 0, "history_days": 0,
            "chart": {"dates": [], "values": [], "predicted_dates": [], "predicted_values": []},
        }

    current = values[-1]

    if unit == "pct":
        # ── 百分比指标：Holt's Damped Trend 指数平滑 ──
        horizon = 30
        forecasts, level, trend_val = _holt_damped(values, horizon=horizon)

        # 钳制到物理边界 [0, capacity]
        upper = (capacity / display_multiplier) if capacity else 1.0
        forecasts = [max(0.0, min(upper, f)) for f in forecasts]

        slope_display = round(trend_val * display_multiplier, 3)
        threshold = 0.05
        trend = _classify_trend(trend_val, threshold)

        # 满载预测（用当前趋势斜率估算）
        days_until_full = None
        predicted_full_date = None
        if trend == "rising" and trend_val > 0 and capacity:
            remaining = (capacity / display_multiplier) - current
            if remaining > 0:
                days = remaining / trend_val
                if 0 < days <= 365:
                    predicted_full_date = (timezone.now().date() + timedelta(days=round(days))).strftime("%Y-%m-%d")
                    days_until_full = round(days)

        extend_days = min(days_until_full or 14, horizon)
        predicted_values = [round(f * display_multiplier, 2) for f in forecasts[:extend_days]]

    else:
        # ── 容量指标：Holt's Damped Trend 指数平滑 + 容量上限 ──
        horizon = 30
        forecasts, level, trend_val = _holt_damped(values, alpha=0.25, beta=0.1, phi=0.9, horizon=horizon)

        # 钳制到物理边界 [0, capacity]
        forecasts = [max(0.0, min(capacity or float('inf'), f)) for f in forecasts]

        slope_display = round(trend_val, 3)
        threshold = 0.1
        trend = _classify_trend(trend_val, threshold)

        # 满载预测（用当前趋势斜率估算）
        days_until_full = None
        predicted_full_date = None
        if trend == "rising" and trend_val > 0 and capacity and capacity > current:
            days = (capacity - current) / trend_val
            if 0 < days <= 365:
                predicted_full_date = (timezone.now().date() + timedelta(days=round(days))).strftime("%Y-%m-%d")
                days_until_full = round(days)

        extend_days = min(days_until_full or 14, horizon)
        predicted_values = [round(f, 2) for f in forecasts[:extend_days]]

    # 生成预测日期
    predicted_dates = []
    from datetime import datetime as dt
    base_date = dt.strptime(dates[-1], "%Y-%m-%d")
    for i in range(1, len(predicted_values) + 1):
        future_date = base_date + timedelta(days=i)
        predicted_dates.append(future_date.strftime("%Y-%m-%d"))

    return {
        "current": round(current * display_multiplier, 2),
        "trend": trend,
        "slope_per_day": slope_display,
        "days_until_full": days_until_full,
        "predicted_full_date": predicted_full_date,
        "data_points": len(values),
        "history_days": len(dates),
        "chart": {
            "dates": dates,
            "values": [round(v * display_multiplier, 2) for v in values],
            "predicted_dates": predicted_dates,
            "predicted_values": predicted_values,
        },
    }


def _build_storage_from_tables(cluster_id, days):
    """从 Storage 表按天聚合存储数据（回退方案）"""
    since = timezone.now() - timedelta(days=days)
    storages = Storage.objects.filter(
        node__cluster_id=cluster_id, scanned_at__gte=since
    ).select_related("node").order_by("scanned_at")

    # 先按天分组，每天每个 (节点名, 存储池名) 只取最新一条（去重）
    daily_pools = defaultdict(dict)  # {date_key: {(node_name, storage_name): Storage}}
    for s in storages:
        date_key = s.scanned_at.strftime("%Y-%m-%d")
        pool_key = (s.node.node_name, s.storage_name)
        # 取最新一条（因为按 scanned_at 升序，后面的覆盖前面的）
        daily_pools[date_key][pool_key] = s

    # 再对每天去重后的存储池求和
    dates = []
    used_values = []
    total_values = []
    for date_key in sorted(daily_pools.keys()):
        pools = daily_pools[date_key]
        used = sum(float(p.used_gb or 0) for p in pools.values())
        total = sum(float(p.total_gb or 0) for p in pools.values())
        dates.append(date_key)
        used_values.append(round(used, 2))
        total_values.append(round(total, 2))

    if not dates:
        return None

    # 取最新的 total 作为容量
    total_gb = total_values[-1] if total_values else 0

    current_used = used_values[-1] if used_values else 0

    # Holt's Damped Trend 指数平滑（容量指标用更平滑的参数）
    horizon = 30
    forecasts, level, trend_val = _holt_damped(used_values, alpha=0.25, beta=0.1, phi=0.9, horizon=horizon)
    # 钳制到物理边界 [0, total_gb]
    forecasts = [max(0.0, min(total_gb, f)) for f in forecasts]

    trend = _classify_trend(trend_val, 0.1)

    days_until_full = None
    predicted_full_date = None
    if trend == "rising" and trend_val > 0 and total_gb > current_used:
        days = (total_gb - current_used) / trend_val
        if 0 < days <= 365:
            predicted_full_date = (timezone.now().date() + timedelta(days=round(days))).strftime("%Y-%m-%d")
            days_until_full = round(days)

    # 预测线（趋势衰减 + 容量边界截断）
    extend_days = min(days_until_full or 14, horizon)
    predicted_dates = []
    predicted_values = []
    from datetime import datetime as dt
    base_date = dt.strptime(dates[-1], "%Y-%m-%d")
    for i, f in enumerate(forecasts[:extend_days], 1):
        predicted_dates.append((base_date + timedelta(days=i)).strftime("%Y-%m-%d"))
        predicted_values.append(round(f, 2))

    return {
        "current_used_gb": round(current_used, 2),
        "total_gb": round(total_gb, 2),
        "current_pct": round(current_used / total_gb * 100, 1) if total_gb > 0 else 0,
        "trend": trend,
        "slope_gb_per_day": round(trend_val, 3),
        "days_until_full": days_until_full,
        "predicted_full_date": predicted_full_date,
        "data_points": len(dates),
        "history_days": len(dates),
        "chart": {
            "dates": dates,
            "values": used_values,
            "predicted_dates": predicted_dates,
            "predicted_values": predicted_values,
        },
    }


def _build_rootfs_from_tables(cluster_id, days):
    """从 ClusterNode 表按天聚合根分区数据（回退方案）"""
    since = timezone.now() - timedelta(days=days)
    nodes = ClusterNode.objects.filter(
        cluster_id=cluster_id, scanned_at__gte=since
    ).order_by("scanned_at")

    # 按天分组，每天每个节点只取最新一条（去重）
    daily_nodes = defaultdict(dict)  # {date_key: {node_name: ClusterNode}}
    for n in nodes:
        date_key = n.scanned_at.strftime("%Y-%m-%d")
        if n.rootfs_used_gb and n.rootfs_total_gb:
            daily_nodes[date_key][n.node_name] = n

    dates = []
    used_values = []
    total_values = []
    for date_key in sorted(daily_nodes.keys()):
        node_pool = daily_nodes[date_key]
        used = sum(float(n.rootfs_used_gb or 0) for n in node_pool.values())
        total = sum(float(n.rootfs_total_gb or 0) for n in node_pool.values())
        dates.append(date_key)
        used_values.append(round(used, 2))
        total_values.append(round(total, 2))

    if not dates:
        return None

    total_gb = total_values[-1] if total_values else 0

    current_used = used_values[-1] if used_values else 0

    # Holt's Damped Trend 指数平滑
    horizon = 30
    forecasts, level, trend_val = _holt_damped(used_values, alpha=0.25, beta=0.1, phi=0.9, horizon=horizon)
    forecasts = [max(0.0, min(total_gb, f)) for f in forecasts]

    trend = _classify_trend(trend_val, 0.1)

    days_until_full = None
    predicted_full_date = None
    if trend == "rising" and trend_val > 0 and total_gb > current_used:
        days = (total_gb - current_used) / trend_val
        if 0 < days <= 365:
            predicted_full_date = (timezone.now().date() + timedelta(days=round(days))).strftime("%Y-%m-%d")
            days_until_full = round(days)

    extend_days = min(days_until_full or 14, horizon)
    predicted_dates = []
    predicted_values = []
    from datetime import datetime as dt
    base_date = dt.strptime(dates[-1], "%Y-%m-%d")
    for i, f in enumerate(forecasts[:extend_days], 1):
        predicted_dates.append((base_date + timedelta(days=i)).strftime("%Y-%m-%d"))
        predicted_values.append(round(f, 2))

    return {
        "current_used_gb": round(current_used, 2),
        "total_gb": round(total_gb, 2),
        "current_pct": round(current_used / total_gb * 100, 1) if total_gb > 0 else 0,
        "trend": trend,
        "slope_gb_per_day": round(trend_val, 3),
        "days_until_full": days_until_full,
        "predicted_full_date": predicted_full_date,
        "data_points": len(dates),
        "history_days": len(dates),
        "chart": {
            "dates": dates,
            "values": used_values,
            "predicted_dates": predicted_dates,
            "predicted_values": predicted_values,
        },
    }


class PredictionsView(APIView):
    """GET /api/dashboard/predictions/?cluster_id=X&days=30"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = list(_all_cluster_ids())

        if cluster_filter:
            cluster_ids = [int(cluster_filter)]

        if not cluster_ids:
            return Response({})

        since = timezone.now() - timedelta(days=days)
        histories = ScanHistory.objects.filter(
            cluster_id__in=cluster_ids, scanned_at__gte=since
        ).order_by("scanned_at")

        # 检查是否有新字段
        sample = histories.first()
        has_storage = sample and "total_storage_gb" in (sample.snapshot_data or {})
        has_rootfs = sample and "total_rootfs_gb" in (sample.snapshot_data or {})

        # 按天聚合
        cpu_mem_fields = ["avg_cpu_usage", "avg_memory_usage", "total_memory_mb", "used_memory_mb"]
        if has_storage:
            cpu_mem_fields += ["total_storage_gb", "used_storage_gb"]
        if has_rootfs:
            cpu_mem_fields += ["total_rootfs_gb", "used_rootfs_gb"]

        daily = _aggregate_daily(histories, cpu_mem_fields)

        # 获取集群总容量（取最新一条）
        latest = histories.order_by("-scanned_at").first()
        latest_snap = latest.snapshot_data if latest else {}

        total_mem_mb = latest_snap.get("total_memory_mb", 0)
        total_storage_gb = latest_snap.get("total_storage_gb", 0)
        total_rootfs_gb = latest_snap.get("total_rootfs_gb", 0)

        # CPU（0~100 百分比）
        cpu_result = _build_dimension(daily, "avg_cpu_usage", capacity=100, unit="pct", display_multiplier=1)

        # 内存（0~100 百分比）
        mem_result = _build_dimension(daily, "avg_memory_usage", capacity=100, unit="pct", display_multiplier=100)

        # 存储
        if has_storage and total_storage_gb > 0:
            storage_result = _build_dimension(daily, "used_storage_gb", capacity=total_storage_gb, unit="gb")
            storage_result["total_gb"] = round(total_storage_gb, 2)
        else:
            # 回退到 Storage 表
            storage_result = _build_storage_from_tables(cluster_ids[0], days)
            if storage_result is None:
                storage_result = {
                    "current_used_gb": None, "total_gb": None, "current_pct": None,
                    "trend": "unknown", "slope_gb_per_day": None,
                    "days_until_full": None, "predicted_full_date": None,
                    "data_points": 0, "history_days": 0,
                    "chart": {"dates": [], "values": [], "predicted_dates": [], "predicted_values": []},
                }

        # 根分区
        if has_rootfs and total_rootfs_gb > 0:
            rootfs_result = _build_dimension(daily, "used_rootfs_gb", capacity=total_rootfs_gb, unit="gb")
            rootfs_result["total_gb"] = round(total_rootfs_gb, 2)
        else:
            # 回退到 ClusterNode 表
            rootfs_result = _build_rootfs_from_tables(cluster_ids[0], days)
            if rootfs_result is None:
                rootfs_result = {
                    "current_used_gb": None, "total_gb": None, "current_pct": None,
                    "trend": "unknown", "slope_gb_per_day": None,
                    "days_until_full": None, "predicted_full_date": None,
                    "data_points": 0, "history_days": 0,
                    "chart": {"dates": [], "values": [], "predicted_dates": [], "predicted_values": []},
                }

        # 为存储和根分区补 total 信息
        if "total_gb" not in storage_result:
            storage_result["total_gb"] = round(total_storage_gb, 2)
        if "total_gb" not in rootfs_result:
            rootfs_result["total_gb"] = round(total_rootfs_gb, 2)

        # 内存补充绝对值
        mem_result["total_mb"] = round(total_mem_mb)

        # 存储/根分区补充 current_pct
        if storage_result.get("current") is not None and storage_result.get("total_gb"):
            storage_result["current_pct"] = round(storage_result["current"] / storage_result["total_gb"] * 100, 1) if storage_result["total_gb"] > 0 else 0
            storage_result["current_used_gb"] = storage_result.pop("current")
        if rootfs_result.get("current") is not None and rootfs_result.get("total_gb"):
            rootfs_result["current_pct"] = round(rootfs_result["current"] / rootfs_result["total_gb"] * 100, 1) if rootfs_result["total_gb"] > 0 else 0
            rootfs_result["current_used_gb"] = rootfs_result.pop("current")

        return Response({
            "cpu": cpu_result,
            "memory": mem_result,
            "storage": storage_result,
            "rootfs": rootfs_result,
        })
