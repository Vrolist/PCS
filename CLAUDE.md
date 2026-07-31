# pve-cluster-scan

PVE 集群扫描与管理平台 — Django 5 + Vue 3 全栈项目。

## 项目架构

```
pve-cluster-scan/
├── config/                 # Django 项目配置
│   ├── settings.py         #   - DRF / JWT / CORS / Vite 端口配置
│   ├── urls.py             #   - auth 路由 + catch-all → Vue SPA
│   └── asgi.py             #   - ASGI 入口（uvicorn）
├── apps/
│   ├── core/               # 通用工具（Vite 模板标签 / 上下文处理器）
│   │   ├── context_processors.py  # - vite_context（注入 vite_host/vite_port）
│   │   ├── templatetags/
│   │   │   └── vite_tags.py       # - vite_asset（生产模式 manifest 查找）
│   │   └── views.py
│   ├── accounts/           # 用户认证 & 操作日志 & AI 助手
│   │   ├── models.py       #   - User / PasswordResetCode / UserLog / UserLLMConfig / ChatConversation / ChatMessage
│   │   ├── serializers.py  #   - Login / Register / User / PasswordReset
│   │   ├── views.py        #   - 登录 / 注册 / 用户信息 / 密码重置 / 操作日志 / AI 聊天流式端点
│   │   ├── urls.py         #   - /api/auth/ 路由（含 logs/ + chat/ + llm-configs/ + system-prompts/）
│   │   ├── llm_service.py  #   - LangChain LLM 封装（build_llm / stream_chat）
│   │   ├── chat_context.py #   - PVE 数据上下文注入（关键词匹配 → 动态查询）
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
│   │   ├── tests.py        #   - 47 个测试用例（含 7 个过期数据清理测试）
│   │   └── admin.py
│   ├── dashboard/          # Dashboard 查询 API
│   │   ├── views.py        #   - stats / alerts / trends / nodes
│   │   ├── urls.py         #   - /api/dashboard/ 路由（4 个端点）
│   │   └── tests.py        #   - 30 个测试用例
│   └── scanner/            # 扫描数据 & 自动检测
│       ├── views.py        #   - 节点/VM/容器/存储/网络/Ceph/HA/SDN 列表+详情
│       ├── urls.py         #   - /api/scanner/ 路由（13 个端点）
│       └── models.py       #   - ClusterNode/VM/LXC/VMConfig/LXCConfig/Storage/NetworkInterface/CephStatus/ScanHistory/DetectionRule/DetectionResult/SDNZone/SDNVNet/SDNSubnet
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
│   │   │   │   ├── StatCards.vue              # 统计卡片（集群/节点/VM&容器/告警）
│   │   │   │   ├── AlertList.vue              # 最近告警列表（固定高度+滚动）
│   │   │   │   ├── TrendChart.vue             # 资源趋势 ECharts 折线图
│   │   │   │   ├── NodeTable.vue              # 节点详情表格
│   │   │   │   └── ChangePassword.vue         # 修改密码
│   │   │   ├── clusters/index.vue             # 集群管理（表格+CRUD+详情弹窗）
│   │   │   ├── nodes/index.vue                # 节点管理（表格+详情弹窗）
│   │   │   ├── vms/index.vue                  # 虚拟机（表格+详情弹窗）
│   │   │   ├── containers/index.vue           # 容器（表格+详情弹窗）
│   │   │   ├── sdn/index.vue                  # SDN 虚拟网络（Tab 切换：区域/VNet/子网）
│   │   │   ├── alerts/index.vue               # 告警中心（告警记录表格）
│   │   │   ├── services/index.vue             # 运维服务（HA 资源状态表格）
│   │   │   ├── settings/index.vue             # 用户信息（完整编辑界面）
│   │   │   ├── user-logs/index.vue            # 操作日志（分页表格+筛选）
│   │   │   └── user-notifications/index.vue   # 通知设置（空状态）
│   │   ├── components/
│   │   │   ├── AppSidebar.vue        # 侧边栏导航（含折叠图标居中 + 集群选择器）
│   │   │   └── AppHeader.vue         # 顶栏（含主题切换 + 退出登录）
│   │   ├── layouts/MainLayout.vue    # 后台主布局（侧边栏+顶栏+内容区）
│   │   │── router/index.ts           # 路由 + 守卫（所有后台页面在 /dashboard/ 下）
│   │   ├── stores/
│   │   │   ├── app.ts                # 全局状态（侧边栏折叠）
│   │   │   ├── auth.ts               # JWT 认证
│   │   │   ├── theme.ts              # 亮暗主题（默认暗色）
│   │   │   └── cluster.ts            # 集群列表 + 当前选中集群 (全局集群选择器)
│   │   ├── api/
│   │   │   ├── request.ts            # Axios 实例 + 拦截器
│   │   │   ├── auth.ts               # 登录/注册/密码重置/用户信息/操作日志 API
│   │   │   ├── clusters.ts           # 集群 CRUD + Agent 查询 API
│   │   │   ├── dashboard.ts          # Dashboard 统计/告警/趋势/节点 API
│   │   │   ├── nodes.ts              # 节点/详情 API
│   │   │   ├── ceph.ts               # Ceph 状态 API
│   │   │   ├── ha.ts                 # HA 资源 API
│   │   │   └── sdn.ts                # SDN 区域/VNet/子网 API
│   │   └── style.css                 # CSS 变量 / 亮暗色值
│   ├── package.json
│   └── vite.config.ts
├── agent/                    # Agent（单文件，零依赖）
│   └── agent.py               # PVE 数据采集 + 上报（纯 Python stdlib）
├── data-structure/           # PVE 数据结构分析文档
│   ├── README.md             # 分析说明与 License 声明
│   ├── database-models.md    # 数据库模型与 PVE 字段映射
│   ├── api-interfaces.md     # PVE API 接口清单
│   ├── field-mapping.md      # 字段对照表
│   ├── data-flow.md          # 数据采集与入库流程
│   └── agent-design.md       # Agent 设计文档（架构/命令/安装/通信）
├── templates/
│   └── vue_index.html                # Django 模板（自动适配 IP/端口）
├── static/                           # Vite 构建输出
├── .venv/                            # Python 虚拟环境（Python 3.12）
├── manage.py
├── dev_start.sh                      # 一键启动（.venv + 依赖 + 前端构建 + uvicorn ASGI）
├── scripts/
│   └── seed_test_data.py             # 模拟测试数据种子脚本（5 级架构 + SDN）
├── requirements.txt                  # 后端 Python 依赖
└── CLAUDE.md
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + Django 5.0 + DRF |
| 服务器 | uvicorn（ASGI，原生支持 streaming） |
| AI | LangChain + langchain-openai（LLM 流式调用） |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Element Plus + Pinia + Vue Router |
| 图表 | ECharts + vue-echarts |
| 认证 | SimpleJWT（access + refresh token） |
| 主题 | CSS 变量 + Element Plus dark 模式 |

## 虚拟环境

项目使用 Python 3.12 虚拟环境（`.venv/`），所有 `python manage.py` 相关命令需在虚拟环境中执行。

```bash
# 激活虚拟环境
source .venv/bin/activate

