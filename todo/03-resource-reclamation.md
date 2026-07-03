# 03 — 资源回收建议

> 优先级：P0 | 预估工期：2-3天 | 依赖：VM/LXC/Snapshot 现有数据

## 功能描述

自动扫描集群中的"僵尸资源"——长时间停止的 VM/容器、堆积的旧快照、未使用的存储卷、孤立模板等，计算可回收空间，生成清理建议报告。

## 核心价值

- 释放被浪费的存储空间
- 降低管理复杂度
- 减少快照导致的性能影响

## 检测规则

### 僵尸 VM/容器

| 规则 | 条件 | 建议 |
|------|------|------|
| 长期停机 | `status=stopped` 且 `uptime_seconds < 60`，持续 >30 天 | 确认后删除 |
| 闲置模板 | `has_template=true` 且无其他 VM 从此模板创建 | 确认后删除模板 |
| 零使用 VM | CPU/内存使用率持续 <1%，持续 >14 天 | 评估是否需要 |

### 快照清理

| 规则 | 条件 | 建议 |
|------|------|------|
| 旧快照堆积 | 同一 VM 快照 >10 个 | 保留最近 3 个，清理其余 |
| 超旧快照 | `snap_time` >90 天 | 评估是否仍需要 |
| 保存内存快照 | `ram=true` 的旧快照（占用大） | 优先清理 |

### 存储回收

| 规则 | 条件 | 建议 |
|------|------|------|
| 空闲存储卷 | storage 中无 VM/容器使用 | 检查是否可卸载 |
| ISO 镜像堆积 | content_types 含 iso，使用量 <5% | 清理过期 ISO |

## 后端实现

### 新增 API

```
GET /api/scanner/resource-reclaim/?cluster_id=X
```

返回结构：
```json
{
  "reclaimable_space_gb": 156.8,
  "items": [
    {
      "category": "stopped_vm",
      "resource": "VM 7711 (Win11-P620)",
      "node": "xingbox",
      "detail": "已停止 45 天，占用 128GB",
      "reclaimable_gb": 128,
      "risk_level": "low",
      "suggestion": "确认业务不再需要后可删除"
    },
    {
      "category": "old_snapshot",
      "resource": "VM 111 (ikuai32) - snap_old",
      "node": "firstbox",
      "detail": "创建于 2026-03-15，已 110 天",
      "reclaimable_gb": 2.3,
      "risk_level": "low",
      "suggestion": "旧快照，建议清理"
    },
    {
      "category": "orphaned_template",
      "resource": "VM 100 (Debian12-Template)",
      "node": "firstbox",
      "detail": "模板，0 个 VM 从此模板创建",
      "reclaimable_gb": 8,
      "risk_level": "medium",
      "suggestion": "无关联 VM，确认后可删除"
    }
  ],
  "summary": {
    "stopped_vms": { "count": 3, "space_gb": 140 },
    "old_snapshots": { "count": 12, "space_gb": 8.5 },
    "orphaned_templates": { "count": 1, "space_gb": 8 }
  }
}
```

## 前端实现

### 资源回收页面

新增 `views/resource-reclaim/index.vue`：

```
┌──────────────────────────────────────┐
│ ♻️ 资源回收建议                      │
│                                      │
│ 可回收空间: 156.8 GB                 │
│ ██████████████░░░░░░ 39% 存储可回收  │
├──────────────────────────────────────┤
│ ⚠️ 停止的 VM (3台, 140GB)           │
│ ┌──────────────────────────────────┐ │
│ │ VM 7711 Win11-P620   128GB 45天 │ │
│ │ VM 9001 Test-Lab      8GB  30天 │ │
│ └──────────────────────────────────┘ │
│                                      │
│ 📸 旧快照 (12个, 8.5GB)             │
│                                      │
│ 📋 孤立模板 (1个, 8GB)              │
│                                      │
│ [导出清理建议]  [一键导出脚本]        │
└──────────────────────────────────────┘
```

### 导出功能

- 导出 Markdown 报告（适合分享）
- 导出 PVE Shell 脚本（需人工确认后执行）

```bash
# 自动生成的清理脚本（预览模式）
echo "=== 资源回收脚本 ==="
echo "# VM 7711 (已停止45天) - 需确认"
# qm stop 7711 2>/dev/null
# qm destroy 7711 2>/dev/null
```

## 注意事项

- 所有删除操作**仅提供建议**，不自动执行
- 导出的脚本默认注释，需人工取消注释后执行
- 风险分级：low（停机 VM）/ medium（模板）/ high（运行中资源）
- 回收建议基于扫描快照数据，不是实时数据
