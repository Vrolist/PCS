# 01 — 容量规划与趋势预测

> 优先级：P0 | 预估工期：3-5天 | 依赖：ScanHistory 数据积累

## 功能描述

基于历史扫描快照（`ScanHistory`），对集群资源使用率进行趋势分析和线性回归预测，计算存储、内存、CPU 等资源预计满载日期，在 Dashboard 展示预测卡片和趋势图表。

## 核心价值

- 提前发现容量瓶颈，避免突发宕机
- 为采购决策提供数据支撑
- 运维从"救火"转向"预防"

## 数据来源

| 指标 | 字段 | 模型 |
|------|------|------|
| CPU 使用率 | `ScanHistory.snapshot_data.avg_cpu_usage` | 按天聚合均值 |
| 内存使用率 | `ScanHistory.snapshot_data.avg_memory_usage` | 按天聚合均值 |
| 存储已用 | `Storage.used_gb` (历史) | 按天聚合总量 |
| 磁盘空间 | `ClusterNode.rootfs_used_gb` | 按天聚合 |

## 后端实现

### 新增 API

```
GET /api/dashboard/predictions/?cluster_id=X&days=90
```

返回结构：
```json
{
  "storage": {
    "current_usage_gb": 2400,
    "total_gb": 4000,
    "daily_growth_gb": 2.3,
    "days_until_full": 696,
    "predicted_full_date": "2028-06-09"
  },
  "memory": {
    "current_avg_pct": 72.5,
    "trend": "stable",
    "slope_pct_per_day": 0.05
  },
  "cpu": {
    "current_avg_pct": 35.2,
    "trend": "rising",
    "slope_pct_per_day": 0.12
  }
}
```

### 预测算法

使用 **最小二乘法线性回归**：

```python
def predict_full_date(history_points, total_capacity):
    """
    history_points: [(timestamp, used_value), ...]
    total_capacity: 资源总量
    返回: (predicted_full_date, daily_growth_rate)
    """
    if len(history_points) < 7:
        return None, 0  # 数据不足
    
    # 线性回归 y = ax + b
    x = np.array([(p[0] - history_points[0][0]).total_seconds() / 86400
                   for p in history_points])
    y = np.array([p[1] for p in history_points])
    
    n = len(x)
    a = (n * np.sum(x*y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
    b = (np.sum(y) - a * np.sum(x)) / n
    
    # 预计满载时间
    if a <= 0:
        return None, a  # 不增长
    
    days_remaining = (total_capacity - b) / a  # 从当前预测
    full_date = datetime.now() + timedelta(days=days_remaining)
    
    return full_date, a
```

## 前端实现

### Dashboard 预测卡片

在现有 `StatCards.vue` 旁新增 `PredictionCard.vue`：

```
┌──────────────────────┐
│ ⏰ 容量预测          │
│                      │
│ 💾 存储              │
│ ████████░░ 60%       │
│ 预计 696 天后满      │
│ 每天增长 2.3 GB      │
│                      │
│ 🧠 内存              │
│ █████████░ 72%       │
│ 趋势：稳定 (±0.05%)  │
│                      │
│ ⚡ CPU               │
│ ████░░░░░░ 35%       │
│ ⚠️ 趋势：上升 ↑      │
└──────────────────────┘
```

### 趋势图表扩展

扩展 `TrendChart.vue`，支持：
- 时间范围选择器（7天/30天/90天/全部）
- 预测线叠加（虚线延伸到预测日期）
- 阈值标记线（85%/95% 告警线）

## 注意事项

- 数据点不足 7 天时不显示预测（避免误判）
- 线性回归适合稳定增长场景，指数增长（如日志爆炸）需额外检测
- 预测结果标记为"仅供参考"，避免过度依赖
- 存储增长可能不是线性的（扩容后突然跳变），需要异常点剔除
