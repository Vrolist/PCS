# 10 — 告警自动修复建议

> 优先级：P1 | 预估工期：3-4天 | 依赖：DetectionResult + PVE API

## 功能描述

检测结果不只展示告警，还给出**一键修复命令**。根据告警类型自动推荐修复操作，并可对接 PVE API 实现半自动修复（预览 → 确认 → 执行）。

## 核心价值

- 从"发现问题"到"解决问题"闭环
- 降低运维门槛，新手也能处理告警
- 减少平均修复时间 (MTTR)

## 告警 → 修复映射

| 告警类型 | 修复建议 | 自动化程度 |
|---------|---------|-----------|
| 节点 CPU 过载 | 迁移高负载 VM 到其他节点 | 半自动（预览迁移方案） |
| 存储空间不足 | 清理快照/模板/ISO | 推荐清理列表 |
| HA 重启过多 | 检查节点日志、重启 corosync | 推荐诊断命令 |
| VM 内存溢出 | 扩容内存或启用 Balloon | 推荐配置变更 |
| Ceph OSD 异常 | 重启 OSD / 标记 out | 推荐操作步骤 |
| PVE 版本过旧 | 升级计划建议 | 仅建议（风险高） |
| 网络 IP 冲突 | 修改冲突 IP | 推荐修改方案 |
| IO 延迟过高 | 检查磁盘健康/迁移存储 | 推荐诊断命令 |

## 后端实现

### 新增 API

```
GET /api/scanner/remediation-suggestions/?cluster_id=X
POST /api/scanner/remediation-execute/  # 执行修复（需确认）
```

### 修复建议生成

```python
class RemediationEngine:
    """根据检测结果生成修复建议"""
    
    REMEDIATION_MAP = {
        "cpu_overload": {
            "title": "CPU 过载修复",
            "steps": [
                {
                    "action": "identify_migrate_candidates",
                    "description": "找出可迁移的 VM",
                    "command": None,  # 计算型操作
                },
                {
                    "action": "preview_migration",
                    "description": "预览迁移方案",
                    "command": "qm migrate {vmid} {target_node} --online",
                    "dry_run": True,
                }
            ]
        },
        "disk_full": {
            "title": "磁盘空间不足修复",
            "steps": [
                {
                    "action": "list_cleanable_snapshots",
                    "description": "列出可清理的快照",
                },
                {
                    "action": "list_old_templates",
                    "description": "列出可删除的模板",
                },
                {
                    "action": "list_old_isos",
                    "description": "列出可清理的 ISO",
                }
            ]
        },
        "ha_restart_loop": {
            "title": "HA 重启循环修复",
            "steps": [
                {
                    "action": "check_logs",
                    "description": "查看 HA 资源日志",
                    "command": "ha-manager status",
                },
                {
                    "action": "check_node_health",
                    "description": "检查所在节点健康状态",
                    "command": "pveversion -v && journalctl -u pve-ha-lrm --since '1 hour ago'",
                }
            ]
        }
    }
```

### PVE API 对接（半自动修复）

```python
async def preview_vm_migration(vmid, target_node):
    """预览迁移方案（不执行）"""
    # 调用 PVE API 获取 VM 当前状态
    vm_info = await pve_api.get(f"/nodes/{source_node}/qemu/{vmid}/status/current")
    config = await pve_api.get(f"/nodes/{source_node}/qemu/{vmid}/config")
    
    return {
        "vmid": vmid,
        "name": vm_info["name"],
        "current_node": source_node,
        "target_node": target_node,
        "is_online": vm_info["status"] == "running",
        "estimated_downtime": estimate_downtime(config),
        "disk_size_gb": sum(d["size_gb"] for d in config["scsi_disks"]),
        "command": f"qm migrate {vmid} {target_node} --online"
    }
```

## 前端实现

### 告警修复面板

在告警中心 (`AlertList.vue`) 增加修复入口：

```
┌──────────────────────────────────────┐
│ 🔧 修复建议                          │
├──────────────────────────────────────┤
│ ❌ VM 199 CPU 使用率 95%             │
│ 可能原因: 单 VM 负载过高             │
│                                      │
│ 修复方案:                            │
│ 方案1: 迁移 VM 199 到 fourbox        │
│   预计影响: 在线迁移，暂停 ~30s      │
│   命令: qm migrate 199 fourbox      │
│   [预览] [执行迁移]                  │
│                                      │
│ 方案2: 增加 CPU 核心数              │
│   当前: 4核 → 建议: 8核             │
│   [预览配置] [应用变更]              │
├──────────────────────────────────────┤
│ ⚠️ 存储 local-lvm 使用率 92%        │
│                                      │
│ 可清理项:                            │
│ • 快照 VM 215 snap-20260315 (3.2GB) │
│ • 模板 Debian12 (8GB)               │
│ • ISO old-win10.iso (5.7GB)         │
│                                      │
│ 共可释放: 16.9 GB                    │
│ [选择清理] [导出脚本]                │
└──────────────────────────────────────┘
```

### 执行确认流程

```
1. 用户点击 [预览] → 显示执行前状态
2. 用户点击 [执行] → 弹出二次确认
3. 确认后 → 调用 PVE API 执行
4. 执行结果 → 实时更新状态
```

## 注意事项

- **所有执行操作必须经过用户确认**，不能自动执行
- PVE API 对接需要集群配置了 API Token（在 Cluster 模型中）
- 在线迁移有前提条件：目标节点有足够资源、共享存储等
- 危险操作（如删除 VM）需要二次确认 + 输入名称验证
- 修复执行后记录操作日志（`UserLog`）