# 或使用虚拟环境中的 Python 直接执行
.venv/bin/python <command>
```

## 一键启动（dev_start.sh）

`dev_start.sh` 是项目开发服务器的统一启动入口，自动完成以下步骤：

1. **虚拟环境** — 检测 `.venv` 目录，不存在则用 `python3.12 -m venv .venv` 创建并激活
2. **后端依赖** — `pip install -r requirements.txt -q`（含 langchain-openai）
3. **数据库迁移** — `python manage.py migrate`
4. **管理员账户** — 自动创建 `pcs` 超级用户（如不存在）
5. **前端构建** — `cd frontend && npm install && npx vite build`
6. **启动服务** — 前台启动 uvicorn ASGI（:8066）

```bash
# 一键启动（推荐）
./dev_start.sh

# 启动后访问
#   http://<本机IP>:8066  → Django 直接 serve 前端 + API
```

> **注意**：生产模式和开发模式统一使用 uvicorn ASGI 服务器，前端构建到 `static/frontend/`。
> 浏览器直接访问 `:8066`，无 Vite 代理，SSE 流式响应正常工作。

## 服务器工作流程

```
统一模式（uvicorn ASGI）:
  方式一（推荐）: ./dev_start.sh
    → .venv + 依赖 + 迁移 + 前端构建 + uvicorn :8066

  方式二（手动启动）:
    source .venv/bin/activate
    uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --reload

  → 浏览器直接访问 http://IP:8066
  → Django serve 前端静态文件（static/frontend/）+ API
  → 无 Vite 代理，SSE 流式响应正常工作

前端构建:
  cd frontend && npm run build
  # 构建产物输出到 static/frontend/（含 manifest.json）
  → vite_asset 模板标签从 manifest 查找构建后的 JS/CSS
```

## 开发命令

以下命令均在项目根目录执行，需先激活虚拟环境（`source .venv/bin/activate` 或使用 `.venv/bin/python`）：

```bash
# 一键启动（推荐）
./dev_start.sh

# 手动启动 uvicorn ASGI
source .venv/bin/activate
uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --reload

# 前端构建
cd frontend && npm install && npx vite build   # 跳过 vue-tsc 类型检查

# 创建迁移
.venv/bin/python manage.py makemigrations <app_name>

# 执行迁移
.venv/bin/python manage.py migrate

# 生成模拟测试数据（含 SDN，需 Django 服务运行中）
.venv/bin/python scripts/seed_test_data.py reset

# 运行测试
.venv/bin/python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2
```

## Git 推送工作流

项目采用双 remote 推送架构：

```
本地开发机  ──push──→  Gitea (192.168.2.27:1022)  ──同步──→  GitHub (Vrolist/PCS)
  origin               内网 Git 服务器                 自动镜像同步
  github               GitHub 公开仓库
```

- **origin** (主 remote): `ssh://git@192.168.2.27:1022/buladou/pve-cluster-scan.git`
- **github** (镜像 remote): `https://github.com/Vrolist/PCS.git`
- 本地 push 到 origin 后，Gitea 自动同步到 GitHub
- 如需手动推送到 GitHub：`git push github main`
- GitHub Actions workflow (`.github/workflows/docker.yml`) 使用 `if: github.repository == 'Vrolist/PCS'` 条件，确保只在 GitHub 侧执行（Gitea 不会运行）

```bash
# 推送到内网 Gitea（主仓库）
git push origin main

# 推送到 GitHub（如 Gitea 同步延迟或需要立即触发 Actions）
git push github main
```

## Agent

单文件 Python 脚本（零依赖，纯 stdlib），安装在 PVE 节点上运行。

