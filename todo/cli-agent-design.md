# CLI Agent 设计方案

> PVE Shell 命令数据采集 Agent — 补充现有 API Agent 无法获取的系统级数据

---

## 1. 背景与目标

### 1.1 现状

现有 `agent/agent.py` 通过 PVE REST API（`/api2/json/`）采集虚拟化层数据（节点状态、VM、LXC、存储、网络、Ceph）。API 数据结构化程度高，但覆盖范围有限：

| 数据类型 | API 是否可获取 | 说明 |
|---------|--------------|------|
| 节点 CPU/内存/磁盘使用率 | ✅ | `/nodes/{node}/status` |
| VM/LXC 列表与状态 | ✅ | `/nodes/{node}/qemu`、`/lxc` |
| 存储/网络 | ✅ | `/nodes/{node}/storage`、`/network` |
| Ceph/HA 状态 | ✅ | `/cluster/ceph/status`、`/cluster/ha/resources` |
| PVE 完整版本信息 | ❌ | API `/version` 只返回主版本，不返回 30+ 个组件版本 |
| CPU/磁盘性能基准 | ❌ | `pveperf` 独有，无 API |
| 磁盘硬件健康 | ❌ | `smartctl` 独有，无 API |
| ZFS 池健康与详情 | ❌ | `zpool status` 独有，无 API |
| 仲裁环路详情 | ⚠️ 部分 | API 缺少 ring 状态和丢失票数信息 |
| 内核硬件错误 | ❌ | `dmesg` 独有，无 API |
| CPU 详细信息（架构/缓存/主频） | ⚠️ 部分 | API 不返回缓存和精确主频 |
| 网卡 MAC 地址/MTU | ❌ | Proxmox 开发者确认 API 不暴露 |

> PVE REST API **没有执行任意 Shell 命令的端点**，这是官方的安全设计。

### 1.2 目标

设计一个独立的 **CLI Agent**，部署在每个 PVE 节点上，通过执行 PVE 官方命令 + Linux 系统命令采集系统级数据，上报到管理平台，补充 API Agent 的数据空白。

### 1.3 设计原则

1. **只读执行** — 白名单命令，不执行任何写入/修改操作
2. **每节点独立** — 每个节点部署一个 CLI Agent，采集本机数据
3. **与 API Agent 互补** — 不替代，只补充
4. **零外部依赖** — 纯 Python 标准库，与现有 Agent 风格一致
5. **安全优先** — 命令白名单 + 输出大小限制 + 执行超时

---

## 2. 架构设计

### 2.1 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    Web 管理平台 (Django + Vue)            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Dashboard    │  │ 节点详情页    │  │ 告警中心      │  │
│  │ (性能基准)   │  │ (硬件信息)   │  │ (健康告警)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼────────┐  │
│  │              CLI Agent API (新增)                   │  │
│  │    /api/agent-cli/scan/    数据上报                 │  │
│  │    /api/agent-cli/heartbeat/  心跳                  │  │
│  │    /api/agent-cli/version/   版本查询               │  │
│  │    /api/agent-cli/install.sh  安装脚本              │  │
│  └──────────────────────┬─────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │ CLI Agent   │ │ CLI Agent   │ │ CLI Agent   │
   │ (pve-1)    │ │ (pve-2)    │ │ (pve-3)    │
   │             │ │             │ │             │
   │ pveperf     │ │ pveperf     │ │ pveperf     │
   │ smartctl    │ │ smartctl    │ │ smartctl    │
   │ zpool       │ │ zpool       │ │ zpool       │
   │ dmesg       │ │ dmesg       │ │ dmesg       │
   │ lscpu       │ │ lscpu       │ │ lscpu       │
   │ pveversion  │ │ pveversion  │ │ pveversion  │
   └─────────────┘ └─────────────┘ └─────────────┘

   ┌──────────────┐ ┌──────────────┐
   │ CLI Agent   │ │ CLI Agent   │
   │ (pve-4)    │ │ (pve-5)    │
   └─────────────┘ └─────────────┘
