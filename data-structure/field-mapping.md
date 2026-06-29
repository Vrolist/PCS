# PVE API 字段与数据库模型字段映射

## 1. ClusterNode - 节点状态

**API 端点**: `GET /nodes/{node}/status`

| DB 字段 | API 字段路径 | 类型转换 | 必填 |
|---------|-------------|---------|------|
| `node_name` | `node` | 直接 | ✅ |
| `status` | `status` | 直接 | ✅ |
| `pve_version` | `pveversion` | 直接 | ✅ |
| `kernel_version` | `kversion` | 直接 (或 `current-kernel.version`) | ✅ |
| `cpu_model` | `cpuinfo.model` | 嵌套取值 | ✅ |
| `cpu_cores` | `cpuinfo.cpus` | 直接 (含超线程) | ✅ |
| `cpu_sockets` | `cpuinfo.sockets` | 直接 | ✅ |
| `cpu_load` | `cpu` | 0~1 float | ✅ |
| `memory_total_mb` | `memory.total` | bytes ÷ 1048576 → MB | ✅ |
| `memory_used_mb` | `memory.used` | bytes ÷ 1048576 → MB | ✅ |
| `memory_free_mb` | `memory.free` | bytes ÷ 1048576 → MB | ✅ |
| `memory_usage_pct` | - | 计算: `used/total*100` | ✅ |
| `rootfs_total_gb` | `rootfs.total` | bytes ÷ 1073741824 → GB | ✅ |
| `rootfs_used_gb` | `rootfs.used` | bytes ÷ 1073741824 → GB | ✅ |
| `rootfs_avail_gb` | `rootfs.avail` | bytes ÷ 1073741824 → GB | ✅ |
| `swap_total_mb` | `swap.total` | bytes ÷ 1048576 → MB | ✅ |
| `swap_used_mb` | `swap.used` | bytes ÷ 1048576 → MB | ✅ |
| `ip_address` | `/cluster/status` → `ip` | 从集群状态获取 | ⚠️ |
| `mac_address` | - | Agent shell 命令获取 | ⚠️ |
| `is_ceph_node` | `/nodes/{node}/ceph` 存在 | 检查响应非空 | ⚠️ |
| `is_ha_node` | `/cluster/ha/status` | 检查节点是否在 HA 组中 | ⚠️ |
| `uptime_seconds` | `uptime` | 直接 (秒) | ✅ |

---

## 2. VM / QEMU 虚拟机

**API 端点**: `GET /nodes/{node}/qemu` + `GET /nodes/{node}/qemu/{vmid}/status/current` + `GET /nodes/{node}/qemu/{vmid}/config`

| DB 字段 | API 字段路径 | 类型转换 | 来源端点 |
|---------|-------------|---------|---------|
| `vmid` | `vmid` | 直接 | qemu list |
| `name` | `name` | 直接 | qemu list |
| `status` | `status` | `running`/`stopped`/`paused` | qemu list |
| `cpu_cores` | `maxcpu` | 直接 | qemu list |
| `cpu_sockets` | `sockets` | 直接 | qemu config |
| `cpu_usage` | `cpu` | 0~1 float | qemu list |
| `memory_mb` | `maxmem` | bytes ÷ 1048576 | qemu list |
| `memory_used_mb` | `mem` | bytes ÷ 1048576 | qemu list |
| `balloon_min_mb` | `balloon_min` | bytes ÷ 1048576 | status/current |
| `balloon_max_mb` | `balloon_max` | bytes ÷ 1048576 | status/current |
| `disk_gb` | `disk` | bytes ÷ 1073741824 | qemu list |
| `max_disk_gb` | `maxdisk` | bytes ÷ 1073741824 | qemu list |
| `disk_write_iops` | `diskwrite` | 直接 (bytes/s) | qemu list |
| `disk_read_iops` | `diskread` | 直接 (bytes/s) | qemu list |
| `net_in_bps` | `netin` | 直接 (bytes/s) | qemu list |
| `net_out_bps` | `netout` | 直接 (bytes/s) | qemu list |
| `uptime_seconds` | `uptime` | 直接 (秒) | qemu list |
| `os_type` | `ostype` | 直接 | qemu config |
| `snapshot_count` | (快照列表长度) | array.length | qemu snapshot |
| `has_template` | `template` | 0/1 → boolean | qemu list |
| `tags` | `tags` | 直接 (逗号分隔) | qemu list |
| `description` | `description` | 直接 | qemu config |

---

## 3. LXC 容器

