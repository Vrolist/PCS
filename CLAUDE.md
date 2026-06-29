# pve-cluster-scan

PVE 集群扫描与管理平台 — Django 5 + Vue 3 全栈项目。

## 项目架构

```
pve-cluster-scan/
├── config/                 # Django 项目配置
│   ├── settings.py         #   - DRF / JWT / django-vite / CORS
│   └── urls.py             #   - auth 路由 + catch-all → Vue SPA
├── apps/
│   ├── accounts/           # 用户认证 & 套餐管理
│   │   ├── models.py       #   - User / Plan / UserPlan / PasswordResetCode
│   │   ├── serializers.py  #   - Login / Register / User / PasswordReset
│   │   ├── views.py        #   - 登录 / 注册 / 用户信息 / 密码重置
│   │   ├── urls.py         #   - /api/auth/ 路由
│   │   └── admin.py
│   ├── clusters/           # 集群管理（CRUD + Agent 列表）
│   │   ├── models.py       #   - Cluster（含 agent_token）
│   │   ├── serializers.py  #   - List / Create / Detail / AgentBrief
│   │   ├── views.py        #   - 集群 CRUD + Agent 查询
│   │   ├── urls.py         #   - /api/clusters/ 路由
│   │   ├── tests.py        #   - 10 个测试用例
│   │   └── admin.py
│   ├── agent_api/          # Agent 通信 & 多 Agent 管理
│   │   ├── models.py       #   - AgentInstance / ScanTask
│   │   ├── serializers.py  #   - Register / Heartbeat / ScanUpload / Tasks / Unregister / Version
│   │   ├── views.py        #   - 注册 / 心跳 / 扫描上传 / 任务下发 / 卸载 / 版本查询 / 安装脚本
│   │   ├── urls.py         #   - /api/agent/ 路由（7 个端点）
│   │   ├── install_script.py  # install.sh 模板生成
│   │   ├── tests.py        #   - 40 个测试用例
│   │   └── admin.py
│   └── scanner/            # 扫描数据 & 自动检测
├── frontend/               # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue                       # Landing Page
│   │   │   ├── auth/
│   │   │   │   ├── Login.vue                  # 登录（用户名/邮箱通用）
│   │   │   │   ├── Register.vue               # 注册（邮箱必填）
│   │   │   │   └── ForgotPassword.vue         # 找回密码（两步流程）
│   │   │   ├── dashboard/
│   │   │   │   ├── index.vue                  # 控制台主布局
│   │   │   │   ├── StatCards.vue              # 统计卡片组件（水平压缩）
│   │   │   │   ├── AlertList.vue              # 最近告警列表（固定高度+滚动）
│   │   │   │   ├── TrendChart.vue             # 资源趋势 ECharts 折线图
│   │   │   │   └── NodeTable.vue              # 节点详情表格
│   │   │   ├── clusters/index.vue             # 集群管理（空状态+el-card）
│   │   │   ├── nodes/index.vue                # 节点管理（空状态+el-card）
│   │   │   ├── vms/index.vue                  # 虚拟机（空状态+el-card）
│   │   │   ├── containers/index.vue           # 容器（空状态+el-card）
│   │   │   ├── alerts/index.vue               # 告警中心（空状态+el-card）
│   │   │   ├── services/index.vue             # 运维服务（空状态+el-card）
│   │   │   └── settings/index.vue             # 系统设置（空状态+el-card）
│   │   ├── components/
│   │   │   ├── AppSidebar.vue        # 侧边栏导航（含折叠图标居中）
│   │   │   └── AppHeader.vue         # 顶栏（含主题切换）
│   │   ├── layouts/MainLayout.vue    # 后台主布局（侧边栏+顶栏+内容区）
│   │   ├── router/index.ts           # 路由 + 守卫
│   │   ├── stores/
│   │   │   ├── app.ts                # 全局状态（侧边栏折叠）
│   │   │   ├── auth.ts               # JWT 认证
│   │   │   └── theme.ts              # 亮暗主题（默认暗色）
│   │   ├── api/
│   │   │   ├── request.ts            # Axios 实例 + 拦截器
│   │   │   ├── auth.ts               # 登录/注册/密码重置 API
│   │   │   └── clusters.ts           # 集群 CRUD + Agent 查询 API
│   │   └── style.css                 # CSS 变量 / 亮暗色值
│   ├── package.json
│   └── vite.config.ts
├── agent/                    # Agent CLI 工具（独立 Python 包）
│   ├── pyproject.toml          # 打包配置
│   └── agent/
│       ├── __init__.py
│       ├── cli.py              # CLI 入口（click）
│       ├── config.py           # 配置管理（~/.config/pcs-agent/config.yaml）
│       ├── pve_client.py       # PVE API 客户端
│       ├── scanner.py          # 数据采集 + 单位转换
│       ├── uploader.py         # 上报到 Django 平台
│       └── scheduler.py        # 心跳 + 扫描调度器
├── data-structure/           # PVE 数据结构分析文档
│   ├── README.md             # 分析说明与 License 声明
│   ├── database-models.md    # 数据库模型与 PVE 字段映射
│   ├── api-interfaces.md     # PVE API 接口清单
│   ├── field-mapping.md      # 字段对照表
│   ├── data-flow.md          # 数据采集与入库流程
│   └── agent-design.md       # Agent 设计文档（架构/命令/安装/通信）
├── templates/
│   └── vue_index.html                # Django 模板（django-vite 入口）
├── static/                           # Vite 构建输出
├── manage.py
├── dev_start.sh                      # 一键启动（Django + Vite）
└── CLAUDE.md
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + Django 5.0 + DRF |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Element Plus + Pinia + Vue Router |
| 图表 | ECharts + vue-echarts |
| 集成 | django-vite（Vite HMR 内嵌到 Django 模板） |
| 认证 | SimpleJWT（access + refresh token） |
| 主题 | CSS 变量 + Element Plus dark 模式 |

## django-vite 工作流程

```
开发模式:
  python manage.py runserver (Django :8000)
  + npm run dev (Vite :5173)
  → django-vite 将 Vite 资源注入 Django 模板
  → 热更新正常工作

