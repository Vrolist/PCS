# 09 — 多集群对比面板

> 优先级：P3 | 预估工期：3-4天 | 依赖：多集群数据

## 功能描述

支持横向对比多个 PVE 集群：资源使用率、告警数量、健康度、DR 评分等维度，适合管理多套 PVE 环境的运维团队。

## 核心价值

- 跨集群统一管理视角
- 资源均衡度分析
- 管理层快速了解全局

## 对比维度

| 维度 | 指标 | 数据来源 |
|------|------|---------|
| 规模 | 节点数 / VM数 / 容器数 | ClusterNode / VM / LXC |
| 资源 | 平均 CPU / 内存 / 磁盘使用率 | 扫描数据聚合 |
| 健康 | DR Score / 告警数 | DetectionResult |
| 存储 | 总容量 / 已用 / 使用率 | Storage / CephStatus |
| HA | HA 覆盖率 / 故障次数 | HAResource |
| 版本 | PVE 版本分布 | ClusterNode.pve_version |

## 后端 API

```
GET /api/dashboard/cluster-comparison/?cluster_ids=1,2,3
```

返回结构：
```json
{
  "clusters": [
    {
      "id": 1,
      "name": "生产环境",
      "nodes": 3,
      "vms": 25,
      "containers": 15,
      "avg_cpu_pct": 65.2,
      "avg_memory_pct": 72.5,
      "avg_disk_pct": 58.3,
      "alerts": 5,
      "dr_score": 78,
      "storage_total_gb": 2000,
      "storage_used_gb": 1166,
      "ha_coverage_pct": 85.0,
      "pve_version": "8.4.16"
    },
    {
      "id": 2,
      "name": "开发环境",
      "nodes": 1,
      "vms": 8,
      "containers": 3,
      "avg_cpu_pct": 22.1,
      "avg_memory_pct": 45.0,
      "avg_disk_pct": 35.2,
      "alerts": 0,
      "dr_score": 42,
      "storage_total_gb": 500,
      "storage_used_gb": 176,
      "ha_coverage_pct": 0,
      "pve_version": "8.3.4"
    }
  ],
  "comparison": {
    "best_dr_score": {"cluster": 1, "score": 78},
    "most_efficient": {"cluster": 2, "resource_usage": "33%"},
    "highest_alerts": {"cluster": 1, "count": 5}
  }
}
```

## 前端实现

### 对比视图

```
┌──────────────────────────────────────┐
│ 📊 多集群对比                        │
│ 选择集群: [☑ 生产环境] [☑ 开发环境]  │
├──────────────────────────────────────┤
│                                      │
│ 集群         生产环境    开发环境     │
│ ─────────────────────────────────    │
│ 节点          3          1           │
│ VM           25          8           │
│ CPU 均值    65.2%      22.1%         │
│ 内存均值    72.5%      45.0%         │
│ 磁盘均值    58.3%      35.2%         │
│ 告警数        5          0           │
│ DR Score     78 🟡       42 🔴       │
│ HA 覆盖     85%          0%          │
│ PVE 版本   8.4.16      8.3.4        │
├──────────────────────────────────────┤
│ 📈 资源对比柱状图                    │
│ [CPU] [内存] [磁盘] [DR Score]       │
└──────────────────────────────────────┘
```

### 对比图表

- **柱状图对比**：ECharts grouped bar chart
- **雷达图对比**：多维度综合对比
- **排名表**：按各维度排序

## 注意事项

- 对比的集群需要都已接入平台（有 Agent 数据）
- 不同集群的扫描时间可能不同步，需标注数据时效
- 空数据的集群不参与对比（避免误导）
- 对比结果可导出为 Markdown 报告