**API 端点**: `GET /nodes/{node}/lxc` + `GET /nodes/{node}/lxc/{vmid}/status/current`

| DB 字段 | API 字段路径 | 类型转换 |
|---------|-------------|---------|
| `vmid` | `vmid` | 直接 |
| `name` | `name` | 直接 |
| `status` | `status` | `running`/`stopped` |
| `cpu_cores` | `maxcpu` | 直接 (可为小数) |
| `cpu_usage` | `cpu` | 0~1 float |
| `memory_mb` | `maxmem` | bytes ÷ 1048576 |
| `memory_used_mb` | `mem` | bytes ÷ 1048576 |
| `swap_mb` | `maxswap` | bytes ÷ 1048576 |
| `swap_used_mb` | `swap` | bytes ÷ 1048576 |
| `disk_gb` | `maxdisk` | bytes ÷ 1073741824 |
| `uptime_seconds` | `uptime` | 直接 |
| `tags` | `tags` | 直接 |
| `description` | `description` | 直接 (从 config 获取) |

---

## 4. Storage 存储

**API 端点**: `GET /nodes/{node}/storage`

| DB 字段 | API 字段路径 | 类型转换 |
|---------|-------------|---------|
| `storage_name` | `storage` | 直接 |
| `type` | `type` | 直接 (dir/nfs/lvm/zfs/rbd/...) |
| `active` | `active` | 0/1 → boolean |
| `enabled` (建议新增) | `enabled` | 0/1 → boolean |
| `used_gb` | `used` | bytes ÷ 1073741824 |
| `avail_gb` | `available` | bytes ÷ 1073741824 |
| `total_gb` | `total` | bytes ÷ 1073741824 |
| `used_fraction` | `used_fraction` | 0~1 float |
| `content_types` | `content` | 直接 (逗号分隔) |
| `shared` | `shared` | 0/1 → boolean |

---

## 5. NetworkInterface 网络接口

**API 端点**: `GET /nodes/{node}/network`

| DB 字段 | API 字段路径 | 类型转换 |
|---------|-------------|---------|
| `name` | `iface` | 直接 |
| `type` | `type` | 直接 (bridge/bond/eth/alias) |
| `active` | `active` | 0/1 → boolean |
| `method` | `method` | 直接 (static/dhcp/manual) |
| `address` | `address` | 直接 |
| `gateway` | `gateway` | 直接 |
| `speed_mbps` | `speed` | 直接 |
| `mtu` (建议新增) | `mtu` | 直接 |
| `bridge_ports` (建议新增) | `bridge_ports` | 直接 |
| `bond_mode` (建议新增) | `bond_mode` | 直接 |

---

## 6. CephStatus Ceph 状态

**API 端点**: `GET /cluster/ceph/status` + `GET /cluster/ceph/pool`

| DB 字段 | API 字段路径 | 类型转换 |
|---------|-------------|---------|
| `health` | `health.status` | `HEALTH_OK`/`HEALTH_WARN`/`HEALTH_ERR` |
| `total_osds` | `osd.nr` | 直接 |
| `up_osds` | `osd.up` | 直接 |
| `in_osds` | `osd.in` | 直接 |
| `pool_count` | `/cluster/ceph/pool` 数组长度 | array.length |
| `total_used_gb` | `pgmap.bytes_used` | bytes ÷ 1073741824 |
| `total_avail_gb` | `pgmap.bytes_avail` | bytes ÷ 1073741824 |
| `total_space_gb` | `pgmap.bytes_total` | bytes ÷ 1073741824 |
| `extra_data` | 其余嵌套字段 | JSONField 存原始数据 |

---

## 7. 通用转换规则

| 原始类型 | 数据库类型 | 转换公式 |
|---------|-----------|---------|
| bytes (内存) | MB (IntegerField) | `value // 1048576` |
| bytes (磁盘) | GB (FloatField) | `round(value / 1073741824, 2)` |
| CPU 0~1 | 百分比 (FloatField) | `round(value * 100, 1)` |
| 0/1 integer | BooleanField | `bool(value)` |
| Unix 时间戳 | DateTimeField | `datetime.fromtimestamp(value)` |

> ⚠️ **精度警告**：当前数据库模型中 `ClusterNode.rootfs_*_gb`、`VM.disk_gb/max_disk_gb`、`Storage.*_gb` 实际使用了 `BigIntegerField`，但磁盘容量转 GB 后为浮点数（如 48.5GB），会导致小数被截断。建议将这些字段改为 `FloatField`，或统一用 MB 单位存储（`BigIntegerField` 存储 MB 整数不会丢失精度）。
