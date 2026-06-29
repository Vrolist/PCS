# 数据库模型分析

## 1. 模型概览

项目共定义 **17 个数据模型**（含 1 个 AbstractUser 子类），分布在 4 个 app 中：

| App | 模型数 | 模型列表 |
|-----|--------|---------|
| accounts | 4 | User, PasswordResetCode, Plan, UserPlan |
| clusters | 1 | Cluster |
| agent_api | 2 | AgentInstance, ScanTask |
| scanner | 10 | ClusterNode, VM, LXC, Storage, NetworkInterface, CephStatus, ScanHistory, DetectionRule, DetectionResult |

---

## 2. 各模型详细分析

### 2.1 accounts (用户认证)

#### User
- **继承**: `AbstractUser`
- **额外字段**: `phone`, `company`, `avatar`
- **说明**: 标准 Django 用户模型扩展，基础字段 (username/password/email) 满足认证需求

#### PasswordResetCode
- 功能完备：含过期时间 `expires_at`、已使用标记 `is_used`、有效性校验方法 `is_valid()`
- 与 PVE 无直接关系，认证模块独立

#### Plan / UserPlan
- 套餐体系：Free / Pro / Enterprise
- 含集群数限制 (`max_clusters`, `max_nodes_per_cluster`)、扫描间隔 (`scan_interval_minutes`)、Agent 数限制 (`max_agents_per_cluster`)
- **评价**: 设计合理，满足 SaaS 多租户需求

---

### 2.2 clusters (集群管理)

#### Cluster
| 字段 | PVE 对应 | 说明 |
|------|---------|------|
| `name` | 用户自定义 | 集群名称 |
| `description` | 用户自定义 | 描述 |
| `agent_token` | - | Agent 鉴权 token，自生成 |
| `status` | `cluster/status` 的 level | pending/active/error/archived |
| `pve_version` | `/version` 的 version | 例: `8.2.4` |
| `cluster_id` | - | 用户自定义集群标识 |
| `total_nodes` | `/cluster/status` 中 type=node 计数 | 汇总缓存 |
| `total_vms` | `/cluster/resources?type=vm` 计数 | 汇总缓存 |
| `total_lxc` | `/cluster/resources?type=lxc` 计数 | 汇总缓存 |
| `total_storage` | `/cluster/resources?type=storage` 计数 | 汇总缓存 |
| `last_scanned_at` | - | 最后一次扫描时间 |

**评价**: 字段设计良好，`total_*` 为冗余缓存字段，提升列表查询性能。

---

### 2.3 agent_api (Agent 通信)

#### AgentInstance
| 字段 | 说明 |
|------|------|
| `cluster` | FK → Cluster，所属集群 |
| `agent_id` | 唯一标识 |
| `version` | Agent 自身版本 |
| `hostname` | 所在主机名 |
| `ip_address` | Agent 所在节点 IP |
| `pve_api_endpoint` | PVE API 地址 (如 `https://192.168.1.100:8006`) |
| `scan_interval` | 扫描间隔 |
| `status` | online/offline/error/paused |
| `last_heartbeat_at` | 最后心跳时间 |
| `current_task` | 当前执行任务描述 |

**评价**: 设计合理，支持多 Agent 部署，心跳检测机制完善。

#### ScanTask
- 记录每次扫描任务的元数据（类型、状态、时长、错误）
- `raw_data` 字段 (JSONField) 可存储原始 JSON 用于调试和重处理

---

### 2.4 scanner (扫描数据)

