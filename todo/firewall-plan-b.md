# 防火墙功能 — 方案 B：完整方案（含在线编辑）

> 方案 A（只读展示）已实现。本方案在 A 基础上增加规则的在线创建/修改/删除能力。

## 架构设计

### 整体思路

```
Web 前端（编辑规则表单）
  → Django API（权限校验 + 入库）
    → Agent 下发任务（task_type=firewall_apply）
      → Agent 调用 PVE API（POST/PUT/DELETE）
        → 结果回传
```

**关键约束**：防火墙配置的写入必须通过 PVE API，而 PVE API 需要在集群节点本地调用。因此写操作必须通过 Agent 转发，不能由 Django 直接调用。

### 数据流

```
读取（已有方案A）:
  PVE API → Agent 采集 → Django 入库 → Web API → 前端展示

写入（方案B新增）:
  前端编辑 → Django API 存储待下发规则 → Agent 心跳拉取任务
  → Agent 执行 PVE API 写入 → Agent 上报结果 → Django 更新状态
```

## 新增模型

### 1. FirewallPendingTask（待下发的防火墙操作任务）

```python
class FirewallPendingTask(models.Model):
    """待下发的防火墙配置变更任务"""
    class Action(models.TextChoices):
        CREATE = "create", "创建"
        UPDATE = "update", "修改"
        DELETE = "delete", "删除"
        ENABLE = "enable", "启用"
        DISABLE = "disable", "禁用"

    class Target(models.TextChoices):
        RULE = "rule", "规则"
        IPSET = "ipset", "IPSet"
        IPSET_ENTRY = "ipset_entry", "IPSet条目"
        ALIAS = "alias", "别名"
        OPTIONS = "options", "选项"
        SECURITY_GROUP = "security_group", "安全组"

    class Status(models.TextChoices):
        PENDING = "pending", "待下发"
        SENT = "sent", "已下发"
        SUCCESS = "success", "成功"
        FAILED = "failed", "失败"

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    action = models.CharField(max_length=16, choices=Action.choices)
    target = models.CharField(max_length=32, choices=Target.choices)

    # 目标定位
    scope = models.CharField(max_length=16)  # cluster / node / vm / ct
    node_name = models.CharField(max_length=128, blank=True)
    vmid = models.IntegerField(null=True, blank=True)
    group_name = models.CharField(max_length=64, blank=True)
    pos = models.IntegerField(null=True, blank=True)  # 规则位置

    # 负载数据（JSON，含规则字段/选项字段等）
    payload = models.JSONField(default=dict)

    # 状态
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    assigned_agent = models.ForeignKey(AgentInstance, on_delete=models.SET_NULL, null=True)
    error_message = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2. Agent 任务扩展

在 `GET /api/agent/tasks/` 响应中增加 `firewall_apply` 类型任务：

```json
[
  {
    "id": 42,
    "task_type": "firewall_apply",
    "payload": {
      "pending_task_id": 42,
      "action": "create",
      "target": "rule",
      "scope": "cluster",
      "data": {
        "action": "ACCEPT",
        "direction": "in",
        "proto": "tcp",
        "dport": "8443",
        "source": "10.0.0.0/8",
        "comment": "允许内网访问管理端口",
        "enabled": true
      }
    },
    "status": "pending"
  }
]
```

### 3. Agent 执行逻辑

Agent 新增 `_apply_firewall_task(task)` 方法：

```python
def _apply_firewall_task(self, task):
    """执行防火墙配置变更"""
    payload = task["payload"]
    action = payload["action"]
    target = payload["target"]
    scope = payload["scope"]
    data = payload["data"]

    if target == "rule":
        if scope == "cluster":
            if action == "create":
                self.pve.post("/cluster/firewall/rules", data)
            elif action == "update":
                self.pve.put(f"/cluster/firewall/rules/{data['pos']}", data)
            elif action == "delete":
                self.pve.delete(f"/cluster/firewall/rules/{data['pos']}")
        elif scope == "node":
            node = payload["node_name"]
            # 类似路径 /nodes/{node}/firewall/rules
        elif scope in ("vm", "ct"):
            node = payload["node_name"]
            vmid = payload["vmid"]
            prefix = "qemu" if scope == "vm" else "lxc"
            # /nodes/{node}/{prefix}/{vmid}/firewall/rules

    elif target == "ipset":
        # /cluster/firewall/ipset/{name}
        pass

    elif target == "options":
        # PUT /cluster/firewall/options 或 /nodes/{node}/firewall/options
        pass

    # ... 其他 target 类型