```bash
# 用户一键安装（从 Web 页面复制）
curl -fsSL 'http://platform:8000/api/agent/install.sh?token=<token>&platform=<url>' | bash
# → 下载 agent.py → 交互式输入 PVE 信息 → 注册 → 安装 systemd → 启动

# 用户一键卸载
curl -fsSL 'http://platform:8000/api/agent/install.sh?uninstall' | bash

# 手动安装
curl -fsSL 'http://platform:8000/api/agent/install.sh?agent=1' -o agent.py
python3 agent.py install     # 交互式配置 + 注册 + 安装 systemd
python3 agent.py run         # 直接运行（前台）
python3 agent.py once        # 单次扫描
python3 agent.py status      # 查看状态

# systemd 管理
systemctl status pcs-agent
systemctl restart pcs-agent
journalctl -u pcs-agent -f
```

**安装目录**：`/opt/pcs-agent/`
**配置文件**：`/opt/pcs-agent/config.env`（KEY=VALUE 格式）
**日志文件**：`/opt/pcs-agent/agent.log`

**执行流程**：
```
curl 安装脚本
  → 下载 agent.py 到 /opt/pcs-agent/
  → 交互式输入 PVE 地址/用户名/密码
  → POST /api/agent/register/ 注册到平台
  → 保存 config.env
  → 安装 systemd 服务 → 启动

Agent 运行中:
  → PVE API 认证 (POST /access/ticket)
  → 心跳循环 (每 120s POST /api/agent/heartbeat/, 含 version)
    → 收到 410 → _stop_permanently() (systemctl disable + exit)
    → 收到 update.available → _handle_update() (自动更新，见下方)
  → 扫描循环 (每 300s)
    → 调用 PVE API 采集所有节点
    → 采集集群级数据（Ceph / HA / SDN）
    → 数据清洗 (bytes→MB/GB, CPU→%)
    → POST /api/agent/scan/upload/
    → 收到 423 → 暂停上传，心跳保持 (deactivated)
    → 收到 410 → _stop_permanently() (集群已删除)
    → 检查下发任务 GET /api/agent/tasks/

Agent 自动更新 (v0.5.0+):
  平台侧: views.py 维护 AGENT_LATEST_VERSION 常量
  心跳响应: agent.version < AGENT_LATEST_VERSION → 返回 update.available + download_url
  Agent 侧:
    → _handle_update() 接收 update 指令
    → GET /api/agent/install.sh?agent=1 下载新版 agent.py 源码
    → 校验 VERSION 字段 → 备份旧版 → 替换 → 重启 systemd
  安装脚本:
    → install.sh?token=X&platform=Y → 返回 bash 安装脚本（首次安装用）
    → install.sh?agent=1 → 返回 agent.py 源码（自动更新用）

当前最新版本: v0.12.0 — 新增集群任务和集群日志采集

Agent 版本提示:
  Web 前端 Agent 表格显示 version 列
  → agent.version < latest_version → 橙色「可更新」标签
  → agent.version == latest_version → 绿色「最新」标签
```

## API 端点

### 认证 `/api/auth/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/login/` | 登录（支持用户名或邮箱） | ❌ |
| POST | `/api/auth/register/` | 注册（用户名+邮箱+密码必填） | ❌ |
| GET | `/api/auth/user/` | 获取当前用户信息 | ✅ JWT |
| PATCH | `/api/auth/user/` | 更新用户信息（phone/company） | ✅ JWT |
| POST | `/api/auth/password-reset/` | 发送密码重置验证码 | ❌ |
| POST | `/api/auth/password-reset/confirm/` | 确认重置密码 | ❌ |
| GET | `/api/auth/logs/` | 操作日志（分页，支持 action 筛选） | ✅ JWT |

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

**操作日志响应：**
```json
GET /api/auth/logs/?page=1&page_size=20&action=login
→ {
    "count": 50,
    "results": [
      {
        "id": 1,
        "action": "login",
        "action_display": "登录",
        "resource_type": "",
        "resource_id": null,
        "detail": "用户登录",
        "ip_address": "192.168.1.1",
        "created_at": "2026-06-30T10:00:00Z"
      }
    ]
  }
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
{"agent_token": "...", "pve_api_endpoint": "https://...", "pve_username": "root@pam", "pve_password": "...", "hostname": "pve-1", "scan_interval": 300}
→ {"agent_id": "hex-uuid", "scan_interval": 300, "status": "online"}
```

**心跳上报（包含版本号）：**
```json
POST /api/agent/heartbeat/
{"agent_id": "hex-uuid", "status": "online", "current_task": "", "version": "0.6.0"}
→ {"ok": true}

// 有新版本时，响应自动附带 update 字段：
→ {
    "ok": true,
    "update": {
      "available": true,
      "latest_version": "0.6.0",
      "download_url": "http://platform:8066/api/agent/install.sh?agent=1",
      "changelog": "v0.6.0: 支持 SDN 虚拟网络数据采集"
    }
  }
```

**集群停用/删除特殊响应：**
```
集群停用: POST /api/agent/scan/upload/ → 423 (is_active=False)
集群删除: POST /api/agent/heartbeat/ 或 upload/ → 410 (cluster=None, AgentInstance 通过 SET_NULL 保留)
```

**扫描上传：**
```json
POST /api/agent/scan/upload/
{
  "agent_id": "hex-uuid", "cluster_id": "int", "scanned_at": "ISO8601", "version": "pve-manager/8.2.4",
  "nodes": [{ "name": "pve-1", ... }],
  "ceph": { ... },
  "ha_resources": [...],
  "sdn": { "zones": [...], "vnets": [...], "subnets": [...] }
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
→ {"latest_version": "0.6.0", "download_url": "/api/agent/install.sh", "changelog": "v0.6.0: 支持 SDN 虚拟网络数据采集"}
```

**安装脚本获取：**
```
GET /api/agent/install.sh?token=<agent_token>&platform=<platform_url>
→ 返回 bash 安装脚本（首次安装用，交互式配置 + 注册 + systemd 安装）

GET /api/agent/install.sh?agent=1
→ 返回 agent.py 源码（自动更新用，Agent _handle_update() 调用此端点下载新版）
```