#### ClusterNode
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `cluster` | FK → Cluster | ✅ |
| `scan` | FK → ScanTask | ✅ |
| `node_name` | `/nodes/{node}/status` → `node` | ✅ |
| `status` | `/nodes/{node}/status` → `status` | ✅ |
| `pve_version` | `/nodes/{node}/status` → `pveversion` | ✅ |
| `kernel_version` | `/nodes/{node}/status` → `kversion` | ✅ |
| `cpu_model` | `/nodes/{node}/status` → `cpuinfo.model` | ✅ |
| `cpu_cores` | `/nodes/{node}/status` → `cpuinfo.cpus` | ✅ |
| `cpu_sockets` | `/nodes/{node}/status` → `cpuinfo.sockets` | ✅ |
| `cpu_load` | `/nodes/{node}/status` → `cpu` | ✅ |
| `memory_total_mb` | `/nodes/{node}/status` → `memory.total` | ✅ |
| `memory_used_mb` | `/nodes/{node}/status` → `memory.used` | ✅ |
| `memory_free_mb` | `/nodes/{node}/status` → `memory.free` | ✅ |
| `memory_usage_pct` | 计算值 | ✅ |
| `rootfs_total_gb` | `/nodes/{node}/status` → `rootfs.total` | ✅ |
| `rootfs_used_gb` | `/nodes/{node}/status` → `rootfs.used` | ✅ |
| `rootfs_avail_gb` | `/nodes/{node}/status` → `rootfs.avail` | ✅ |
| `swap_total_mb` | `/nodes/{node}/status` → `swap.total` | ✅ |
| `swap_used_mb` | `/nodes/{node}/status` → `swap.used` | ✅ |
| `disk_io_delay_ms` | `/nodes/{node}/status` → `diskstat[].io_ms` 汇总 | ✅ |
| `diskstat` | `/nodes/{node}/status` → `diskstat` 数组 | ✅ |
| `ip_address` | `/cluster/status` → `ip` 或 DNS 解析 | ⚠️ 需确认来源 |
| `mac_address` | `/nodes/{node}/network` → 对应接口的 MAC | ⚠️ API 无直接 MAC 字段 |
| `is_ceph_node` | `/nodes/{node}/ceph` 检查 | ✅ |
| `is_ha_node` | `/cluster/ha/status` | ⚠️ 需确认端点 |
| `uptime_seconds` | `/nodes/{node}/status` → `uptime` | ✅ |

**`⚠️` 标记的字段需要特别处理：**
- `ip_address`: 可以从 `/cluster/status` 的 `ip` 字段获取
- `mac_address`: PVE API `/nodes/{node}/network` 不直接返回 MAC 地址，需通过 `ip addr` 等方式获取或从 `/nodes/{node}/network` 的某些类型接口中提取（非标准）
- `is_ha_node`: HA 信息可通过 `/cluster/ha/status` 获取

**精度问题**: `rootfs_total_gb`、`rootfs_used_gb`、`rootfs_avail_gb` 当前使用 `BigIntegerField`，但 bytes→GB 转换后会产生浮点数（如 48.5GB），会导致小数截断。建议改为 `FloatField`。

#### VM (QEMU 虚拟机)
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `vmid` | `/nodes/{node}/qemu` → `vmid` | ✅ |
| `name` | `/nodes/{node}/qemu` → `name` | ✅ |
| `status` | `/nodes/{node}/qemu` → `status` | ✅ |
| `cpu_cores` | `/nodes/{node}/qemu` → `maxcpu` | ✅ |
| `cpu_sockets` | `/nodes/{node}/qemu/{vmid}/config` → `sockets` | ✅ |
| `cpu_usage` | `/nodes/{node}/qemu` → `cpu` | ✅ |
| `memory_mb` | `/nodes/{node}/qemu` → `maxmem` (bytes→MB) | ✅ |
| `memory_used_mb` | `/nodes/{node}/qemu` → `mem` (bytes→MB) | ✅ |
| `balloon_min_mb` | `/nodes/{node}/qemu/{vmid}/status/current` → `balloon_min` | ✅ |
| `balloon_max_mb` | `/nodes/{node}/qemu/{vmid}/status/current` → `balloon_max` | ✅ |
| `disk_gb` | `/nodes/{node}/qemu` → `disk` (bytes→GB) | ✅ |
| `max_disk_gb` | `/nodes/{node}/qemu` → `maxdisk` (bytes→GB) | ✅ |
| `disk_write_iops` | `/nodes/{node}/qemu` → `diskwrite` | ✅ |
| `disk_read_iops` | `/nodes/{node}/qemu` → `diskread` | ✅ |
| `net_in_bps` | `/nodes/{node}/qemu` → `netin` | ✅ |
| `net_out_bps` | `/nodes/{node}/qemu` → `netout` | ✅ |
| `uptime_seconds` | `/nodes/{node}/qemu` → `uptime` | ✅ |
| `os_type` | `/nodes/{node}/qemu/{vmid}/config` → `ostype` | ✅ |
| `snapshot_count` | `/nodes/{node}/qemu/{vmid}/snapshot` 返回数组长度 | ✅ |
| `has_template` | `/nodes/{node}/qemu` → `template` | ✅ |
| `tags` | `/nodes/{node}/qemu` → `tags` | ✅ |
| `description` | `/nodes/{node}/qemu/{vmid}/config` → `description` | ✅ |