```

### 2.2 与现有 Agent 的关系

```
PVE 节点
  │
  ├── API Agent (agent.py)     ← 虚拟化层数据（REST API）
  │     采集：VM / LXC / 存储 / 网络 / Ceph / HA
  │     权限：PVEAuditor（低权限）
  │     间隔：每 300s
  │
  └── CLI Agent (cli_agent.py) ← 系统层数据（Shell 命令）  [新增]
        采集：性能基准 / 硬件健康 / 软件版本 / ZFS / 仲裁
        权限：root（需要执行系统命令）
        间隔：每 3600s（CLI 数据变化慢）
```

---

## 3. 命令白名单设计

### 3.1 白名单分类

```python
# 命令分类定义
COMMAND_CATEGORIES = {
    # ── 集群级命令（任意节点可执行，数据相同）──
    "cluster": {
        "pvecm_status":      "pvecm status",
        "pvecm_nodes":       "pvecm nodes",
        "quorum_detail":     "corosync-quorumtool -s",
    },

    # ── 节点级命令（本机数据，每个节点必须独立执行）──
    "node": {
        "pveperf":           "pveperf",
        "pveversion":        "pveversion -v",
        "lscpu":             "lscpu --json",
        "dmesg_hw_errors":   "dmesg --level=err,warn | tail -50",
        "smart_health":      "smartctl -H {device}",
        "smart_info":        "smartctl -i {device}",
        "smart_health_all":  "for d in /dev/sd? /dev/nvme?n?; do smartctl -H $d 2>/dev/null; done",
    },

    # ── 存储级命令（本机存储池）──
    "storage": {
        "zpool_status":      "zpool status",
        "zpool_iostat":      "zpool iostat -v 1 1",
        "lvm_status":        "lvs --noheadings --nosuffix --units g",
    },

    # ── 网络级命令 ──
    "network": {
        "ip_link":           "ip -j link show",
        "ip_addr":           "ip -j addr show",
    },
}
```

### 3.2 安全约束

| 约束项 | 值 | 说明 |
|--------|-----|------|
| 命令白名单 | 仅上述命令 | 未在白名单中的命令直接拒绝 |
| 输出大小限制 | 512 KB | 超出截断，防止 OOM |
| 执行超时 | 30 秒 | `pveperf` 等耗时命令放宽到 120 秒 |
| 无写入操作 | 严格禁止 | `qm start/stop/create`、`pct`、`zpool destroy` 等全部禁止 |
| 设备名限制 | `/dev/sd?`、`/dev/nvme?n?` | `smartctl` 只允许标准磁盘设备 |

---

## 4. 数据模型设计

### 4.1 新增模型（`apps/scanner/models.py`）

```python
class NodeBenchResult(models.Model):
    """节点性能基准 — pveperf 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE, related_name="bench_results")

    # pveperf 输出解析
    cpu_bogomips = models.FloatField("BogoMIPS", null=True, blank=True)
    cpu_threads = models.IntegerField("CPU线程数", null=True, blank=True)
    disk_seq_read_mbs = models.FloatField("磁盘顺序读(MB/s)", null=True, blank=True)
    disk_seq_write_mbs = models.FloatField("磁盘顺序写(MB/s)", null=True, blank=True)

    raw_output = models.TextField("原始输出", blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "性能基准"
        ordering = ["-scanned_at"]
        indexes = [models.Index(fields=["node", "-scanned_at"])]


class NodeSoftwareVersion(models.Model):
    """节点软件版本 — pveversion -v 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="software_versions", null=True, blank=True)

    proxmox_ve = models.CharField("Proxmox VE", max_length=64, blank=True)
    kernel = models.CharField("内核版本", max_length=128, blank=True)
    pve_manager = models.CharField("PVE Manager", max_length=64, blank=True)
    # 关键组件版本
    corosync = models.CharField("Corosync", max_length=64, blank=True)
    pve_cluster = models.CharField("PVE Cluster", max_length=64, blank=True)
    pve_container = models.CharField("PVE Container", max_length=64, blank=True)
    pve_qemu_kvm = models.CharField("PVE QEMU KVM", max_length=64, blank=True)
    qemu_server = models.CharField("QEMU Server", max_length=64, blank=True)
    zfsutils = models.CharField("ZFS Utils", max_length=64, blank=True)
    smartmontools = models.CharField("SmartMonTools", max_length=64, blank=True)
    # 全部包版本 JSON
    all_packages = models.JSONField("全部组件版本", default=dict, blank=True,
        help_text='{"pve-qemu-kvm": "7.2.0-8", "corosync": "3.1.7-pve1", ...}')

    raw_output = models.TextField("原始输出", blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "软件版本"
        unique_together = ("node",)
        ordering = ["node"]


class NodeHardwareInfo(models.Model):
    """节点硬件信息 — lscpu / smartctl / lspci 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="hardware_info", null=True, blank=True)

    # CPU 详情
    cpu_model = models.CharField("CPU型号", max_length=256, blank=True)
    cpu_arch = models.CharField("架构", max_length=64, blank=True)
    cpu_mhz = models.FloatField("当前主频(MHz)", null=True, blank=True)
    cpu_max_mhz = models.FloatField("最大主频(MHz)", null=True, blank=True)
    cpu_cache_kb = models.IntegerField("缓存(KB)", null=True, blank=True)
    cpu_threads = models.IntegerField("线程数", null=True, blank=True)
    cpu_cores = models.IntegerField("核心数", null=True, blank=True)
    cpu_sockets = models.IntegerField("插槽数", null=True, blank=True)

    # BIOS / 主板
    bios_version = models.CharField("BIOS版本", max_length=128, blank=True)
    bios_date = models.CharField("BIOS日期", max_length=32, blank=True)
    board_vendor = models.CharField("主板厂商", max_length=128, blank=True)
    board_name = models.CharField("主板型号", max_length=128, blank=True)

    # 磁盘健康
    disks = models.JSONField("磁盘列表", default=list, blank=True,
        help_text='[{"device":"/dev/sda","model":"Samsung SSD","capacity_gb":480,'
                  '"health":"PASSED","temp_c":35,"power_on_hours":12000,'
                  '"reallocation_count":0,"wear_leveling":95}]')

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "硬件信息"
        unique_together = ("node",)
        ordering = ["node"]


class NodeZFSStatus(models.Model):
    """ZFS 存储池状态 — zpool status / zpool iostat 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="zfs_status", null=True, blank=True)

    pool_name = models.CharField("池名", max_length=128)
    health = models.CharField("健康状态", max_length=32, help_text="ONLINE / DEGRADED / FAULTED")
    size_gb = models.BigIntegerField("总容量(GB)", null=True, blank=True)
    used_gb = models.BigIntegerField("已用(GB)", null=True, blank=True)
    free_gb = models.BigIntegerField("可用(GB)", null=True, blank=True)
    fragmentation_pct = models.FloatField("碎片率(%)", null=True, blank=True)

    # VDev 拓扑
    vdevs = models.JSONField("VDev配置", default=list, blank=True,
        help_text='[{"name":"mirror-0","type":"mirror","state":"ONLINE",'
                  '"devices":[{"path":"/dev/sda","state":"ONLINE"}]}]')

    # I/O 统计（zpool iostat）
    read_ops = models.BigIntegerField("读操作数", null=True, blank=True)
    write_ops = models.BigIntegerField("写操作数", null=True, blank=True)
    read_bandwidth_mbs = models.FloatField("读带宽(MB/s)", null=True, blank=True)
    write_bandwidth_mbs = models.FloatField("写带宽(MB/s)", null=True, blank=True)

    # 错误信息
    errors = models.JSONField("错误信息", default=list, blank=True)
    raw_output = models.TextField("原始输出", blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "ZFS状态"
        unique_together = ("node", "pool_name", "scanned_at")
        ordering = ["node", "pool_name"]
        indexes = [models.Index(fields=["node", "-scanned_at"])]


class NodeQuorumDetail(models.Model):
    """集群仲裁详情 — corosync-quorumtool 采集"""
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE,
                                related_name="quorum_details", null=True, blank=True)

    quorate = models.BooleanField("仲裁通过")
    votes_expected = models.IntegerField("预期票数", null=True, blank=True)
    votes_total = models.IntegerField("实际票数", null=True, blank=True)
    ring_id = models.CharField("环路ID", max_length=32, blank=True)

    # 环路详情
    ring_status = models.JSONField("环路状态", default=list, blank=True,
        help_text='[{"ring":0,"status":"OK","addr":"192.168.1.10","latency_ms":0.1}]')

    # 节点成员信息
    members = models.JSONField("成员列表", default=list, blank=True,
        help_text='[{"nodeid":1,"name":"pve-1","ip":"192.168.1.10","online":true,"votes":1}]')

    raw_output = models.TextField("原始输出", blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "仲裁详情"
        ordering = ["-scanned_at"]
        indexes = [models.Index(fields=["cluster", "-scanned_at"])]


class NodeNetworkDetail(models.Model):
    """网络接口详情 — ip link / ip addr 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="network_details", null=True, blank=True)

    name = models.CharField("接口名", max_length=64)
    mac_address = models.CharField("MAC地址", max_length=32, blank=True)
    mtu = models.IntegerField("MTU", null=True, blank=True)
    state = models.CharField("状态", max_length=16, blank=True, help_text="UP / DOWN")
    speed_mbps = models.IntegerField("速率(Mbps)", null=True, blank=True)

    # IP 地址列表
    ipv4_addresses = models.JSONField("IPv4地址", default=list, blank=True)
    ipv6_addresses = models.JSONField("IPv6地址", default=list, blank=True)

    # 统计信息
    rx_bytes = models.BigIntegerField("接收字节", null=True, blank=True)
    tx_bytes = models.BigIntegerField("发送字节", null=True, blank=True)
    rx_errors = models.IntegerField("接收错误", null=True, blank=True)
    tx_errors = models.IntegerField("发送错误", null=True, blank=True)

    raw_data = models.JSONField("原始数据", default=dict, blank=True)
    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "网络接口详情"
        unique_together = ("node", "name", "scanned_at")
        ordering = ["node", "name"]
        indexes = [models.Index(fields=["node", "-scanned_at"])]


class NodeKernelErrors(models.Model):
    """内核错误日志 — dmesg 采集"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="kernel_errors", null=True, blank=True)

    level = models.CharField("日志级别", max_length=16, help_text="err / warn")
    subsystem = models.CharField("子系统", max_length=128, blank=True,
        help_text="如 pci / ata / usb / memory")
    message = models.TextField("错误信息")
    timestamp = models.CharField("内核时间戳", max_length=64, blank=True)
    raw_line = models.TextField("原始日志行")

    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "内核错误日志"
        ordering = ["-scanned_at"]
        indexes = [models.Index(fields=["node", "subsystem", "-scanned_at"])]


class NodeShellCommandLog(models.Model):
    """通用 Shell 命令执行日志"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name="shell_logs", null=True, blank=True)

    command_name = models.CharField("命令标识", max_length=64, db_index=True)
    command = models.CharField("完整命令", max_length=512)
    exit_code = models.IntegerField("退出码", default=0)
    duration_ms = models.IntegerField("执行耗时(ms)", null=True, blank=True)
    output_size_bytes = models.IntegerField("输出大小(B)", null=True, blank=True)
    parsed_data = models.JSONField("解析数据", default=dict, blank=True)
    raw_output = models.TextField("原始输出", blank=True)
    error_message = models.TextField("错误信息", blank=True)

    scanned_at = models.DateTimeField("采集时间", db_index=True)

    class Meta:
        verbose_name = "Shell命令日志"
        unique_together = ("node", "command_name", "scanned_at")
        ordering = ["-scanned_at"]
        indexes = [models.Index(fields=["node", "command_name", "-scanned_at"])]
```

### 4.2 存储策略

| 模型 | unique_together | 更新策略 | 保留天数 | 说明 |
|------|----------------|---------|---------|------|
| NodeBenchResult | — | 历史追加 | 30 天 | 看性能趋势 |
| NodeSoftwareVersion | (node,) | **原地更新** | — | 版本不常变 |
| NodeHardwareInfo | (node,) | **原地更新** | — | 硬件信息不变 |
| NodeZFSStatus | (node, pool_name, scanned_at) | 历史追加 | 7 天 | 看 ZFS 变化趋势 |
| NodeQuorumDetail | — | 历史追加 | 7 天 | 仲裁变化监控 |
| NodeNetworkDetail | (node, name, scanned_at) | 历史追加 | 7 天 | 网络统计趋势 |
| NodeKernelErrors | — | 历史追加 | 30 天 | 错误日志需保留 |
| NodeShellCommandLog | (node, command_name, scanned_at) | 历史追加 | 7 天 | 调试用 |

---

## 5. API 端点设计

### 5.1 新增路由（`apps/agent_cli/urls.py`）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/agent-cli/register/` | CLI Agent 注册 | agent_token |
| POST | `/api/agent-cli/heartbeat/` | CLI Agent 心跳 | agent_token |
| POST | `/api/agent-cli/scan/upload/` | CLI 扫描数据上传 | agent_token |
| GET | `/api/agent-cli/tasks/` | 查询下发任务 | agent_token |
| GET | `/api/agent-cli/version/` | 查询最新版本 | 无 |
| GET | `/api/agent-cli/install.sh` | 获取安装脚本 | 无 |

### 5.2 数据上报格式

```json
POST /api/agent-cli/scan/upload/
{
  "agent_id": "cli-hex-uuid",
  "cluster_id": 1,
  "node_name": "pve-1",
  "scanned_at": "2026-07-02T10:00:00Z",

  "pveperf": {
    "cpu_bogomips": 7200.00,
    "cpu_threads": 40,
    "disk_read_mbs": 525.3,
    "disk_write_mbs": 480.1
  },

  "software_version": {
    "proxmox_ve": "7.4-1",
    "kernel": "5.15.102-1-pve",
    "pve_manager": "7.4-3",
    "corosync": "3.1.7-pve1",
    "zfsutils": "2.1.9-pve1",
    "all_packages": {"pve-qemu-kvm": "7.2.0-8", "...": "..."}
  },

  "hardware": {
    "cpu_model": "Intel Xeon E5-2680 v4",
    "cpu_arch": "x86_64",
    "cpu_mhz": 2400.0,
    "cpu_max_mhz": 3200.0,
    "cpu_cache_kb": 35840,
    "cpu_threads": 40,
    "cpu_cores": 20,
    "cpu_sockets": 1,
    "bios_version": "2.14",
    "board_vendor": "Dell Inc.",
    "disks": [
      {
        "device": "/dev/sda",
        "model": "Samsung SSD 860 EVO 500GB",
        "capacity_gb": 500,
        "health": "PASSED",
        "temp_c": 35,
        "power_on_hours": 12000,
        "reallocation_count": 0
      }
    ]
  },

  "zfs": [
    {
      "pool_name": "rpool",
      "health": "ONLINE",
      "size_gb": 480,
      "used_gb": 120,
      "free_gb": 360,
      "vdevs": [{"name": "mirror-0", "type": "mirror", "state": "ONLINE"}],
      "errors": []
    }
  ],

  "quorum": {
    "quorate": true,
    "votes_expected": 5,
    "votes_total": 5,
    "ring_id": "1.11ad",
    "ring_status": [
      {"ring": 0, "status": "OK", "addr": "192.168.1.10", "latency_ms": 0.1}
    ],
    "members": [
      {"nodeid": 1, "name": "pve-1", "ip": "192.168.1.10", "online": true, "votes": 1}
    ]
  },

  "network_details": [
    {
      "name": "vmbr0",
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "mtu": 1500,
      "state": "UP",
      "ipv4_addresses": ["192.168.1.10/24"],
      "rx_bytes": 1234567890,
      "tx_bytes": 9876543210
    }
  ],

  "kernel_errors": [
    {
      "level": "err",
      "subsystem": "pci",
      "message": "pcieport 0000:00:01.0: AER: Corrected error received",
      "timestamp": "[12345.678]"
    }
  ],

  "shell_logs_summary": {
    "total_commands": 8,
    "successful": 7,
    "failed": 1,
    "total_duration_ms": 15200
  }
}
```

---

## 6. Agent 设计

### 6.1 文件结构

```
agent/
├── agent.py                  # 现有 API Agent
├── cli_agent.py              # 新 CLI Agent（主入口）
├── cli_collector.py          # 命令采集器（执行 + 解析）
├── cli_config.py             # 配置管理
└── cli_parser.py             # 命令输出解析器
```

### 6.2 核心流程

```
cli_agent.py main()
  │
  ├── 1. 加载配置 (config.env)
  ├── 2. 注册到平台 POST /api/agent-cli/register/
  ├── 3. 启动心跳线程 (每 120s)
  │     └── POST /api/agent-cli/heartbeat/
  │           ├── 收到 410 → _stop_permanently()
  │           └── 收到 update.available → 自动更新
  │
  └── 4. 启动采集循环 (每 3600s)
        │
        ├── 采集集群级命令（一次/集群）
        │   ├── pvecm status → 解析仲裁状态
        │   ├── corosync-quorumtool -s → 解析环路详情
        │   └── (从任意节点采集即可，数据相同)
        │
        ├── 采集节点级命令（每节点）
        │   ├── pveperf → 解析 CPU/磁盘性能
        │   ├── pveversion -v → 解析组件版本
        │   ├── lscpu --json → 解析 CPU 硬件详情
        │   ├── smartctl -H → 解析磁盘健康
        │   ├── zpool status → 解析 ZFS 状态
        │   ├── zpool iostat → 解析 ZFS I/O
        │   ├── ip -j link show → 解析网卡 MAC/MTU
        │   └── dmesg --level=err,warn → 解析内核错误
        │
        ├── 组装上报数据
        └── POST /api/agent-cli/scan/upload/
```

### 6.3 命令采集器设计

```python
class CommandExecutor:
    """安全的命令执行器"""

    def __init__(self, config):
        self.config = config
        self.timeout = 30        # 默认超时
        self.max_output = 512 * 1024  # 512KB 输出限制

    def execute(self, command_name: str, command: str, timeout: int = None) -> dict:
        """
        执行白名单中的命令，返回结构化结果。

        Returns:
            {
                "command_name": "pveperf",
                "command": "pveperf",
                "exit_code": 0,
                "duration_ms": 1234,
                "raw_output": "...",
                "error": ""
            }
        """
        # 1. 白名单校验
        if command_name not in ALLOWED_COMMANDS:
            raise PermissionError(f"Command not in whitelist: {command_name}")

        # 2. 执行命令
        timeout = timeout or ALLOWED_COMMANDS[command_name].get("timeout", 30)
        start = time.time()
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout
        )
        duration_ms = int((time.time() - start) * 1000)

        # 3. 输出截断
        output = result.stdout[:self.max_output]

        return {
            "command_name": command_name,
            "command": command,
            "exit_code": result.returncode,
            "duration_ms": duration_ms,
            "raw_output": output,
            "error": result.stderr[:4096] if result.stderr else "",
        }
```

### 6.4 输出解析器设计

```python
class PveperfParser:
    """解析 pveperf 输出"""
    @staticmethod
    def parse(raw_output: str) -> dict:
        """
        输入:
        CPU BOGOIPS/SEC   18768.64 (4692.16 x 4.0)
        HD 0 OpenMbrSeq   493484.00 (4.93 MB/sec)
        HD 1 SeqReadMbr   525655.04 (5.26 MB/sec)
        HD 1 SeqWriteMbr  480225.28 (4.80 MB/sec)

        输出:
        {"cpu_bogomips": 18768.64, "cpu_threads": 4, "disk_read_mbs": 5.26, "disk_write_mbs": 4.80}
        """
        result = {}
        for line in raw_output.strip().splitlines():
            if "CPU BOGOIPS" in line:
                match = re.search(r"([\d.]+)\s+\((\d+)\s+x\s+(\d+\.?\d*)\)", line)
                if match:
                    result["cpu_bogomips"] = float(match.group(1))
                    result["cpu_threads"] = int(match.group(3))
            elif "SeqReadMbr" in line:
                match = re.search(r"([\d.]+)\s+\(([\d.]+)\s+MB/sec\)", line)
                if match:
                    result["disk_read_mbs"] = float(match.group(2))
            elif "SeqWriteMbr" in line:
                match = re.search(r"([\d.]+)\s+\(([\d.]+)\s+MB/sec\)", line)
                if match:
                    result["disk_write_mbs"] = float(match.group(2))
        return result


class PveversionParser:
    """解析 pveversion -v 输出"""
    @staticmethod
    def parse(raw_output: str) -> dict:
        """
        输入:
        proxmox-ve: 7.4-1 (running kernel: 5.15.102-1-pve)
        pve-manager: 7.4-3 (running version: 7.4-3/9002ab8a)
        corosync: 3.1.7-pve1
        ...

        输出:
        {
            "proxmox_ve": "7.4-1",
            "kernel": "5.15.102-1-pve",
            "pve_manager": "7.4-3",
            "corosync": "3.1.7-pve1",
            "all_packages": {"proxmox-ve": "7.4-1", "pve-manager": "7.4-3", ...}
        }
        """
        result = {"all_packages": {}}
        for line in raw_output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # proxmox-ve: 7.4-1 (running kernel: 5.15.102-1-pve)
            match = re.match(r"^([\w\-]+):\s+(.+?)(?:\s+\(.*\))?$", line)
            if match:
                pkg, ver = match.group(1), match.group(2).strip()
                result["all_packages"][pkg] = ver
                # 提取关键组件
                if pkg == "proxmox-ve":
                    result["proxmox_ve"] = ver
                    kernel_match = re.search(r"running kernel:\s+(.+?)\)", line)
                    if kernel_match:
                        result["kernel"] = kernel_match.group(1)
                elif pkg == "pve-manager":
                    result["pve_manager"] = ver
                elif pkg == "corosync":
                    result["corosync"] = ver
                elif pkg == "zfsutils-linux":
                    result["zfsutils"] = ver
                elif pkg == "smartmontools":
                    result["smartmontools"] = ver
        return result


class SmartctlParser:
    """解析 smartctl 输出"""
    @staticmethod
    def parse_device(raw_output: str, device: str) -> dict:
        """
        解析单个磁盘的 smartctl 输出，提取健康/温度/通电时间等。
        """
        result = {"device": device, "health": "UNKNOWN"}
        for line in raw_output.strip().splitlines():
            if "overall-health" in line.lower():
                result["health"] = line.split(":")[-1].strip()
            elif "temperature" in line.lower() and "celsius" in line.lower():
                match = re.search(r"(\d+)\s+Celsius", line)
                if match:
                    result["temp_c"] = int(match.group(1))
            elif "power_on_hours" in line.lower():
                match = re.search(r"(\d+)", line.split(":")[-1])
                if match:
                    result["power_on_hours"] = int(match.group(1))
            elif "model_family" in line.lower() or "device_model" in line.lower():
                result["model"] = line.split(":")[-1].strip()
        return result
```

### 6.5 心跳与版本更新

与现有 API Agent 逻辑一致：

```python
def _heartbeat_loop(self):
    while self._running:
        try:
            resp = self._post("/api/agent-cli/heartbeat/", {
                "agent_id": self.agent_id,
                "status": "online",
                "version": VERSION,
            })
            if resp.get("status_code") == 410:
                self._stop_permanently("集群已删除")
            elif resp.get("update", {}).get("available"):
                self._handle_update(resp["update"])
        except Exception as e:
            logger.error(f"心跳失败: {e}")
        time.sleep(120)
```

---

## 7. 部署设计

### 7.1 安装方式

与现有 API Agent 一致，支持一键安装：

```bash
# 一键安装 CLI Agent
curl -fsSL 'http://platform:8000/api/agent-cli/install.sh?token=<token>&platform=<url>' | bash
```

### 7.2 安装目录

```
/opt/pcs-cli-agent/
├── cli_agent.py           # 主程序
├── cli_collector.py       # 采集器
├── cli_parser.py          # 解析器
├── cli_config.py          # 配置管理
├── config.env             # 配置文件
├── cli_agent.service      # systemd 服务文件
└── cli_agent.log          # 日志
```

### 7.3 配置文件 (config.env)

```env
PLATFORM_URL=http://192.168.1.100:8000
AGENT_TOKEN=cli-xxxxxx
CLUSTER_ID=1
NODE_NAME=pve-1
SCAN_INTERVAL=3600
HEARTBEAT_INTERVAL=120
```

### 7.4 systemd 服务

```ini
[Unit]
Description=PVE CLI Agent (Shell Command Collector)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/pcs-cli-agent/cli_agent.py run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.5 部署矩阵

```
一个 5 节点集群的部署情况：

┌─────────┬───────────┬────────────────────┬──────────────────────┐
│  节点    │ API Agent │ CLI Agent          │ 采集内容              │
├─────────┼───────────┼────────────────────┼──────────────────────┤
│  pve-1  │  ✅ 已有   │  ✅ 部署 CLI Agent  │ 本机性能/硬件/ZFS     │
│  pve-2  │  ✅ 已有   │  ✅ 部署 CLI Agent  │ 本机性能/硬件/ZFS     │
│  pve-3  │  ✅ 已有   │  ✅ 部署 CLI Agent  │ 本机性能/硬件/ZFS     │
│  pve-4  │  ✅ 已有   │  ✅ 部署 CLI Agent  │ 本机性能/硬件/ZFS     │
│  pve-5  │  ✅ 已有   │  ✅ 部署 CLI Agent  │ 本机性能/硬件/ZFS     │
└─────────┴───────────┴────────────────────┴──────────────────────┘

每个节点的两个 Agent 独立运行，互不依赖。
```

---

## 8. 数据保留与清理

沿用现有 Lazy on-upload 清理策略，每次 CLI Agent 上传数据时自动清理过期数据：

| 模型 | 保留天数 | 清理方式 |
|------|---------|---------|
| NodeBenchResult | 30 天 | `scanned_at__lt=cutoff` 批量 DELETE |
| NodeZFSStatus | 7 天 | 同上 |
| NodeQuorumDetail | 7 天 | 同上 |
| NodeNetworkDetail | 7 天 | 同上 |
| NodeKernelErrors | 30 天 | 同上 |
| NodeShellCommandLog | 7 天 | 同上 |
| NodeSoftwareVersion | — | 原地更新，不清理 |
| NodeHardwareInfo | — | 原地更新，不清理 |

---

## 9. 实现计划

### Phase 1: 基础框架
- [ ] 创建 `apps/agent_cli/` app
- [ ] 新增 8 个数据模型
- [ ] 执行 `makemigrations` + `migrate`
- [ ] Agent 基础框架（注册/心跳/上报）

### Phase 2: Agent 采集器
- [ ] 实现 `CommandExecutor`（白名单 + 超时 + 输出限制）
- [ ] 实现各解析器（pveperf / pveversion / smartctl / zpool / dmesg / ip）
- [ ] 实现采集循环

### Phase 3: 后端 API
- [ ] 注册/心跳/上传 API 端点
- [ ] 数据入库逻辑（update_or_create + 历史追加）
- [ ] 过期数据清理逻辑

### Phase 4: 前端展示
- [ ] 节点详情页增加「性能基准」「硬件信息」Tab
- [ ] Dashboard StatCards 增加系统健康度指标
- [ ] 告警中心对接内核错误/磁盘不健康告警

### Phase 5: 安装与部署
- [ ] CLI Agent 安装脚本
- [ ] systemd 服务模板
- [ ] 一键卸载脚本

---

## 10. 风险与注意事项

| 风险项 | 影响 | 缓解措施 |
|--------|------|---------|
| `pveperf` 耗时较长 | 采集阻塞 | 单独线程执行，超时 120s |
| `smartctl` 部分磁盘不支持 | 命令报错 | try/except + exit_code 检查 |
| `zpool` 不存在 | 命令报错 | 检测 exit_code，非 0 跳过 |
| `dmesg` 输出过大 | OOM | `tail -50` + 512KB 截断 |
| 集群级命令每个节点都跑 | 重复数据 | 服务端用 cluster_id 去重，或只在 leader 节点执行 |
| 新旧版本兼容 | API 变化 | CLI Agent 独立版本号，独立安装脚本 |
