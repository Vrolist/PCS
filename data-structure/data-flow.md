# 数据流架构

## 1. 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    PVE 集群                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Node 1  │  │  Node 2  │  │  Node 3  │          │
│  │ (Agent)  │  │ (Agent)  │  │ (Agent)  │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │             │             │                │
│       └─────────────┼─────────────┘                │
│                     │ PVE API (HTTPS :8006)         │
└─────────────────────┼──────────────────────────────┘
                      │
              ┌───────┴────────┐
              │   Agent CLI    │  ← Python CLI 工具，部署在 PVE 节点上
              │ (pve-agent)    │     或独立服务器上
              └───────┬────────┘
                      │ HTTP (REST API)
                      ▼
┌─────────────────────────────────────────────────────┐
│              PVE 集群扫描平台 (Django)               │
│                                                     │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │  认证 API   │    │     Agent API             │    │
│  │ /api/auth/  │    │  /api/agent/register/    │    │
│  │             │    │  /api/agent/heartbeat/   │    │
│  │             │    │  /api/agent/scan/upload/ │    │
│  │             │    │  /api/agent/tasks/       │    │
│  └─────────────┘    └──────────┬───────────────┘    │
│                                │                    │
│  ┌─────────────────────────────▼──────────────────┐ │
│  │              scanner 数据入库层                 │ │
│  │  ClusterNode / VM / LXC / Storage / NetIf      │ │
│  │  CephStatus / ScanHistory / DetectionResult    │ │
│  └─────────────────────┬──────────────────────────┘ │
│                        │                            │
│  ┌─────────────────────▼──────────────────────────┐ │
│  │               Web API (DRF)                     │ │
│  │  GET /api/dashboard/stats/                     │ │
│  │  GET /api/dashboard/trend/                     │ │
│  │  GET /api/clusters/                            │ │
│  │  GET /api/clusters/{id}/nodes/                 │ │
│  │  ...                                           │ │
│  └─────────────────────┬──────────────────────────┘ │
│                        │                            │
└────────────────────────┼────────────────────────────┘
                         │ JSON
                         ▼
              ┌───────────────────┐
              │   Vue 3 前端      │
              │  (Element Plus)   │
              │  仪表盘 / 集群管理 │
              │  节点 / VM / LXC  │
              └───────────────────┘
```

---

## 2. Agent 数据采集流程

```
Agent 启动
  │
  ├── 1. 注册 /api/agent/register/
  │     → 返回 agent_id
  │
  ├── 2. 进入心跳循环 (每 N 秒)
  │     └── POST /api/agent/heartbeat/
  │         → 更新在线状态
  │
  ├── 3. 扫描触发 (定时 / 手动下发)
  │     │
  │     ├── 3.1 POST PVE API /access/ticket
  │     │     → 获取认证票据
  │     │
  │     ├── 3.2 GET PVE API /version
  │     │     → 获取 PVE 版本
  │     │
  │     ├── 3.3 GET PVE API /cluster/status
  │     │     → 获取节点列表
  │     │
  │     ├── 3.4 遍历每个节点
  │     │     ├── GET /nodes/{node}/status → 节点状态
  │     │     ├── GET /nodes/{node}/qemu → VM 列表
  │     │     ├── GET /nodes/{node}/lxc → LXC 列表
  │     │     ├── GET /nodes/{node}/storage → 存储
  │     │     └── GET /nodes/{node}/network → 网络
  │     │
  │     ├── 3.5 GET /cluster/ceph/status (if applicable)
  │     │     → Ceph 健康状态
  │     │
  │     ├── 3.6 数据清洗 & 单位转换
  │     │     → bytes → MB/GB
  │     │     → CPU 0~1 → 百分比
  │     │
  │     └── 3.7 POST /api/agent/scan/upload/
  │           → 上传扫描数据 (JSON)
  │
  └── 4. 检查下发任务
        └── GET /api/agent/tasks/
            → 执行管理端下发的任务
