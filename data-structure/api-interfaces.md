# PVE API 接口参考

## 1. API 基础

| 项目 | 说明 |
|------|------|
| 基础 URL | `https://{pve-host}:8006/api2/json/` |
| 认证 | `POST /api2/json/access/ticket` → 获取 `PVEAuthCookie` + `CSRFPreventionToken` |
| 数据格式 | 所有端点返回 JSON，结构: `{"data": {...}}` |
| 认证流程 | 1. POST 获取 ticket → 2. 后续请求 Cookie 携带 ticket → 3. 写操作加 CSRFPreventionToken Header |

---

## 2. 认证端点

### `POST /access/ticket`

获取 API 认证票据。

**请求体：**
```json
{"username": "root@pam", "password": "xxx"}
```

**响应：**
```json
{
  "data": {
    "ticket": "PVE:root@pam:xxxxx...",
    "CSRFPreventionToken": "xxxxx...",
    "username": "root@pam"
  }
}
```

---

## 3. 集群级别端点 (Agent 扫描时调用)

### `GET /cluster/status`

集群状态概览（节点列表、类型、在线状态）。

**返回示例：**
```json
{
  "data": [
    {"id": "cluster/pve-cluster", "type": "cluster", "name": "pve-cluster", "status": "online"},
    {"id": "node/pve1", "type": "node", "name": "pve1", "status": "online", "ip": "192.168.1.10", "local": 1, "nodeid": 1, "online": 1},
    {"id": "node/pve2", "type": "node", "name": "pve2", "status": "online", "ip": "192.168.1.11", "local": 0, "nodeid": 2, "online": 1}
  ]
}
```

### `GET /cluster/resources`

集群所有资源汇总（节点/VM/LXC/存储）。

**参数:** `type` (可选: `vm`, `storage`, `node`, `sdn`)

### `GET /cluster/ceph/status`

Ceph 集群健康状态。

### `GET /cluster/ceph/osd`

Ceph OSD 列表。

### `GET /cluster/ceph/pool`

Ceph 存储池列表。

### `GET /version`

PVE 版本信息。

---

## 4. 节点级别端点 (Agent 按节点调用)

### `GET /nodes`

所有节点列表与资源概览。

### `GET /nodes/{node}/status`

节点详细状态（CPU/内存/磁盘/Swap/磁盘I/O统计/内核/运行时长）。

**返回字段中与 I/O 延迟相关的 `diskstat` 数组：**
```json
{
  "diskstat": [
    {"dev": "sda", "read": 1234567890, "write": 9876543210, "read_ios": 50000, "write_ios": 80000, "io_ms": 12.5}
  ]
}
```
- `io_ms`: I/O 等待时间（毫秒），即该磁盘设备的 I/O 延迟

### `GET /nodes/{node}/config`

节点配置（主机名、时区、SSH Key、DNS 等）。

### `GET /nodes/{node}/qemu`

VM 列表（含实时性能数据）。

**参数:** `full` (0/1, 默认0) — 为 1 时返回更详细的 balloon/network 数据。

### `GET /nodes/{node}/qemu/{vmid}/status/current`

单个 VM 的详细实时状态。

### `GET /nodes/{node}/qemu/{vmid}/config`

单个 VM 的完整配置（硬件定义）。

### `GET /nodes/{node}/qemu/{vmid}/snapshot`

VM 快照列表。

### `GET /nodes/{node}/lxc`

LXC 容器列表（含实时性能数据）。

### `GET /nodes/{node}/lxc/{vmid}/status/current`

单个容器的详细实时状态。

### `GET /nodes/{node}/lxc/{vmid}/config`

单个容器的完整配置。

### `GET /nodes/{node}/storage`

节点可访问的存储列表。

### `GET /nodes/{node}/storage/{storage}/content`

存储中的内容（卷/ISO/模板等）。

### `GET /nodes/{node}/network`

节点网络接口配置。

### `GET /nodes/{node}/ceph`

节点 Ceph 状态（OSD 数量、CRUSH 配置）。

---

## 5. 数据字段类型说明

| 类型 | 说明 |
|------|------|
| string | 字符串 |
| integer | 整数，存储容量单位为 **bytes** |
| float | 浮点数，CPU 负载范围为 0~1 |
| array | 数组 |
| object | 对象/字典 |

**单位转换规则：**
- 内存: PVE 返回 bytes, 数据库存储 MB (÷ 1048576)
- 磁盘/存储: PVE 返回 bytes, 数据库存储 GB (÷ 1073741824)
- CPU 负载: PVE 返回 0~1 float, 数据库存储百分比 (× 100)
- 网络流量: PVE 返回 bytes/s, 数据库直接存储 bps

---

## 6. Agent 扫描流程

```
Agent 启动
  │
  ├─ POST /access/ticket → 获取 ticket
  │
  ├─ GET /version → 保存集群版本
  │
  ├─ GET /cluster/status → 获取节点列表
  │
  ├─ for each node:
  │   ├─ GET /nodes/{node}/status → 节点状态
  │   ├─ GET /nodes/{node}/config → 节点配置
  │   ├─ GET /nodes/{node}/qemu → VM 列表
  │   ├─ GET /nodes/{node}/lxc → LXC 列表
  │   ├─ GET /nodes/{node}/storage → 存储列表
  │   └─ GET /nodes/{node}/network → 网络接口
  │
  ├─ GET /cluster/ceph/status → Ceph 状态 (如果有 Ceph)
  │
  └─ POST /api/agent/scan/upload/ → 上传扫描结果
```
