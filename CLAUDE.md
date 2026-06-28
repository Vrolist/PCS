# pve-cluster-scan

PVE 集群扫描与管理平台 — Django 5 + REST Framework 后端。

## 项目架构

```
pve-cluster-scan/
├── config/                 # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/           # 用户认证 & 套餐管理
│   ├── clusters/           # 集群管理
│   ├── agent_api/          # Agent 通信 & 多 Agent 管理
│   └── scanner/            # 扫描数据 & 自动检测
├── agent/                  # Agent CLI 工具（待开发）
├── static/                 # 静态文件
├── templates/              # 模板
├── manage.py
├── requirements.txt
└── CLAUDE.md
```

## 技术栈

- Python 3.12 + Django 5.0
- Django REST Framework
- SQLite（开发）/ PostgreSQL（生产）
- SimpleJWT 认证

## 开发命令

```bash
# 启动开发服务器
python manage.py runserver 0.0.0.0:8000

# 创建迁移
python manage.py makemigrations <app_name>

# 执行迁移
python manage.py migrate

# 创建超级管理员
python manage.py createsuperuser

# 收集静态文件
python manage.py collectstatic
```

## 数据模型总览

### accounts (用户认证)
| 模型 | 说明 |
|------|------|
| User | 自定义用户（继承 AbstractUser） |
| Plan | 套餐/价格体系 |
| UserPlan | 用户订阅关系 |

### clusters (集群管理)
| 模型 | 说明 |
|------|------|
| Cluster | 用户的 PVE 集群，含 agent_token 鉴权 |

### agent_api (Agent 多实例管理)
| 模型 | 说明 |
|------|------|
| AgentInstance | Agent 进程实例，支持多 Agent 部署 |
| ScanTask | 每次扫描任务记录 |

### scanner (扫描数据与检测)
| 模型 | 说明 |
|------|------|
| ClusterNode | PVE 节点（CPU/内存/磁盘/网络） |
| VM | 虚拟机 QEMU |
| LXC | LXC 容器 |
| Storage | 存储 |
| NetworkInterface | 网络接口 |
| CephStatus | Ceph 集群状态快照 |
| ScanHistory | 扫描汇总快照（趋势图表用） |
| DetectionRule | 自动检测规则配置 |
| DetectionResult | 检测结果 |

## 多 Agent 架构

一个集群可部署多个 AgentInstance，每个 Agent 独立运行并上报数据：

1. Agent 安装时向 `/api/agent/register/` 注册，获得 agent_id
2. 每隔 N 秒发送心跳 `POST /api/agent/heartbeat/`
3. 定时执行扫描任务，上报到 `POST /api/agent/scan/upload/`
4. Web 端可向特定 Agent 下发任务 `GET /api/agent/tasks/`

## 管理员

- 用户名: buladou
- 密码: husongsxx
- 邮箱: buladou@example.com