### Dashboard `/api/dashboard/`

**Stats 响应：**
```json
GET /api/dashboard/stats/
→ {"total_clusters": 1, "total_nodes": 3, "online_nodes": 3, "total_vms": 16, "total_containers": 67, "active_alerts": 0}
```

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/dashboard/stats/` | 统计卡片（集群数/节点数/VM&容器数/告警数） | ✅ JWT |
| GET | `/api/dashboard/alerts/?limit=10` | 最近未解决告警列表 | ✅ JWT |
| GET | `/api/dashboard/trends/?days=7` | CPU/内存使用率趋势 | ✅ JWT |
| GET | `/api/dashboard/nodes/` | 最新节点状态 | ✅ JWT |

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
    { "hostname": "pve-1", "status": "online", "version": "0.6.0", "total_scans": 58 }
  ],
  "install_command": "curl -fsSL 'https://platform:8000/api/agent/install.sh?token=abc123&platform=https://platform:8000' | bash"
}
```

### 扫描数据 `/api/scanner/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/scanner/nodes/` | 节点列表（含集群名，按扫描时间倒序） | ✅ JWT |
| GET | `/api/scanner/nodes/:id/detail/` | 节点详情（关联存储/网络/VM/容器） | ✅ JWT |
| GET | `/api/scanner/vms/` | 虚拟机列表（含集群名+节点名） | ✅ JWT |
| GET | `/api/scanner/vms/:id/detail/` | 虚拟机详情（CPU/内存/磁盘/网络/HA/标签等） | ✅ JWT |
| GET | `/api/scanner/containers/` | LXC 容器列表 | ✅ JWT |
| GET | `/api/scanner/containers/:id/detail/` | 容器详情（含 IP 地址、HA 等） | ✅ JWT |
| GET | `/api/scanner/storage/` | 存储列表 | ✅ JWT |
| GET | `/api/scanner/networks/` | 网络接口列表 | ✅ JWT |
| GET | `/api/scanner/ceph/` | Ceph 集群状态 | ✅ JWT |
| GET | `/api/scanner/ha/` | HA 资源组列表 | ✅ JWT |
| GET | `/api/scanner/sdn/zones/` | SDN 区域列表 | ✅ JWT |
| GET | `/api/scanner/sdn/vnets/` | SDN 虚拟网络列表 | ✅ JWT |
| GET | `/api/scanner/sdn/subnets/` | SDN 子网列表 | ✅ JWT |

**节点详情响应：**
```json
GET /api/scanner/nodes/1/detail/
{
  "node": { "id": 1, "node_name": "pve-1", "status": "online", "cpu_load": 35.0, "memory_total_mb": 32000, ... },
  "storages": [{ "name": "local", "type": "dir", ... }],
  "networks": [{ "name": "vmbr0", "type": "bridge", "address": "192.168.1.1", ... }],
  "vms": [{ "vmid": 100, "name": "ubuntu", "status": "running", ... }],
  "containers": [{ "vmid": 200, "name": "nginx", "status": "running", ... }]
}
```

**VM 详情响应（含补充字段）：**
```json
GET /api/scanner/vms/1/detail/
{
  "vm": { "vmid": 100, "name": "ubuntu", "cpu_cores": 2, "cpu_sockets": 1, "balloon_min_mb": 1024, "balloon_max_mb": 4096, "disk_read_iops": 100, "disk_write_iops": 50, "snapshot_count": 2, "has_template": false, "description": "..." },
  "config": { "ha_enabled": false, "ha_group": null }
}
```

**容器详情响应（含 IP 地址）：**
```json
GET /api/scanner/containers/1/detail/
{
  "container": { ..., "ip_address": "192.168.1.100" },
  "config": { ... }
}
```

## 页面路由

| 路径 | 页面 | 说明 | 需要登录 |
|------|------|------|---------|
| `/` | 自动重定向 → `/dashboard` | 根路径跳转到控制台 | ❌ |
| `/login` | 登录 | 左右分栏布局 + 品牌展示 | ❌ |
| `/register` | 注册 | 表单校验（用户名/邮箱/密码/确认） | ❌ |
| `/forgot-password` | 找回密码 | 两步流程：邮箱→验证码+新密码 | ❌ |
| `/dashboard` | 控制台 | 统计卡片 + 告警+趋势 + 节点表格 | ✅ |
| `/dashboard/clusters` | 集群管理 | 集群 CRUD + Agent 列表 + 安装命令 | ✅ |
| `/dashboard/nodes` | 节点管理 | PVE 节点监控（表格+详情弹窗） | ✅ |
| `/dashboard/vms` | 虚拟机 | 虚拟机实例管理（表格+详情弹窗） | ✅ |
| `/dashboard/containers` | 容器 | LXC 容器管理（表格+详情弹窗） | ✅ |
| `/dashboard/storage` | 存储管理 | PVE 存储列表 | ✅ |
| `/dashboard/networks` | 网络接口 | 网络接口列表 | ✅ |
| `/dashboard/ceph` | Ceph 存储 | Ceph 集群状态 | ✅ |
| `/dashboard/sdn` | 软件定义网络 | SDN 区域/虚拟网络/子网 (3 Tab 表格) | ✅ |
| `/dashboard/network-topology` | 网络拓扑 | SVG 节点-网络拓扑图（复杂网络可视化） | ✅ |
| `/dashboard/dependency-mapping` | 依赖链路 | SVG 节点内嵌依赖图（VM/LXC→节点→存储→网络），含拖拽/缩放/自动扩充 | ✅ |
| `/dashboard/alerts` | 告警中心 | 告警记录表格（按集群筛选） | ✅ |
| `/dashboard/ha` | 高可用管理 | HA 资源统计卡片 + 表格 | ✅ |
| `/dashboard/services` | 运维服务 | HA 资源状态表格 | ✅ |
| `/dashboard/settings` | 用户信息 | 编辑资料 + 安全设置（完整界面） | ✅ |
| `/dashboard/change-password` | 修改密码 | 修改登录密码 | ✅ |
| `/dashboard/user-logs` | 操作日志 | 用户操作记录（分页表格+筛选） | ✅ |
| `/dashboard/user-notifications` | 通知设置 | 通知偏好（待实现） | ✅ |
| `/admin/` | Django Admin | 后台管理 | 管理员 |