```

---

## 3. 数据上传格式

Agent 扫描完成后，通过 `POST /api/agent/scan/upload/` 上传数据，格式如下：

```json
{
  "agent_id": "uuid-string",
  "cluster_id": "cluster-uuid",
  "scanned_at": "2026-06-29T10:30:00Z",
  "version": "pve-manager/8.2.4",
  "nodes": [
    {
      "name": "pve-1",
      "status": "online",
      "pve_version": "pve-manager/8.2.4/...",
      "kernel_version": "Linux 6.8.8-1-pve",
      "cpu_model": "AMD EPYC 7443P 24-Core Processor",
      "cpu_cores": 48,
      "cpu_sockets": 2,
      "cpu_load": 0.35,
      "memory_total_mb": 131072,
      "memory_used_mb": 65536,
      "memory_free_mb": 65536,
      "rootfs_total_gb": 100.0,
      "rootfs_used_gb": 45.2,
      "rootfs_avail_gb": 54.8,
      "swap_total_mb": 4096,
      "swap_used_mb": 128,
      "ip_address": "192.168.1.10",
      "uptime_seconds": 1209600,
      "is_ceph_node": true,
      "vms": [
        {
          "vmid": 100,
          "name": "web-server-01",
          "status": "running",
          "cpu_cores": 4,
          "cpu_usage": 0.25,
          "memory_mb": 8192,
          "memory_used_mb": 4096,
          "disk_gb": 50.0,
          "max_disk_gb": 100.0,
          "net_in_bps": 1048576,
          "net_out_bps": 524288,
          "uptime_seconds": 604800,
          "os_type": "l26",
          "tags": "production,web"
        }
      ],
      "containers": [
        {
          "vmid": 200,
          "name": "redis-cache",
          "status": "running",
          "cpu_cores": 2,
          "cpu_usage": 0.15,
          "memory_mb": 2048,
          "memory_used_mb": 1024,
          "disk_gb": 20.0,
          "uptime_seconds": 86400,
          "tags": "production,cache"
        }
      ],
      "storages": [
        {
          "name": "local",
          "type": "dir",
          "active": true,
          "used_gb": 500.0,
          "avail_gb": 1500.0,
          "total_gb": 2000.0,
          "used_fraction": 0.25,
          "content_types": "images,rootdir,vztmpl,iso",
          "shared": false
        }
      ],
      "networks": [
        {
          "name": "vmbr0",
          "type": "bridge",
          "active": true,
          "method": "static",
          "address": "192.168.1.10/24",
          "gateway": "192.168.1.1",
          "speed_mbps": 10000
        }
      ]
    }
  ],
  "ceph": {
    "health": "HEALTH_OK",
    "total_osds": 12,
    "up_osds": 12,
    "in_osds": 12,
    "pool_count": 4,
    "total_used_gb": 2048.0,
    "total_avail_gb": 6144.0,
    "total_space_gb": 8192.0
  }
}
```

---

## 4. 服务端处理流程

```
POST /api/agent/scan/upload/
  │
  ├── 1. 验证 Agent 身份 (agent_token)
  │
  ├── 2. 创建 ScanTask 记录 (status= running)
  │
  ├── 3. 更新 Cluster 汇总字段
  │     (total_nodes, total_vms, total_lxc, total_storage)
  │
  ├── 4. 批量创建/更新 ClusterNode
  │
  ├── 5. 批量创建/更新 VM
  │
  ├── 6. 批量创建/更新 LXC
  │
  ├── 7. 批量创建/更新 Storage
  │
  ├── 8. 批量创建/更新 NetworkInterface
  │
  ├── 9. 创建/更新 CephStatus
  │
  ├── 10. 创建 ScanHistory 快照
  │
  ├── 11. 触发自动检测引擎 (DetectionRule → DetectionResult)
  │
  └── 12. 更新 ScanTask (status= completed)
```

---

## 5. 前端数据流

```
Vue Router 进入仪表盘
  │
  ├── GET /api/dashboard/stats/
  │     → 统计卡片数据 (总集群/节点/VM/告警数)
  │
  ├── GET /api/dashboard/trend/?days=7
  │     → 趋势图表数据 (ScanHistory 聚合)
  │
  ├── GET /api/nodes/?limit=10
  │     → 节点详情表格
  │
  └── GET /api/alerts/?limit=5
        → 最近告警列表
```
