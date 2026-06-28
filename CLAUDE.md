# pve-cluster-scan

PVE 集群扫描与管理平台 — Django 5 + Vue 3 全栈项目。

## 项目架构

```
pve-cluster-scan/
├── config/                 # Django 项目配置
│   ├── settings.py         #   - DRF / JWT / django-vite / CORS
│   └── urls.py             #   - catch-all 路由 → Vue SPA
├── apps/
│   ├── accounts/           # 用户认证 & 套餐管理
│   ├── clusters/           # 集群管理
│   ├── agent_api/          # Agent 通信 & 多 Agent 管理
│   └── scanner/            # 扫描数据 & 自动检测
├── frontend/               # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue          # Landing Page
│   │   │   ├── auth/Login.vue    # 登录
│   │   │   ├── auth/Register.vue # 注册
│   │   │   ├── dashboard/        # 控制台
│   │   │   └── clusters/         # 集群管理
│   │   ├── components/
│   │   │   ├── AppSidebar.vue    # 侧边栏导航
│   │   │   ├── AppHeader.vue     # 顶栏（含主题切换）
│   │   │   └── ServerIcon.vue    # 自定义服务器 SVG 图标
│   │   ├── layouts/MainLayout.vue
│   │   ├── router/index.ts       # 路由 + 守卫
│   │   ├── stores/
│   │   │   ├── app.ts            # 全局状态
│   │   │   ├── auth.ts           # JWT 认证
│   │   │   └── theme.ts          # 亮暗主题
│   │   ├── api/
│   │   │   ├── request.ts        # Axios 实例 + 拦截器
│   │   │   └── auth.ts           # 登录/注册 API
│   │   └── style.css             # CSS 变量 / 亮暗色值
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── templates/
│   └── vue_index.html            # Django 模板（django-vite 入口）
├── static/                       # Vite 构建输出
├── manage.py
├── dev_start.sh                  # 一键启动脚本
├── frontend_start.sh             # 前端单独启动
└── CLAUDE.md
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + Django 5.0 + DRF |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Element Plus + Pinia + Vue Router |
| 集成 | django-vite（Vite HMR 内嵌到 Django 模板） |
| 认证 | SimpleJWT |
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
```

## 页面路由

| 路径 | 页面 | 说明 | 需要登录 |
|------|------|------|---------|
| `/` | 首页 | Landing Page，品牌介绍与 CTA | ❌ |
| `/login` | 登录 | 左右分栏布局 + 品牌展示 | ❌ |
| `/register` | 注册 | 表单校验（用户名/邮箱/密码/确认） | ❌ |
| `/dashboard` | 控制台 | 统计卡片 + 集群列表 | ✅ |
| `/clusters` | 集群管理 | 集群 CRUD（待实现） | ✅ |
| `/admin/` | Django Admin | 后台管理 | 管理员 |

## 亮暗主题

- **默认暗色主题**，首次访问即暗色
- 切换按钮在首页导航栏 + 后台顶部栏
- 通过 CSS 变量 (`--bg-primary`, `--text-primary` 等) 实现双色值
- 存入 localStorage，用户偏好持久化

## 数据模型总览

### accounts (用户认证)
- **User** - 自定义用户（继承 AbstractUser，含 phone/company）
- **Plan** - 套餐体系 Free/Pro/Enterprise
- **UserPlan** - 用户订阅关系

### clusters (集群管理)
- **Cluster** - 用户的 PVE 集群，含 agent_token 鉴权

### agent_api (Agent 多实例管理)
- **AgentInstance** - Agent 进程实例，支持多 Agent 部署
- **ScanTask** - 每次扫描任务记录

### scanner (扫描数据与检测)
- **ClusterNode** - PVE 节点（CPU/内存/磁盘/网络）
- **VM** - 虚拟机 QEMU
- **LXC** - LXC 容器
- **Storage** - 存储
- **NetworkInterface** - 网络接口
- **CephStatus** - Ceph 集群状态
- **ScanHistory** - 扫描汇总快照（趋势图表用）
- **DetectionRule** - 自动检测规则配置
- **DetectionResult** - 检测结果

## 多 Agent 架构

一个集群可部署多个 AgentInstance，每个 Agent 独立运行并上报数据：

1. Agent 安装时向 `/api/agent/register/` 注册，获得 agent_id
2. 每隔 N 秒发送心跳 `POST /api/agent/heartbeat/`
3. 定时执行扫描任务，上报到 `POST /api/agent/scan/upload/`
4. Web 端可向特定 Agent 下发任务 `GET /api/agent/tasks/`

## 管理员

- 用户名: `buladou`
- 密码: `husongsxx`
- Django Admin: `http://localhost:8000/admin/`

## 下一步待实现（参考方向）

1. 开发认证 API（`/api/auth/login/`、`/api/auth/register/`）
2. 集群 CRUD API + 前端页面
3. Agent CLI 工具
4. Agent 上报接口与数据入库
5. 自动检测引擎
6. 仪表盘数据可视化（ECharts）