生产模式:
  npm run build → 输出到 static/frontend/
  python manage.py collectstatic
  → Django 直接 serve 构建产物
```

## 开发命令

```bash
# 一键启动（后端 + Vite 前端）
./dev_start.sh

# 或分别启动
python manage.py runserver 0.0.0.0:8000    # Django
cd frontend && npm run dev                  # Vite

# 前端构建
cd frontend && npm run build

# 创建迁移
python manage.py makemigrations <app_name>

# 执行迁移
python manage.py migrate

# 运行测试
python manage.py test apps.agent_api apps.clusters --verbosity=2
```

## Agent CLI 工具

独立 Python 包，安装在 PVE 节点上运行。

> 完整设计文档见 `data-structure/agent-design.md`

```bash
# 用户一键安装（从 Web 页面复制）
curl -fsSL https://platform:8000/api/agent/install.sh?token=<token>&platform=<url> | bash

# 用户一键卸载
curl -fsSL https://platform:8000/api/agent/install.sh | bash -s -- --uninstall

# Agent 管理命令
pcs-agent init        # 注册到平台（安装时自动执行）
pcs-agent start       # 启动 Agent
pcs-agent stop        # 停止 Agent
pcs-agent status      # 查看运行状态
pcs-agent update      # 更新到最新版本
pcs-agent uninstall   # 卸载 Agent
pcs-agent install     # 安装 Agent（交互式）
pcs-agent logs        # 查看运行日志（--follow 实时跟踪）

# systemd 管理（标准 Linux 命令）
systemctl status pcs-agent     # 查看服务状态
systemctl stop pcs-agent       # 停止
systemctl restart pcs-agent    # 重启
journalctl -u pcs-agent -f     # 查看日志
```

**配置文件**：`~/.config/pcs-agent/config.yaml`
**安装目录**：`/opt/pcs-agent/`

**执行流程**：
```
curl 安装脚本
  → 检测系统环境
  → 安装 Python3 + venv
  → pip install pcs-agent
  → pcs-agent init（注册到平台）
  → 安装 systemd 服务
  → 启动服务

Agent 运行中:
  → PVE API 认证
  → 心跳循环 (每 60s)
  → 扫描循环 (每 3600s)
    → 调用 PVE API 采集所有节点
    → 数据清洗 (bytes→MB/GB, CPU→%)
    → POST /api/agent/scan/upload/
    → Django 事务性入库 (10 个模型)
    → 检查下发任务