## 控制台布局（dashboard）

```
┌─────────────────────────────────────────────┐
│  控制台                                        │
├──────────┬──────────┬────────────────┬───────┤
│ 集群 1    │ 节点 3   │ 虚拟机/容器 16/67│ 告警 0│  ← StatCards（左图标+右数值）
├──────────┴──────────┴────────────────┴───────┤
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

## 全局集群选择器

侧边栏顶部增加全局集群选择框 (`cluster.ts` store)，所有使用集群数据的页面共享同一个选择状态：

- **HA / 运维服务 / 告警中心 / SDN** 等页面不再有独立 `el-select`，统一使用侧边栏的全局选择器
- 切换集群时，通过 `watch(clusterStore.currentClusterId)` 自动刷新页面数据
- 使用方式：`useClusterStore()` → `clusterStore.currentClusterId` / `clusterStore.clusterList`

## 数据模型总览

### accounts (用户认证)
- **User** - 自定义用户（继承 AbstractUser，含 phone/company）
- **PasswordResetCode** - 密码重置验证码（含过期时间、已使用标记）
- **UserLog** - 操作日志（记录用户的登录/注册/CRUD/改密等操作）

### clusters (集群管理)
- **Cluster** - 用户的 PVE 集群，含 agent_token 鉴权

### agent_api (Agent 多实例管理)
- **AgentInstance** - Agent 进程实例，支持多 Agent 部署。`cluster` FK 使用 `SET_NULL`（集群删除后 agent 记录保留，但 cluster=None，心跳/上传返回 410）
- **ScanTask** - 每次扫描任务记录

### scanner (扫描数据与检测)
- **ClusterNode** - PVE 节点（CPU/内存/磁盘/磁盘I/O延迟/网络）
- **VM** - 虚拟机 QEMU（`unique_together = ("node", "vmid")`，原地更新）
- **VMConfig** - VM 详细配置（`unique_together = ("vm",)`，原地更新）
- **LXC** - LXC 容器（`unique_together = ("node", "vmid")`，原地更新）
- **LXCConfig** - LXC 容器详细配置（`unique_together = ("container",)`，原地更新）
- **Storage** - 存储
- **NetworkInterface** - 网络接口
- **CephStatus** - Ceph 集群状态
- **ScanHistory** - 扫描汇总快照（趋势图表用）
- **HAResource** - HA 高可用资源（sid/resource_type/vmid/ha_group/ha_status/crm_state）
- **DetectionRule** - 自动检测规则配置
- **DetectionResult** - 检测结果
- **SDNZone** - SDN 区域（zone/zone_type/nodes，原地更新）
- **SDNVNet** - SDN 虚拟网络（vnet/vnet_type/vlan/zone，原地更新）
- **SDNSubnet** - SDN 子网（subnet/gateway/dns_server/vnet，原地更新）

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
  GET /nodes/{node}/qemu/{vmid}/config  → VM 详细配置
  GET /nodes/{node}/lxc/{vmid}/config   → LXC 详细配置
GET  /cluster/ceph/status        → Ceph 健康状态 (如有)
GET  /cluster/ha/resources       → HA 资源列表 (如有)
GET  /cluster/sdn/zones          → SDN 区域列表 (如有)
GET  /cluster/sdn/vnets          → SDN 虚拟网络列表 (如有)
GET  /cluster/sdn/subnets        → SDN 子网列表 (如有)
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
| HAResource | `/cluster/ha/resources` | `sid`, `type`(→resource_type), `status`(→state), `ha.group`, `ha.status`, `ha.crm_state` |
| SDNZone | `/cluster/sdn/zones` | `zone`, `type`(→zone_type), `nodes` |
| SDNVNet | `/cluster/sdn/vnets` | `vnet`, `type`(→vnet_type), `vlan`, `zone` |
| SDNSubnet | `/cluster/sdn/subnets` | `subnet`, `gateway`, `dnsserver`, `dnszoneprefix`, `vnet` |

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
  "ceph": { "health": "HEALTH_OK", "total_osds": 12, ... },
  "ha_resources": [{ "sid": "vm:100", "type": "vm", ... }],
  "sdn": { "zones": [...], "vnets": [...], "subnets": [...] }
}
```

### 数据流

```
PVE 节点 (Agent) → PVE API (HTTPS :8006) → Agent 数据清洗 → POST /api/agent/scan/upload/
→ Django 入库 (ClusterNode/VM/LXC/VMConfig/LXCConfig/Storage/NetworkInterface/CephStatus/ScanHistory/HAResource/SDNZone/SDNVNet/SDNSubnet)
→ Web API → Vue 前端展示
```

### 存储优化

VM、LXC、VMConfig、LXCConfig、SDNZone、SDNVNet、SDNSubnet 使用 **原地更新** 策略（`unique_together` 不含 `scanned_at`，写入用 `update_or_create`），每次扫描覆盖最新数据，不产生历史冗余行。

