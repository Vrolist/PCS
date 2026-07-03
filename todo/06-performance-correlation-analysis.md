# 06 — 性能关联分析

> 优先级：P2 | 预估工期：3-4天 | 依赖：VM IOPS/网络流量 + Node IO delay 数据

## 功能描述

对集群性能数据进行多维度关联分析：IOPS vs 延迟散点图、网络流量 vs CPU 负载关联、节点间负载均衡热力图，帮助运维人员定位性能瓶颈。

## 核心价值

- 发现"慢盘"（IOPS 低但延迟高）
- 识别网络密集型 vs CPU 密集型 VM
- 判断负载是否均衡分布

## 数据来源

| 分析维度 | 字段 | 来源模型 |
|---------|------|---------|
| IOPS | `disk_read_iops`, `disk_write_iops` | VM |
| IO 延迟 | `disk_io_delay_ms`, `diskstat` | ClusterNode |
| 网络流量 | `net_in_bps`, `net_out_bps` | VM |
| CPU 使用率 | `cpu_usage` | VM / LXC |
| 内存使用率 | `memory_used_mb / memory_mb` | VM / LXC |

## 分析图表

### 1. IOPS vs 延迟散点图

X 轴：IOPS（读+写），Y 轴：IO 延迟 (ms)
- 每个点代表一个节点
- 颜色编码：绿色(<10ms) / 黄色(10-50ms) / 红色(>50ms)
- 发现离群点：IOPS 高但延迟高 = 磁盘瓶颈

### 2. 网络 vs CPU 关联

X 轴：网络总流量(Mbps)，Y 轴：CPU 使用率(%)
- 每个点代表一个 VM
- 颜色编码：节点归属
- 发现：高网络低 CPU = 网关/代理 VM；高 CPU 低网络 = 计算节点

### 3. 节点负载热力图

矩阵图：X 轴 = 节点，Y 轴 = 指标（CPU/内存/磁盘/网络/IO）
- 颜色深度 = 使用率
- 一眼看出哪个节点最忙

### 4. Top N 排行榜

- Top 5 IOPS 的 VM
- Top 5 网络流量的 VM
- Top 5 CPU 使用率的 VM
- Top 5 IO 延迟的节点

## 后端 API

```
GET /api/dashboard/performance-analysis/?cluster_id=X&type=scatter|iops_latency|network_cpu|heatmap|topn
```

## 前端实现

新增 `views/performance/index.vue`，使用 ECharts 散点图和热力图组件：

```
┌──────────────────────────────────────┐
│ 📈 性能关联分析                      │
│ [IOPS-延迟] [网络-CPU] [热力图] [TopN]│
├──────────────────────────────────────┤
│                                      │
│     IOPS vs IO 延迟                  │
│  ms│          🔴                     │
│ 50 │    🟡                           │
│    │ 🟢🟢🟢🟢🟢                      │
│ 10 │  🟢🟢🟢🟢                       │
│    └──────────────── IOPS            │
│       1K  5K  10K  50K              │
│                                      │
│ ⚠️ xingbox IO 延迟异常 (120ms)       │
│ 建议检查 NVMe 健康状态               │
├──────────────────────────────────────┤
│ 🏆 Top 5 网络流量 VM                 │
│ 1. VM 199 (nwy-server)    85 Mbps   │
│ 2. VM 7711 (Win11-P620)   42 Mbps   │
│ 3. CT 150 (nwy-server)    38 Mbps   │
└──────────────────────────────────────┘
```

## 注意事项

- 散点图适合对比维度不超过 3 个（2 轴 + 颜色）
- 热力图在数据量大时需要缩放交互
- ECharts 的 scatter 和 heatmap 组件原生支持
- TopN 数据量固定（前 5/10），不需要分页