```

## API 端点

### 认证 `/api/auth/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/login/` | 登录（支持用户名或邮箱） | ❌ |
| POST | `/api/auth/register/` | 注册（用户名+邮箱+密码必填） | ❌ |
| GET | `/api/auth/user/` | 获取当前用户信息 | ✅ JWT |
| POST | `/api/auth/password-reset/` | 发送密码重置验证码 | ❌ |
| POST | `/api/auth/password-reset/confirm/` | 确认重置密码 | ❌ |

**登录请求示例：**
```json
POST /api/auth/login/
{"username": "buladou 或 buladou@example.com", "password": "xxx"}
→ {"access": "eyJ...", "refresh": "eyJ...", "user": {...}}
```

**密码重置流程：**
```
1. POST /api/auth/password-reset/  →  {"email": "..."}  → 返回 dev_code（开发模式）
2. POST /api/auth/password-reset/confirm/  →  {"code": "...", "new_password": "...", "new_password2": "..."}
```

### Agent 通信 `/api/agent/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/agent/register/` | Agent 注册（agent_token 鉴权） | ❌ |
| POST | `/api/agent/heartbeat/` | Agent 心跳上报 | ❌ |
| POST | `/api/agent/scan/upload/` | 扫描数据上传入库 | ❌ |
| GET | `/api/agent/tasks/` | 查询下发任务 | ❌ |
| POST | `/api/agent/unregister/` | Agent 卸载通知 | ❌ |
| GET | `/api/agent/version/` | 查询最新版本号 | ❌ |
| GET | `/api/agent/install.sh` | 获取安装脚本 | ❌ |

**Agent 注册：**
```json
POST /api/agent/register/
{"agent_token": "...", "pve_api_endpoint": "https://...", "pve_username": "root@pam", "pve_password": "...", "hostname": "pve-1", "scan_interval": 3600}
→ {"agent_id": "hex-uuid", "scan_interval": 3600, "status": "online"}
```

**心跳上报：**
```json
POST /api/agent/heartbeat/
{"agent_id": "hex-uuid", "status": "online", "current_task": ""}
→ {"ok": true}
```

**扫描上传：**
```json
POST /api/agent/scan/upload/
{
  "agent_id": "hex-uuid", "cluster_id": "int", "scanned_at": "ISO8601", "version": "pve-manager/8.2.4",
  "nodes": [{ "name": "pve-1", "cpu_load": 35.0, "disk_io_delay_ms": 12.5, "diskstat": [...], "vms": [...], "containers": [...], "storages": [...], "networks": [...] }],
  "ceph": { "health": "HEALTH_OK", "total_osds": 12, ... }
}
→ {"ok": true, "scan_task_id": 1}
```

**任务查询：**
```
GET /api/agent/tasks/?agent_id=hex-uuid
→ [{"id": 1, "task_type": "full_scan", "status": "running", "created_at": "..."}]
```

**Agent 卸载通知：**
```json
POST /api/agent/unregister/
{"agent_id": "hex-uuid"}
→ {"ok": true}
```

**版本查询：**
```
GET /api/agent/version/
→ {"latest_version": "0.2.0", "download_url": "https://..."}
```

**安装脚本获取：**
```
GET /api/agent/install.sh?token=<agent_token>&platform=<platform_url>
→ (返回 bash 安装脚本内容)
```

### 集群管理 `/api/clusters/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/clusters/` | 获取用户的所有集群 | ✅ JWT |
| POST | `/api/clusters/` | 创建集群（自动生成 agent_token） | ✅ JWT |
| GET | `/api/clusters/:id/` | 集群详情（含 Agent 列表 + 安装命令） | ✅ JWT |
| PATCH | `/api/clusters/:id/` | 更新集群信息 | ✅ JWT |
| DELETE | `/api/clusters/:id/` | 删除集群 | ✅ JWT |

**集群列表响应：**
```json
GET /api/clusters/
{
  "count": 2,
  "results": [
    {
      "id": 1, "name": "生产集群", "status": "active",
      "total_nodes": 3, "total_vms": 15, "total_lxc": 5,
      "agent_count": 2, "online_agents": 2,
      "last_scanned_at": "2026-06-29T15:30:00Z"
    }
  ]
}
```

**集群详情响应（含一键安装命令）：**
```json
GET /api/clusters/1/
{
  "id": 1, "name": "生产集群", "agent_token": "abc123...",
  "agents": [
    { "hostname": "pve-1", "status": "online", "version": "0.1.0", "total_scans": 58 }
  ],
  "install_command": "curl -fsSL 'https://platform:8000/api/agent/install.sh?token=abc123&platform=https://platform:8000' | bash"
}
```

## 页面路由

| 路径 | 页面 | 说明 | 需要登录 |
|------|------|------|---------|
| `/` | 首页 | Landing Page，品牌介绍与 CTA | ❌ |
| `/login` | 登录 | 左右分栏布局 + 品牌展示 | ❌ |
| `/register` | 注册 | 表单校验（用户名/邮箱/密码/确认） | ❌ |
| `/forgot-password` | 找回密码 | 两步流程：邮箱→验证码+新密码 | ❌ |
| `/dashboard` | 控制台 | 统计卡片 + 告警+趋势 + 节点表格 | ✅ |
| `/clusters` | 集群管理 | 集群 CRUD + Agent 列表 + 安装命令 | ✅ |
| `/nodes` | 节点管理 | PVE 节点监控（待实现） | ✅ |
| `/vms` | 虚拟机 | 虚拟机实例管理（待实现） | ✅ |
| `/containers` | 容器 | LXC 容器管理（待实现） | ✅ |
| `/alerts` | 告警中心 | 告警记录与处理（待实现） | ✅ |
| `/services` | 运维服务 | 远程运维订阅（待实现） | ✅ |
| `/settings` | 系统设置 | 账户和系统配置（待实现） | ✅ |
| `/admin/` | Django Admin | 后台管理 | 管理员 |

## 控制台布局（dashboard）

```
┌─────────────────────────────────────────────┐
│  控制台                                        │
├──────────┬──────────┬──────────┬─────────────┤
│ 集群总数  │ 在线节点  │ 告警数    │ Agent 数    │  ← StatCards（水平排列）
├──────────┴──────────┴──────────┴─────────────┤
│ ┌──────────┐ ┌──────────────────────────────┐│
│ │ 最近告警   │ │ 资源趋势 (ECharts)           ││  ← dash-row-split（grid）
│ │ (固定高度) │ │ CPU / 内存使用率折线         ││
│ │ 可滚动    │ │ 7d / 15d 切换               ││
│ └──────────┘ └──────────────────────────────┘│
├──────────────────────────────────────────────┤
│  节点详情（表格：名称/CPU/内存/磁盘/IP/版本/状态）│  ← NodeTable
└──────────────────────────────────────────────┘
```

## 亮暗主题

- **默认暗色主题**，首次访问即暗色
- 切换按钮在首页导航栏 + 后台顶部栏 + 登录/注册/找回密码页
- 通过 CSS 变量 (`--bg-primary`, `--bg-secondary` 等) 实现双色值
- 存入 localStorage，用户偏好持久化
- 相邻组件用交替背景色形成明显分层（`bg-primary` / `bg-secondary`）
- 侧边栏使用独立渐变背景色（亮色/暗色各一套）

## 数据模型总览

### accounts (用户认证)
- **User** - 自定义用户（继承 AbstractUser，含 phone/company）
- **PasswordResetCode** - 密码重置验证码（含过期时间、已使用标记）
- **Plan** - 套餐体系 Free/Pro/Enterprise
- **UserPlan** - 用户订阅关系

### clusters (集群管理)
- **Cluster** - 用户的 PVE 集群，含 agent_token 鉴权

### agent_api (Agent 多实例管理)
- **AgentInstance** - Agent 进程实例，支持多 Agent 部署
- **ScanTask** - 每次扫描任务记录

### scanner (扫描数据与检测)
- **ClusterNode** - PVE 节点（CPU/内存/磁盘/磁盘I/O延迟/网络）
- **VM** - 虚拟机 QEMU
- **LXC** - LXC 容器
- **Storage** - 存储
- **NetworkInterface** - 网络接口
- **CephStatus** - Ceph 集群状态
- **ScanHistory** - 扫描汇总快照（趋势图表用）
- **DetectionRule** - 自动检测规则配置
- **DetectionResult** - 检测结果

> 完整 PVE 数据结构分析文档见 `data-structure/` 目录。

## PVE 数据结构参考

### PVE API 认证

```
POST https://{host}:8006/api2/json/access/ticket
{"username": "root@pam", "password": "xxx"}
→ {"data": {"ticket": "PVE:...", "CSRFPreventionToken": "..."}}
```

### Agent 扫描流程（调用 PVE API）

```
POST /access/ticket → 获取票据
GET  /version                    → 集群版本
GET  /cluster/status             → 节点列表
for each node:
  GET /nodes/{node}/status       → 节点状态 (CPU/内存/磁盘/Swap/运行时长)
  GET /nodes/{node}/config       → 节点配置
  GET /nodes/{node}/qemu         → VM 列表 (含实时性能)
  GET /nodes/{node}/lxc          → LXC 列表
  GET /nodes/{node}/storage      → 存储列表
  GET /nodes/{node}/network      → 网络接口