| 模型 | unique_together | 策略 | 30天节省 |
|------|----------------|------|---------|
| VM | `(node, vmid)` | update_or_create | ~99.9%（720行→1行） |
| LXC | `(node, vmid)` | update_or_create | ~99.9%（720行→1行） |
| VMConfig | `(vm,)` | update_or_create | ~99.9%（720行→1行） |
| LXCConfig | `(container,)` | update_or_create | ~99.9%（720行→1行） |
| SDNZone | `(cluster, zone)` | update_or_create | ~99.9% |
| SDNVNet | `(cluster, vnet)` | update_or_create | ~99.9% |
| SDNSubnet | `(cluster, subnet)` | update_or_create | ~99.9% |

其余模型（ClusterNode、Storage、NetworkInterface、CephStatus、ScanHistory、HAResource）仍按时间序保留历史记录，用于趋势分析。

### 数据保留策略（Lazy on-upload 清理）

每次 Agent 扫描上传成功时，自动清理**当前集群**的过期历史数据（事务外执行，失败不影响上传）：

| 模型 | 保留天数 | 说明 |
|------|---------|------|
| ClusterNode | 7 天 | 节点快照变化慢，7 天足够趋势 |
| Storage | 7 天 | 存储容量变化慢 |
| NetworkInterface | 7 天 | 网络配置基本不变 |
| CephStatus | 7 天 | 健康状态变化不频繁 |
| SDNZone | 7 天 | SDN 配置基本不变 |
| SDNVNet | 7 天 | SDN 配置基本不变 |
| SDNSubnet | 7 天 | SDN 配置基本不变 |
| ScanHistory | 30 天 | 趋势图核心数据源，需较长历史 |
| ScanTask | 30 天 | 审计需要 |

清理实现在 `apps/agent_api/views.py` 的 `_cleanup_expired()` 方法中，使用 `scanned_at__lt=cutoff` 批量 DELETE，走索引。

## 多 Agent 架构

一个集群可部署多个 AgentInstance，每个 Agent 独立运行并上报数据：

1. Agent 安装时向 `/api/agent/register/` 注册，获得 agent_id（已有实现）
2. 每隔 60s 发送心跳 `POST /api/agent/heartbeat/`（已有实现）
3. 定时执行扫描任务，上报到 `POST /api/agent/scan/upload/`（已有实现）
4. Web 端可向特定 Agent 下发任务 `GET /api/agent/tasks/`（已有实现）
5. 操作日志自动记录用户关键操作（登录/注册/CRUD/改密等）
6. 后端 126 个测试用例覆盖完整流程：`python manage.py test apps.agent_api apps.clusters apps.dashboard`

## 管理员

- 用户名: `buladou`
- 密码: `husongsxx`
- Django Admin: `http://localhost:8066/admin/`

## 模拟测试数据

`scripts/seed_test_data.py` 支持 5 种架构级别的模拟数据生成，可用于开发和演示：

| Level | 架构 | 节点 | VM | 容器 | Ceph | HA | SDN | 网络拓扑 |
|-------|------|------|-----|------|------|----|-----|---------|
| 1 | 单节点入门 | 1 | 0 | 3 | ❌ | ❌ | ❌ | vmbr0 |
| 2 | 双节点小集群 | 2 | 6 | 13 | ❌ | ❌ | ❌ | vmbr0+vmbr1 |
| 3 | 三节点标准集群 | 3 | ~20 | ~35 | ❌ | ❌ | ✅ | vmbr0+bond0 |
| 4 | Ceph 三节点 | 3 | ~36 | ~30 | ✅ OK | 2 | ✅ | vmbr0+vmbr1+bond0 |
| 5 | 企业生产集群 | 5 | ~65 | ~60 | ✅ WARN | 5 | ✅ | vmbr0+vmbr1+bond0 |

使用方式: `python scripts/seed_test_data.py reset`

## 下一步待实现

1. ~~认证 API~~ ✅ 已完成（登录/注册/密码重置）
2. ~~前端页面框架~~ ✅ 已完成（7 个后台页面 + 路由 + 侧边栏）
3. ~~仪表盘 UI~~ ✅ 已完成（统计卡片 + 告警列表 + 趋势图 + 节点表格）
4. ~~Agent 上报接口与数据入库~~ ✅ 已完成（注册/心跳/扫描上传/任务下发 + 48 个测试）
5. ~~Agent CLI 工具~~ ✅ 已完成（单文件 agent.py，零依赖，curl 一键安装）
6. ~~集群 CRUD API + 前端对接~~ ✅ 已完成（CRUD API + Agent 列表 + 安装命令展示）
7. ~~节点/VM/容器管理页面~~ ✅ 已完成（表格+详情弹窗+详情API）
8. ~~操作日志~~ ✅ 已完成（UserLog 模型+API+前端分页列表）
9. ~~用户信息设置页面~~ ✅ 已完成（编辑资料+安全设置）
10. ~~数据库存储优化~~ ✅ 已完成（VM/LXC/VMConfig/LXCConfig 原地更新，节省 ~99.9% 存储）
11. ~~数据保留清理~~ ✅ 已完成（Lazy on-upload 清理，7天/30天阈值）
12. ~~集群停用/恢复/删除完成链路~~ ✅ 已完成（is_active→423, deleted→410, agent _stop_permanently）
13. ~~Agent 版本更新提示~~ ✅ 已完成（前端 agent 表格显示「最新」/「可更新」标签）
14. ~~SDN 数据采集与展示~~ ✅ 已完成（SDNZone/VNet/Subnet 模型 + Agent 采集 v0.6.0 + 前端 Tab 页面）
15. ~~网络拓扑可视化~~ ✅ 已完成（SVG 节点-网络连接图 + 图例筛选 + IP 网段图层）
16. ~~依赖链路可视化~~ ✅ 已完成（SVG 节点内嵌依赖图 + 拖拽/缩放/自动扩充 + 布局居中）
17. ~~LLM 流式对话（AI 助手）~~ ✅ 已完成（LangChain async streaming + uvicorn ASGI + SSE；已修复流式 UI 不刷新问题；已补充 85 个 LLM/SSE 测试用例）
18. 自动检测引擎
19. 仪表盘真实数据进一步接入（告警、趋势数据源）

