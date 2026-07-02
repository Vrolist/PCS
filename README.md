# PVE Cluster Scan

[English](README.en.md) | [Deutsch](README.de.md)

PVE 集群扫描与管理平台 — 基于 Django 5 + Vue 3 的全栈解决方案，支持多集群、多 Agent 部署，实时监控 Proxmox VE 环境。

## 功能特性

- **多集群管理**：一个账号管理多个 PVE 集群，统一监控
- **Agent 自动采集**：单文件零依赖 Python Agent，curl 一键安装，自动扫描节点/VM/容器/存储/网络/Ceph 状态
- **实时仪表盘**：统计卡片、告警列表、资源趋势图（ECharts）、节点状态表格
- **资源管理**：节点、虚拟机（QEMU）、LXC 容器、存储、网络接口、Ceph 存储集群、HA 高可用
- **Agent 自动更新**：平台下发更新指令，Agent 自动升级并重启
- **用户认证**：JWT 登录/注册/密码重置，操作日志审计
- **亮暗主题**：默认暗色，支持一键切换，偏好持久化

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + Django 5.0 + DRF + SimpleJWT |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| 图表 | ECharts + vue-echarts |
| Agent | Python stdlib（零依赖） |

## 快速开始

### 一键启动

```bash
# 安装依赖
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 数据库迁移
python manage.py migrate

# 启动（后端 + Vite 前端）
./dev_start.sh
```

### 分别启动

```bash
python manage.py runserver 0.0.0.0:8066    # Django
cd frontend && npm run dev                  # Vite (:5173)
```

访问 `http://localhost:8066` 即可。

### Agent 安装

在 PVE 节点上一键安装：

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?token=<token>&platform=<url>' | bash
```

或手动安装：

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?agent=1' -o agent.py
python3 agent.py install     # 交互式配置 + 注册 + 安装 systemd
```

## 项目结构

```
pve-cluster-scan/
├── config/                 # Django 项目配置
├── apps/
│   ├── accounts/           # 用户认证 & 操作日志
│   ├── clusters/           # 集群管理（CRUD + Agent 列表）
│   ├── agent_api/          # Agent 通信（注册/心跳/扫描上传/任务下发）
│   ├── dashboard/          # 仪表盘查询 API
│   └── scanner/            # 扫描数据 & 自动检测
├── frontend/               # Vue 3 + Vite 前端
│   └── src/views/          # 页面（仪表盘/集群/节点/VM/容器/设置等）
├── agent/                  # Agent 单文件（零依赖 Python 脚本）
├── data-structure/         # PVE 数据结构分析文档
└── dev_start.sh            # 一键启动脚本
```

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `/api/auth/` | 登录/注册/密码重置/用户信息/操作日志 |
| Agent | `/api/agent/` | 注册/心跳/扫描上传/任务/版本/安装脚本 |
| 仪表盘 | `/api/dashboard/` | 统计/告警/趋势/节点状态 |
| 集群 | `/api/clusters/` | 集群 CRUD + Agent 列表 |
| 扫描 | `/api/scanner/` | 节点/VM/容器/存储/网络/Ceph/HA 查询 |

详细 API 文档见 `data-structure/api-interfaces.md`。

## 测试

```bash
python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2
```

## 许可证

本项目采用 [GNU Affero General Public License v3.0](LICENSE) 协议。

这意味着你可以自由使用、修改和分发本软件，但如果你通过网络向用户提供服务，则必须公开修改后的完整源码。
