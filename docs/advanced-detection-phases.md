# PVE 集群进阶检测 — 四阶段实施计划

基于当前项目已采集的 PVE API 数据，分阶段实现集群潜在问题自动检测。

## 数据模型基础

检测引擎基于已有的两个模型：

- **DetectionRule** — 规则配置，condition_config (JSON) 存储检测条件
- **DetectionResult** — 检测结果，记录告警标题/详情/严重级别

---

## 第一阶段：资源 + 可用性检测

**优先级最高**，数据已齐全，实现最直接。

### 资源类检测 (resource)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| CPU 过载 | ClusterNode.cpu_load | `> 0.8` 告警，`> 0.95` 严重 | warning / critical |
| 内存过载 | ClusterNode.memory_usage_pct | `> 85%` 告警，`> 95%` 严重 | warning / critical |
| 内存 Balloon 收紧 | VM balloon_min/max | 实际内存 < balloon_min | warning |
| 磁盘空间不足 | ClusterNode.rootfs_*, Storage.used_gb | 根分区 `> 85%`，存储 `> 90%` | warning / critical |
| Swap 使用异常 | ClusterNode.swap_used_mb | 使用率 `> 50%` | warning |
| I/O 延迟过高 | ClusterNode.disk_io_delay_ms | `> 50ms` 告警，`> 200ms` 严重 | warning / critical |
| VM CPU 超分 | VM.cpu_usage vs cpu_cores | 单 VM CPU 使用率 `> 90%` | warning |
| VM 内存溢出风险 | VM.memory_used_mb / memory_mb | 使用率 `> 90%` 且无 balloon | warning |

### 可用性检测 (availability)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| 节点离线 | ClusterNode.status | status != online 且上次扫描 > 5min | critical |
| HA 资源状态异常 | HAResource.state | state != started（非预期停止） | critical |
| HA 重启次数过多 | HAResource.crm_state 变化 | 短时间内重启 > 3 次 | warning |
| HA 资源不在组内 | HAResource.ha_group | 有 HA 标记但未加入任何组 | warning |
| VM 长时间停机 | VM.status + uptime_seconds | stopped 且 uptime < 60s | info |
| 关键服务无 HA | VMConfig.ha_enabled | 运行中的 VM 无 HA 保护 | info |

---

## 第二阶段：存储 + Ceph 检测

依赖 Storage / CephStatus 数据。

### 存储与备份检测 (storage)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| 存储容量告警 | Storage.used_fraction | 使用率 `> 85%` 告警，`> 95%` 严重 | warning / critical |
| 无备份存储 | Storage.content_types | 集群内无 backup 类型存储 | warning |
| 存储不可用 | Storage.status | status = unavailable | critical |
| 存储使用率不均 | Storage.used_fraction | 同类型存储使用率差异过大 | info |

### Ceph 检测 (ceph)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| Ceph OSD 异常 | CephStatus.up_osds / total_osds | up_osds < total_osds | warning / critical |
| Ceph 健康异常 | CephStatus.health | health != HEALTH_OK | warning / critical |
| Ceph 存储不足 | CephStatus.total_used_gb | 使用率 `> 80%` | warning |

---

## 第三阶段：性能 + 趋势检测

需要 ScanHistory 积累数据后方可实现。

### 性能检测 (performance)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| 网络流量异常 | VM.net_in_bps / net_out_bps | 入/出流量突增 `> 100Mbps` | warning |
| 磁盘 IOPS 异常 | VM.disk_read_iops / disk_write_iops | 单盘 IOPS `> 10000` | warning |
| 节点负载不均 | 多节点 cpu_load 对比 | 节点间 CPU 差异 `> 50%` | info |
| CPU 类型不一致 | VMConfig.cpu_type | 同集群 VM CPU 类型不统一，影响热迁移 | info |

### 趋势检测 (trend)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| CPU 使用率持续上升 | ScanHistory 按天聚合 | 连续 3 天 cpu 持续上涨 `> 10%` | warning |
| 内存使用率持续上升 | ScanHistory 按天聚合 | 连续 3 天 mem 持续上涨 `> 10%` | warning |
| 存储即将耗尽预测 | Storage 历史 used_gb 趋势 | 按线性回归，X 天内将满 | warning |
| 扫描频率下降 | AgentInstance.last_scan_at | 实际扫描间隔 > 配置间隔的 1.5 倍 | warning |

---

## 第四阶段：安全 + 合规检测

需要维护版本基线数据。

### 安全检测 (security)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| QEMU Agent 未启用 | VMConfig.agent_enabled | 生产 VM 未启用 Agent | info |
| VM 无快照保护 | VM.snapshot_count | 非模板 VM 无任何快照 | info |
| 存储未加密 | Storage.type + content_types | 敏感存储类型无加密 | info |
| API 暴露检测 | ClusterNode.ip_address | 节点 IP 暴露在公网 | warning |

### 版本与合规检测 (compliance)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| PVE 版本过旧 | ClusterNode.pve_version | 低于当前最新 2 个版本 | info |
| 内核版本不一致 | ClusterNode.kernel_version | 节点间内核版本不同 | info |
| Agent 版本过旧 | AgentInstance.version | 低于 latest_version | info |
| Node 版本不一致 | 多节点 pve_version | 节点间 PVE 版本不同，影响集群稳定性 | warning |

### 配置检测 (configuration)

| 检测项 | 数据来源 | 规则示例 | 级别 |
|--------|---------|---------|------|
| VM 配置冗余 | VMConfig.raw_config | 多余的空 IDE/SCSI 设备 | info |
| 网络配置冲突 | NetworkInterface.address | 同集群内 IP 地址重复 | warning |
| 磁盘 I/O 延迟分布不均 | ClusterNode.diskstat JSON | 单盘 I/O 占比 `> 80%` | warning |

---

## 实施优先级总结

| 阶段 | 分类 | 检测项数量 | 依赖数据 | 优先级 |
|------|------|-----------|---------|--------|
| 第一阶段 | 资源 + 可用性 | 14 项 | ClusterNode / VM / HAResource | P0 |
| 第二阶段 | 存储 + Ceph | 7 项 | Storage / CephStatus | P1 |
| 第三阶段 | 性能 + 趋势 | 8 项 | VM 流量/IOPS + ScanHistory | P2 |
| 第四阶段 | 安全 + 合规 | 8 项 | VMConfig / 版本信息 | P3 |