**评价**: 字段覆盖全面，与 PVE API 高度匹配。

**精度问题**: `disk_gb`、`max_disk_gb` 当前使用 `BigIntegerField`，bytes→GB 转换后浮点数会被截断，建议改为 `FloatField`。

#### LXC (容器)
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `vmid` | `/nodes/{node}/lxc` → `vmid` | ✅ |
| `name` | `/nodes/{node}/lxc` → `name` | ✅ |
| `status` | `/nodes/{node}/lxc` → `status` | ✅ |
| `cpu_cores` | `/nodes/{node}/lxc` → `maxcpu` | ✅ |
| `cpu_usage` | `/nodes/{node}/lxc` → `cpu` | ✅ |
| `memory_mb` | `/nodes/{node}/lxc` → `maxmem` (bytes→MB) | ✅ |
| `memory_used_mb` | `/nodes/{node}/lxc` → `mem` (bytes→MB) | ✅ |
| `swap_mb` | `/nodes/{node}/lxc` → `maxswap` (bytes→MB) | ✅ |
| `swap_used_mb` | `/nodes/{node}/lxc` → `swap` (bytes→MB) | ✅ |
| `disk_gb` | `/nodes/{node}/lxc` → `maxdisk` (bytes→GB) | ✅ |
| `uptime_seconds` | `/nodes/{node}/lxc` → `uptime` | ✅ |
| `tags` | `/nodes/{node}/lxc` → `tags` | ✅ |
| `description` | `/nodes/{node}/lxc/{vmid}/config` → `description` | ✅ |

**评价**: 覆盖全面，与 PVE API 匹配。

#### Storage
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `storage_name` | `/nodes/{node}/storage` → `storage` | ✅ |
| `type` | `/nodes/{node}/storage` → `type` | ✅ |
| `status` | / | ✅ 已有 (available/unavailable) |
| `active` | `/nodes/{node}/storage` → `active` | ✅ |
| `used_gb` | `/nodes/{node}/storage` → `used` (bytes→GB) | ✅ |
| `avail_gb` | `/nodes/{node}/storage` → `available` (bytes→GB) | ✅ |
| `total_gb` | `/nodes/{node}/storage` → `total` (bytes→GB) | ✅ |
| `used_fraction` | `/nodes/{node}/storage` → `used_fraction` | ✅ |
| `content_types` | `/nodes/{node}/storage` → `content` | ✅ |
| `shared` | `/nodes/{node}/storage` → `shared` | ✅ |

**建议**: Storage 模型中缺少 `enabled` 字段，PVE API 返回此字段但当前模型未收录。

**精度问题**: `used_gb`、`avail_gb`、`total_gb` 当前使用 `BigIntegerField`，bytes→GB 转换后浮点数会被截断，建议改为 `FloatField`。

#### NetworkInterface
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `name` | `/nodes/{node}/network` → `iface` | ✅ |
| `type` | `/nodes/{node}/network` → `type` | ✅ |
| `active` | `/nodes/{node}/network` → `active` | ✅ |
| `method` | `/nodes/{node}/network` → `method` | ✅ |
| `address` | `/nodes/{node}/network` → `address` | ✅ |
| `gateway` | `/nodes/{node}/network` → `gateway` | ✅ |
| `speed_mbps` | `/nodes/{node}/network` → `speed` | ✅ |

**建议**:
- 缺少 `mtu` 字段（PVE API 返回此字段）
- 缺少 `bridge_ports` 字段（Bridge 接口的绑定端口）
- 缺少 `bond_mode` 字段（Bond 接口的模式）

