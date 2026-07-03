# 02 — 变更追踪 (Scan Diff)

> 优先级：P0 | 预估工期：3-4天 | 依赖：ScanHistory 两次扫描数据

## 功能描述

对比相邻两次扫描结果，以可视化方式展示集群资源的变更：新增/删除的 VM/容器、配置变更、节点状态变化。类似 `git diff` 的体验，帮助运维人员快速掌握"发生了什么变化"。

## 核心价值

- 运维审计：谁在什么时候改了什么
- 异常溯源：故障前后的配置差异
- 变更确认：批量操作后的验证

## 数据来源

对比两次 `ScanTask` 对应的全量数据：

| 变更类型 | 数据源 | 检测方式 |
|---------|--------|---------|
| 新增 VM | `VM` 表 | 本次有、上次无 |
| 删除 VM | `VM` 表 | 上次有、本次无 |
| VM 迁移 | `VM.node` | node 外键变化 |
| 内存变更 | `VMConfig.memory_mb` | 值变化 |
| 磁盘变更 | `VMConfig.scsi_disks` | JSON 列表变化 |
| 网卡变更 | `VMConfig.net_devices` | JSON 列表变化 |
| 节点上下线 | `ClusterNode.status` | status 字段变化 |
| 存储变更 | `Storage` 表 | 容量/使用率变化 |

## 后端实现

### 新增 API

```
GET /api/scanner/scan-diff/?cluster_id=X&from_scan_id=Y&to_scan_id=Z
```

返回结构：
```json
{
  "from_scan": { "id": 120, "scanned_at": "2026-07-01T03:00:00Z" },
  "to_scan":   { "id": 121, "scanned_at": "2026-07-02T03:00:00Z" },
  "summary": {
    "total_changes": 8,
    "vm_added": 1,
    "vm_removed": 0,
    "vm_config_changed": 3,
    "node_changed": 1,
    "storage_changed": 2
  },
  "changes": [
    {
      "type": "vm_added",
      "resource": "VM 205 (new-webapp)",
      "node": "fourbox",
      "detail": "CPU: 2核, 内存: 4096MB, 磁盘: 50GB"
    },
    {
      "type": "config_changed",
      "resource": "VM 111 (Win11)",
      "field": "memory_mb",
      "old_value": 8192,
      "new_value": 16384,
      "diff": "+8192 MB"
    },
    {
      "type": "config_changed",
      "resource": "VM 111 (Win11)",
      "field": "scsi_disks",
      "old_value": [{"slot":"scsi0","size":"128G"}],
      "new_value": [{"slot":"scsi0","size":"256G"}],
      "diff": "磁盘扩容 128G → 256G"
    }
  ]
}
```

### 核心逻辑

```python
def compute_scan_diff(scan_a_id, scan_b_id):
    changes = []
    
    # 1. VM 变更检测
    vms_a = set(VM.objects.filter(scan_id=scan_a_id).values_list('vmid', flat=True))
    vms_b = set(VM.objects.filter(scan_id=scan_b_id).values_list('vmid', flat=True))
    
    for vmid in vms_b - vms_a:
        changes.append({"type": "vm_added", ...})
    for vmid in vms_a - vms_b:
        changes.append({"type": "vm_removed", ...})
    
    # 2. VM 配置变更（对交集中的 VM 逐字段对比）
    common_vms = vms_a & vms_b
    for vmid in common_vms:
        config_a = VMConfig.objects.get(vm__vmid=vmid, scan_id=scan_a_id)
        config_b = VMConfig.objects.get(vm__vmid=vmid, scan_id=scan_b_id)
        for field in ['memory_mb', 'cpu_cores', 'scsi_disks', 'net_devices']:
            old = getattr(config_a, field)
            new = getattr(config_b, field)
            if old != new:
                changes.append({"type": "config_changed", "field": field, ...})
    
    # 3. 类似逻辑检测 LXC、存储、节点变更
    ...
    
    return {"summary": summarize(changes), "changes": changes}
```

## 前端实现

### 变更时间线视图

新增 `views/scan-diff/index.vue`：

```
┌──────────────────────────────────────┐
│ 📋 变更追踪                          │
│ 从: [2026-07-01 03:00]              │
│ 到: [2026-07-02 03:00]    [对比]    │
├──────────────────────────────────────┤
│ 变更摘要: 8 项                       │
│ 🟢 +1 VM  🔴 -0 VM  🟡 3 配置变更   │
├──────────────────────────────────────┤
│ ✅ VM 205 (new-webapp) — 新增       │
│    fourbox | 2核/4GB/50GB           │
│                                      │
│ 🔄 VM 111 (Win11) — 配置变更        │
│    内存: 8192 MB → 16384 MB (+100%) │
│    磁盘: 128G → 256G                │
│                                      │
│ 🔄 VM 222 (OpenCut) — 节点迁移      │
│    firstbox → xingbox               │
└──────────────────────────────────────┘
```

### 变更列表页

- 支持按变更类型筛选（新增/删除/配置/迁移）
- 时间选择器（选择对比的两次扫描）
- 变更详情弹窗（展示完整旧/新配置 JSON）

## 注意事项

- 对比粒度控制：VM 级别（哪些变了）+ 字段级别（具体变了什么）
- JSON 字段（scsi_disks, net_devices）需做深度对比，不能只比较字符串
- 扫描间隔建议 ≥5 分钟，避免中间态数据干扰
- 变更记录本身不存数据库（按需计算），避免数据膨胀