GET  /cluster/ceph/status        → Ceph 健康状态 (如有)
```

### 关键字段映射（PVE API → DB）

| DB 模型 | API 端点 | 核心字段映射 |
|---------|---------|-------------|
| ClusterNode | `/nodes/{node}/status` | `cpu`(0~1) → `cpu_load`, `memory.total`(bytes→MB), `rootfs.total`(bytes→GB), `diskstat[].io_ms` → `disk_io_delay_ms`, `uptime` |
| VM | `/nodes/{node}/qemu` | `vmid`, `maxcpu`(cores), `cpu`(0~1), `maxmem`(bytes→MB), `netin/netout`(bps) |
| LXC | `/nodes/{node}/lxc` | `vmid`, `maxcpu`, `cpu`(0~1), `maxmem`(bytes→MB), `maxswap`(bytes→MB) |
| Storage | `/nodes/{node}/storage` | `storage`, `type`, `used/available/total`(bytes→GB), `content`, `shared` |
| NetworkInterface | `/nodes/{node}/network` | `iface`(→name), `type`, `address`, `speed` |
| CephStatus | `/cluster/ceph/status` | `health.status`, `osd.nr/up/in`, `pgmap.bytes_*`(bytes→GB) |

### 单位转换规则

| 原始 | DB | 公式 |
|------|-----|------|
| bytes (内存) | MB | `value // 1048576` |
| bytes (磁盘) | GB | `round(value / 1073741824, 2)` |
| CPU 0~1 | 百分比 | `round(value * 100, 1)` |