## AI 助手流式对话

AI 助手聊天面板（ChatBubble）通过 `/api/auth/chat/stream/` 端点实现 LLM 流式输出，使用 LangChain 统一接入。

### 架构

```
前端 (ChatBubble)           后端 (Django + LangChain)        LLM Provider
  │                           │                              │
  │── POST /chat/stream/ ────→│                              │
  │   {config_id, messages,   │                              │
  │    cluster_id,            │── build_llm(config) ────────→│ ChatOpenAI
  │    user_message}          │   → llm.astream(messages) ──→│   .astream()
  │                           │                              │
  │  ← SSE text/event-stream  │  ← async for chunk: yield   │
  │  data: {delta:...}        │     token → SSE 格式         │
  │  data: [DONE]             │                              │
```

### 核心模块

| 文件 | 职责 |
|------|------|
| `apps/accounts/llm_service.py` | LangChain LLM 封装（`build_llm` / `build_langchain_messages` / `stream_chat`），支持 DeepSeek 等模型的 `reasoning_content` 透传 |
| `config/asgi.py` | ASGI 入口，将 `/api/auth/chat/stream/` 路由到独立 SSE handler，绕过 Django 中间件缓冲 |
| `config/sse_handler.py` | 独立 ASGI SSE handler，直接通过 transport 写入并 flush，保证逐 token 推送 |
| `apps/accounts/chat_context.py` | `build_pve_context` — PVE 数据动态注入 |
| `frontend/src/stores/chat.ts` | `sendMessage` — fetch + ReadableStream 读取 SSE，注意引用数组中的响应式代理以触发 UI 更新 |
| `frontend/src/components/ChatBubble.vue` | 渲染消息Markdown，将 `<think>` 思考过程渲染为可折叠灰色块 |

### 后端流式传输（LangChain async generator）

`apps/accounts/llm_service.py`：

```python
# 构建 LLM 实例（所有 OpenAI 兼容 API 统一接入）
llm = ChatOpenAI(api_key=..., base_url=..., model=..., streaming=True)

# 流式生成，yield 每个 token
async for chunk in llm.astream(messages):
    # DeepSeek 等推理模型可能返回 reasoning_content
    reasoning = (
        getattr(chunk, "additional_kwargs", {}).get("reasoning_content", "")
        or getattr(chunk, "response_metadata", {}).get("reasoning_content", "")
        or ""
    )
    if reasoning:
        yield f"<think>{reasoning}</think>"
    if chunk.content:
        yield chunk.content
```

`config/sse_handler.py` — `sse_chat_stream()`（独立 ASGI handler，绕过 Django 中间件）：

```python
async def sse_chat_stream(scope, receive, send):
    # ... 读取 body、JWT 鉴权、加载配置 ...

    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"text/event-stream"],
            [b"cache-control", b"no-cache, no-store, must-revalidate"],
            [b"x-accel-buffering", b"no"],
        ],
    })

    async def _stream():
        async for token in stream_chat(llm, langchain_msgs):
            chunk = json.dumps({"choices": [{"delta": {"content": token}}]})
            await _send_sse(send, f"data: {chunk}\n\n")

    async def _listen_disconnect():
        while True:
            msg = await receive()
            if msg.get("type") == "http.disconnect":
                return

    # 并发：流式输出 + 监听断连
    stream_task = asyncio.ensure_future(_stream())
    disconnect_task = asyncio.ensure_future(_listen_disconnect())
    await asyncio.wait([stream_task, disconnect_task], return_when=asyncio.FIRST_COMPLETED)
```

关键设计：
- **独立 ASGI handler**：`config/asgi.py` 将 SSE 请求直接路由到 `sse_chat_stream`，绕过 Django 与 uvicorn 的 StreamingHttpResponse 缓冲
- **直接写 transport**：每个 token 通过 `send({"type": "http.response.body", ...})` 直接 push，无中间缓冲
- **并发监听断连**：`_stream()` 与 `_listen_disconnect()` 并发，用户停止或刷新页面时立即中止流
- **LangChain streaming**：`ChatOpenAI(streaming=True)` + `llm.astream()` 原生异步流式
- **SSE 格式兼容**：前端无需改动，格式与之前一致

### 前端 SSE 解析

`frontend/src/stores/chat.ts` — `sendMessage()`：

```typescript
const reader = response.body!.getReader()
const decoder = new TextDecoder()
let lineBuffer = ''

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  lineBuffer += decoder.decode(value, { stream: true })
  const lines = lineBuffer.split('\n')
  lineBuffer = lines.pop() || ''

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || !trimmed.startsWith('data: ')) continue
    const data = trimmed.slice(6)
    if (data === '[DONE]') break
    const parsed = JSON.parse(data)
    const delta = parsed.choices?.[0]?.delta?.content
    if (delta) {
      fullReply += delta
      if (!assistantMsg) {
        const newMsg: ChatMessage = { id: ..., role: 'assistant', content: '', timestamp: ... }
        messages.value.push(newMsg)
        // 必须引用数组中的响应式代理，否则修改 content 不会触发 UI 刷新
        assistantMsg = messages.value[messages.value.length - 1]
      }
      assistantMsg.content = fullReply
    }
  }
}
```

