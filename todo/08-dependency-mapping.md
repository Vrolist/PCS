# 08 — 依赖链路可视化

> 优先级：P3 | 预估工期：4-5天 | 依赖：VM/存储/网络数据

## 功能描述

在现有网络拓扑图的基础上，增加**资源依赖图**——展示 VM、存储、节点之间的关联关系，识别单点故障和关键路径，可视化 HA 切换路径。

## 核心价值

- 识别单点故障（所有 VM 挂在一个存储上）
- HA 切换路径可视化
- 故障影响范围评估

## 依赖关系模型

```
节点 (Node)
  ├── VM 1 ──→ 存储 A
  ├── VM 2 ──→ 存储 B, 存储 C
  ├── LXC 1 ──→ 存储 A
  └── 网络 ──→ vmbr0 ──→ bond0 ──→ eno1, eno2
  
HA 组:
  ├── VM 1 (firstbox → fourbox 备份节点)
  └── LXC 1 (firstbox → xingbox 备份节点)
```

## 数据来源

| 关系 | 字段 | 模型 |
|------|------|------|
| VM → 节点 | `VM.node` | VM |
| VM → 存储 | `VMConfig.scsi_disks[].storage` | VMConfig |
| LXC → 节点 | `LXC.node` | LXC |
| LXC → 存储 | `LXCConfig.rootfs.storage` | LXCConfig |
| 节点 → 网络 | `NetworkInterface.node` | NetworkInterface |
| Bridge → 物理口 | `NetworkInterface.bridge_ports` | NetworkInterface |
| Bond → 从接口 | `NetworkInterface.bond_slaves` | NetworkInterface |
| HA 资源 → 节点 | `HAResource.node_name` | HAResource |
| HA 资源 → 备份节点 | `HAResource.raw_data` | HAResource |

## 前端实现

### 依赖图视图

新增 `views/dependency-graph/index.vue`：

```
┌──────────────────────────────────────┐
│ 🔗 资源依赖图                        │
│ [存储视角] [节点视角] [HA路径]        │
├──────────────────────────────────────┤
│                                      │
│         ┌── VM 111 ──┐              │
│  firstbox── VM 222 ──┤              │
│         ├── CT 150 ──┤── local-lvm  │
│         └── CT 211 ──┘              │
│                                      │
│         ┌── VM 199 ──┐              │
│  fourbox ── CT 198 ──┤── nfs-shared │
│         └── CT 159 ──┘              │
│                                      │
│         ┌── VM 7711 ─┐              │
│  xingbox── CT 211 ───┤── zfs-local  │
│         └── CT 215 ──┘              │
│                                      │
│ ⚠️ local-lvm 仅 firstbox 可用       │
│    若 firstbox 故障，4 台 VM/CT 不可用│
└──────────────────────────────────────┘
```

### 视图模式

1. **存储视角**：中心是存储，周围是 VM/容器，展示存储依赖
2. **节点视角**：中心是节点，展示 VM/容器分布
3. **HA 路径**：展示 HA 资源的故障切换路径

### 可视化技术

- 使用 **D3.js force-directed graph** 或 **vis-network** 库
- 节点用不同形状/颜色区分（VM=方块, 存储=圆, 节点=大圆）
- 连线表示依赖，粗细表示权重
- 悬停显示详情
- 点击节点高亮其所有依赖

## 风险检测

### 单点故障识别

```python
def detect_single_points_of_failure(cluster_id):
    """找出所有 VM/容器都依赖同一存储的节点"""
    # 统计每个存储被多少资源使用
    storage_usage = defaultdict(list)
    for vm in VM.objects.filter(node__cluster_id=cluster_id):
        for disk in vm.configs.first().scsi_disks:
            storage_usage[disk['storage']].append(vm.name)
    
    # 如果某个存储只有 1 个节点能访问，且有 >2 个资源使用它
    for storage, resources in storage_usage.items():
        nodes = get_nodes_for_storage(storage)
        if len(nodes) == 1 and len(resources) > 2:
            yield {
                "type": "single_point_of_failure",
                "storage": storage,
                "node": nodes[0],
                "affected_resources": resources
            }
```

## 注意事项

- 依赖图数据量可能较大（3 节点 x 多 VM），需要按集群过滤
- D3.js 力导向图在 >100 节点时需要性能优化
- 首选 vis-network 库（更简单，内置布局算法）
- 可以先做简化版（树状图），再迭代为交互式力导向图