#### CephStatus
| 字段 | 数据来源 | 状态 |
|------|---------|------|
| `health` | `/cluster/ceph/status` → `health.status` | ✅ |
| `total_osds` | `/cluster/ceph/status` → `osd.nr` | ✅ |
| `up_osds` | `/cluster/ceph/status` → `osd.up` | ✅ |
| `in_osds` | `/cluster/ceph/status` → `osd.in` | ✅ |
| `pool_count` | `/cluster/ceph/pool` 数组长度 | ✅ |
| `total_used_gb` | `/cluster/ceph/status` → `pgmap.bytes_used` | ✅ |
| `total_avail_gb` | `/cluster/ceph/status` → `pgmap.bytes_avail` | ✅ |
| `total_space_gb` | `/cluster/ceph/status` → `pgmap.bytes_total` | ✅ |
| `extra_data` | JSONField 存额外字段 (mon, mgr, df 等) | ✅ |

**评价**: 核心字段覆盖完整，`extra_data` JSONField 可存 Ceph 的详细状态。

#### 其余模型
- **ScanHistory**: 扫描汇总快照，`snapshot_data` JSONField 灵活存储
- **DetectionRule / DetectionResult**: 自动检测引擎，设计合理

---

## 3. 模型关系图

```
User ──< UserPlan >── Plan
  │
  └──< Cluster
         ├──< AgentInstance
         │     └──< ScanTask
         │
         ├──< ClusterNode
         │     ├──< VM
         │     ├──< LXC
         │     ├──< Storage
         │     └──< NetworkInterface
         │
         ├──< CephStatus
         ├──< ScanHistory
         ├──< DetectionRule
         └──< DetectionResult
```

---

## 4. 改进建议

### 4.1 字段补充

| 模型 | 建议新增字段 | 原因 |
|------|------------|------|
| Storage | `enabled` (Boolean) | PVE API 返回，用于判断存储是否启用 |
| NetworkInterface | `mtu` (Integer) | PVE API 返回，MTU 值对网络诊断有意义 |
| NetworkInterface | `bridge_ports` (CharField) | 桥接接口的绑定端口 |
| NetworkInterface | `bond_mode` (CharField) | Bond 接口的模式 |

### 4.2 字段类型修复

| 模型 | 当前字段 | 当前类型 | 问题 | 建议 |
|------|---------|---------|------|------|
| ClusterNode | `rootfs_total_gb` | BigIntegerField | PVE 返回 bytes，转 GB 后为浮点数，BigIntegerField 截断小数 | 改为 FloatField |
| ClusterNode | `rootfs_used_gb` | BigIntegerField | 同上 | 改为 FloatField |
| ClusterNode | `rootfs_avail_gb` | BigIntegerField | 同上 | 改为 FloatField |
| VM | `disk_gb`, `max_disk_gb` | BigIntegerField | 同上 | 改为 FloatField |
| Storage | `used_gb`, `avail_gb`, `total_gb` | BigIntegerField | 同上 | 改为 FloatField |

### 4.3 字段优化

| 模型 | 当前字段 | 建议 | 原因 |
|------|---------|------|------|
| ClusterNode | `ip_address` | 保持从 `/cluster/status` 获取 | `ip` 字段在嵌套中为可选 |
| ClusterNode | `mac_address` | 改为从 Agent 通过 shell 命令获取 | PVE API 不直接暴露 MAC |

### 4.3 索引建议

| 模型 | 建议索引 | 原因 |
|------|---------|------|
| ClusterNode | `(cluster, scanned_at)` | 按集群查询节点历史 |
| VM / LXC | `(node, scanned_at)` | 按节点查询 VM/CT 历史 |
| ScanHistory | `(cluster, scanned_at)` | 趋势图表查询 |
| DetectionResult | `(cluster, is_resolved)` | 活跃告警列表查询 |

### 4.4 序列化器

目前只有 accounts app 有 serializers.py，以下 app 需要新建：

| App | 建议 Serializer |
|-----|----------------|
| clusters | ClusterSerializer (CRUD) |
| agent_api | AgentInstanceSerializer, ScanTaskSerializer |
| scanner | 全部 10 个模型的 Serializer |

### 4.5 视图

所有业务视图（clusters, agent_api, scanner）目前仅含占位函数，需要实现：
- clusters: ClusterViewSet (CRUD)
- agent_api: AgentRegisterView, AgentHeartbeatView, ScanTaskView
- scanner: DataUploadView, DashboardDataView