### ⚠️ 已知兼容性问题

1. **字段类型精度**：`ClusterNode.rootfs_*_gb`、`VM.disk_gb`、`Storage.*_gb` 使用了 `BigIntegerField`，但 bytes→GB 转换后为浮点数（如 48.5GB），会导致小数截断。**建议改为 `FloatField`**。
2. **缺字段**：Storage 缺少 `enabled` 字段、NetworkInterface 缺少 `mtu`/`bridge_ports`/`bond_mode`（PVE API 均有返回）。
3. **mac_address**：PVE API 不直接暴露 MAC 地址，需 Agent 通过 shell 命令获取。

### 数据上传格式（Agent → Django API）

```json
POST /api/agent/scan/upload/
{
  "agent_id": "uuid",
  "cluster_id": "uuid",
  "scanned_at": "2026-06-29T10:30:00Z",
  "version": "pve-manager/8.2.4",
  "nodes": [{ "name": "pve-1", "status": "online", "cpu_load": 0.35, "vms": [...], "containers": [...], "storages": [...], "networks": [...] }],
  "ceph": { "health": "HEALTH_OK", "total_osds": 12, ... }
}
```

### 数据流

```
PVE 节点 (Agent) → PVE API (HTTPS :8006) → Agent 数据清洗 → POST /api/agent/scan/upload/
→ Django 入库 (ClusterNode/VM/LXC/Storage/NetworkInterface/CephStatus/ScanHistory)
→ 触发自动检测 (DetectionRule → DetectionResult)
→ Web API → Vue 前端展示
```



## 多 Agent 架构

一个集群可部署多个 AgentInstance，每个 Agent 独立运行并上报数据：

1. Agent 安装时向 `/api/agent/register/` 注册，获得 agent_id（已有实现）
2. 每隔 60s 发送心跳 `POST /api/agent/heartbeat/`（已有实现）
3. 定时执行扫描任务，上报到 `POST /api/agent/scan/upload/`（已有实现）
4. Web 端可向特定 Agent 下发任务 `GET /api/agent/tasks/`（已有实现）
5. 后端 58 个测试用例覆盖完整流程：`python manage.py test apps.agent_api apps.clusters`

## 管理员

- 用户名: `buladou`
- 密码: `husongsxx`
- Django Admin: `http://localhost:8000/admin/`

## 下一步待实现

1. ~~认证 API~~ ✅ 已完成（登录/注册/密码重置）
2. ~~前端页面框架~~ ✅ 已完成（7 个后台页面 + 路由 + 侧边栏）
3. ~~仪表盘 UI~~ ✅ 已完成（统计卡片 + 告警列表 + 趋势图 + 节点表格）
4. ~~Agent 上报接口与数据入库~~ ✅ 已完成（注册/心跳/扫描上传/任务下发 + 48 个测试）
5. ~~Agent CLI 工具~~ ✅ 已完成（pcs-agent：init/start/stop/status/update/uninstall/install/logs）
6. ~~集群 CRUD API + 前端对接~~ ✅ 已完成（CRUD API + Agent 列表 + 安装命令展示）
7. 自动检测引擎
8. 仪表盘真实数据接入
9. 各管理页面功能实现（节点/虚拟机/容器/告警等）