> ⚠️ **重要**：`messages.value.push(newMsg)` 后，数组内部会创建响应式代理。如果直接持有 `newMsg` 引用并修改 `newMsg.content`，Vue 无法感知变化，导致流式过程中 UI 不刷新。务必通过 `messages.value[index]` 引用代理对象再赋值。

### 测试覆盖

`apps/accounts/tests_llm.py` 提供 85 个测试用例，覆盖 LLM 沟通全流程：

| 测试类 | 用例数 | 覆盖范围 |
|--------|--------|----------|
| `LLMConfigTest` | 11 | `build_llm` 配置解析、base_url 规范化、模型参数 |
| `LangChainMessageTest` | 12 | `build_langchain_messages` 角色转换、PVE 上下文注入、边界值 |
| `StreamChatTest` | 8 | 流式 token yield、中文 Unicode、空 chunk、异常传播 |
| `ChatContextTest` | 25 | 关键词匹配、无数据集群、空消息、大小写混写 |
| `SSEHandlerAuthTest` | 10 | 方法限制、JWT 鉴权、参数校验、配置不存在 |
| `SSEHandlerStreamingTest` | 15 | 多 token 流式、SSE 帧格式、顺序、断连、异常、空流 |
| `FullLLMIntegrationTest` | 6 | 配置→SSE handler→流式输出的全链路组合测试 |

运行命令：

```bash
.venv/bin/python manage.py test apps.accounts.tests_llm --verbosity=1
```

### PVE 数据上下文注入

`apps/accounts/chat_context.py` — `build_pve_context()` 根据用户消息关键词动态查询数据库，将集群实时数据注入到 system prompt 中：

- 关键词匹配（"节点"/"cpu"/"存储"/"网络"/"ha"/"sdn" 等）确定需要加载的数据层
- 始终注入集群摘要（节点数/VM数/容器数）
- 无关键词匹配时默认加载节点/VM/容器层
- 注入格式：`--- 当前集群实时数据 ---\n{数据}\n--- 数据结束 ---`
- 由 `build_langchain_messages()` 在构建 LangChain 消息时自动注入

## 依赖链路可视化（dependency-mapping）

`/dashboard/dependency-mapping` 页面使用纯 SVG 实现三层递进式依赖关系图。

### 三层架构

```
集群（cluster）→ 节点容器（node）→ 子节点（VM/容器/存储/网络）
```

- **集群**（cluster）：最外层，内含所有节点
- **节点容器**（node）：矩形容器，内部排列子节点。子节点类型用不同边框色区分：VM（绿色）、容器（蓝色）、存储（红色）、网络（紫色）
- **子节点**（vm/container/storage/network）：固定尺寸卡片，存储固定在底部行，网络固定在右侧列

### autoLayout 布局算法

```
节点起始 Y = 120（保留集群标题空间）
间距：padding=28, cardW=170, cardH=52, gapX=gapY=16

节点容器内布局：
  VM/容器行：从 (nx + padding, contentY) 开始水平排列
  存储行：VM 行下方，左对齐（不足时容器宽度自适应）
  网络列：与 VM/容器行同 Y，靠右对齐（widthAuto 时居右剩余空间）

布局后自动居中到 SVG 画布（包围盒 + 80px 边距偏移）
SVG 尺寸：max(1200, contentW+160) × max(800, contentH+160)
```

### 边线路由

| 边类型 | 方向 | 路径 |
|--------|------|------|
| cluster→node | 垂直 | 集群底部 → 节点顶部，贝塞尔曲线 |
| vm→storage | 垂直 | VM 底部 → 存储顶部，同列 |
| vm→network | 水平 | VM 右边缘 → 网络左边缘，水平贝塞尔 |
| container→storage | 垂直 | 容器底部 → 存储顶部 |
| container→network | 水平 | 容器右边缘 → 网络左边缘 |

节点→子节点的边（node-vm/node-container/node-storage/node-network）被跳过，通过**视觉包含**体现归属关系。

### 交互功能

| 交互 | 行为 |
|------|------|
| **拖拽子节点** | 所有同组子节点同步移动，触及时自动扩充父节点宽度/高度（padding=28） |
| **拖拽父节点** | 所有子节点跟随移动 |
| **画布拖拽** | 移动整个场景 |
| **滚轮缩放** | zoomIn/zoomOut（0.3~3.0），viewBox 实时计算 |
| **双指缩放** | 触控板手势缩放 |
| **点击节点** | 右侧显示节点详情面板（调用对应详情 API） |
| **复位视图** | resetView() 将 scale 重置为 1 并重新 autoLayout |

### 拖动坐标校正

使用 `screenToSvg()` 将 `clientX/clientY` 映射到 SVG viewBox 坐标空间，避免缩放后抖动。

### 切换集群全量重置

`watch(clusterStore.currentClusterId)` 时自动：
1. `scale=1`、清空 graphData/nodePositions
2. 清空资源选择器和详情面板
3. 刷新新集群的 VM/容器下拉列表

### SVG 特效

- `filter="url(#node-shadow)"` — 所有节点卡片阴影
- `filter="url(#edge-glow)"` — 边线 hover 发光
- `.node-group:hover rect` — 亮度提升 + stroke 加粗
- `.edge-path:hover` — 加粗 + 发光