```

## API 端点

### 新增写入 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/scanner/firewall/tasks/` | 创建防火墙变更任务（下发到 Agent） |
| GET | `/api/scanner/firewall/tasks/` | 查询变更任务列表（含状态） |
| DELETE | `/api/scanner/firewall/tasks/:id/` | 取消未下发的任务 |

### 请求示例

```json
// 创建规则
POST /api/scanner/firewall/tasks/
{
  "action": "create",
  "target": "rule",
  "scope": "cluster",
  "payload": {
    "action": "ACCEPT",
    "direction": "in",
    "proto": "tcp",
    "dport": "8443",
    "source": "10.0.0.0/8",
    "comment": "允许内网访问管理端口"
  }
}

// 删除规则
POST /api/scanner/firewall/tasks/
{
  "action": "delete",
  "target": "rule",
  "scope": "cluster",
  "pos": 3
}

// 创建 IPSet 及添加条目
POST /api/scanner/firewall/tasks/
{
  "action": "create",
  "target": "ipset",
  "scope": "cluster",
  "group_name": "management",
  "payload": { "name": "management", "comment": "管理IP池" }
}

// 修改防火墙选项
POST /api/scanner/firewall/tasks/
{
  "action": "update",
  "target": "options",
  "scope": "cluster",
  "payload": { "enable": 1, "policy_in": "DROP", "policy_out": "ACCEPT" }
}
```

## 前端页面扩展

### 规则管理 Tab

- 表格展示规则，每行增加「编辑」「删除」按钮
- 顶部增加「新建规则」按钮
- 规则支持拖拽排序（通过修改 pos 实现）
- 编辑弹窗：方向/动作/协议/源地址/目标端口/注释 等表单字段

### 安全组 Tab

- 列表展示安全组，点击进入安全组详情
- 安全组内规则的 CRUD

### IPSet Tab

- 展示 IPSet 列表，点击展开条目
- 支持添加/删除条目

### 选项 Tab

- 表单方式编辑防火墙选项（开关/默认策略/日志级别）

### 任务状态展示

- 变更任务提交后显示「待下发」状态
- Agent 执行后自动更新为「成功」或「失败」
- 失败时显示错误信息，支持重试

## 实现顺序

1. 新增 `FirewallPendingTask` 模型 + 迁移
2. Agent 端增加 `firewall_apply` 任务执行逻辑 + PVE API PUT/DELETE 方法
3. Django 端增加任务创建/查询/取消 API
4. Agent tasks 响应增加 firewall_apply 类型任务
5. 前端规则编辑 UI（弹窗表单 + 拖拽排序）
6. 前端任务状态实时展示（轮询或 WebSocket）

## 风险与注意事项

1. **并发冲突**：多 Agent 场景下，同一规则可能被多个任务修改。需加锁或乐观锁（版本号）。
2. **回滚**：PVE API 不支持事务，写入失败后需手动回滚。建议每次操作前记录快照。
3. **权限控制**：当前所有登录用户均可编辑防火墙（单用户系统），多用户场景需增加 RBAC。
4. **Agent 可用性**：写操作依赖在线 Agent。若无在线 Agent，前端应提示「无可用 Agent，无法下发」。
5. **PVE API 错误处理**：部分 PVE 版本可能不支持某些防火墙 API（如 nftables forward rules），需兼容处理。
