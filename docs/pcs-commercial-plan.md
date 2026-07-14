# PCS 商业化方案

## 概述

将 pve-cluster-scan 项目做成 **Open Core + Cloud** 模式：
- **自部署版（服务A）**：用户自行部署，功能完整免费
- **PCS 公网服务**：用户注册账号，付费升级套餐，获取运维增值服务

核心机制：用户在 PCS 购买套餐后获得专属 Token，配置到自部署的 Agent 中，Agent 数据**双写**到本地服务和 PCS 公网。

---

## 架构设计

### 数据流

```
用户自部署环境                          PCS 公网服务
┌─────────────────┐                   ┌─────────────────┐
│ PVE 集群         │                   │                 │
│   ↓              │                   │  用户账户系统    │
│ Agent ──────────→│── POST scan ───→  │  套餐计费系统    │
│   ↓              │    (双写)          │  数据存储展示    │
│ 本地 Web 界面    │                   │  运维报告        │
└─────────────────┘                   └─────────────────┘
```

### Agent 双上报机制

Agent 配置文件新增 `PCS_UPLOAD_URL` 和 `PCS_TOKEN` 字段：

```bash
# /opt/pcs-agent/config.env
PVE_API_ENDPOINT=https://pve.local:8006
LOCAL_UPLOAD_URL=http://localhost:8066/api/agent/scan/upload/
PCS_UPLOAD_URL=https://pcs.yourdomain.com/api/agent/scan/upload/
PCS_TOKEN=usera-xxxx-xxxx  # 用户在 PCS 购买套餐后获得
```

扫描数据同时上报到本地服务和 PCS 公网。

---

## 代码结构

采用 **单项目 + 环境变量切换**，不新增独立项目：

```
pve-cluster-scan/
├── apps/
│   ├── accounts/          # 共用（用户认证）
│   ├── clusters/          # 共用（集群管理）
│   ├── agent_api/         # 共用（Agent 通信）
│   ├── scanner/           # 共用（扫描数据）
│   ├── dashboard/         # 共用（控制台）
│   │
│   ├── plans/             # 🆕 仅 cloud 模式启用
│   │   ├── models.py      #   套餐定义 + 用户订阅
│   │   ├── serializers.py
│   │   ├── views.py       #   套餐查询 + Token 生成
│   │   └── urls.py
│   │
│   └── sync/              # 🆕 仅 cloud 模式启用
│       ├── models.py      #   绑定关系（token → cluster → user）
│       ├── serializers.py
│       ├── views.py       #   接收自部署服务上传的数据
│       └── urls.py
│
├── frontend/
│   └── src/
│       └── views/
│           ├── plans/     # 🆕 套餐购买页面
│           └── sync/      # 🆕 同步管理页面
│
└── config/
    └── settings.py        # 增加 RUNNING_MODE 判断
```

---

## 配置开关

```python
# config/settings.py

import os

# 运行模式：self-hosted（自部署）或 cloud（PCS 公网）
RUNNING_MODE = os.environ.get('RUNNING_MODE', 'self-hosted')

if RUNNING_MODE == 'cloud':
    # PCS 公网服务特有的配置
    INSTALLED_APPS += ['apps.plans', 'apps.sync']
    # 启用套餐限制、Token 管理、数据同步接收
else:
    # 自部署模式，功能完整，无需付费
    pass
```

---

## 套餐设计

| 套餐 | 价格 | 集群数 | Agent 数 | 数据保留 | 功能 |
|------|------|--------|---------|---------|------|
| 免费 | ¥0 | 1 | 2 | 7 天 | 基础监控 |
| 个人 | ¥99/月 | 3 | 10 | 30 天 | 告警 + 趋势 |
| 企业 | ¥499/月 | 20 | 100 | 180 天 | 运维报告 + API |

---

## 功能对比

| 功能 | 自部署版 | PCS 版 |
|------|---------|--------|
| Agent 数据采集 | ✅ | ✅ |
| 本地 Web 展示 | ✅ | ✅ |
| 用户注册 | ✅ | ✅ |
| 套餐付费 | ❌ | ✅ |
| Token 管理 | ❌ | ✅ |
| 接收远程数据 | ❌ | ✅ |
| 运维报告 | ❌ | ✅（付费功能） |
| 多集群聚合 | 本地 | ✅（云端聚合） |

---

## 部署方式

### 自部署用户

```bash
git clone https://github.com/xxx/pve-cluster-scan
./dev_start.sh
# 直接用，所有功能免费
```

### PCS 公网服务

```bash
git clone https://github.com/xxx/pve-cluster-scan
export RUNNING_MODE=cloud
docker-compose up  # 或 ./dev_start.sh
# 启用套餐系统、Token 管理等商业功能
```

---

## 关键问题与解决方案

### 1. 数据安全

用户可能担心数据上传到公网。

**解决方案：**
- 只上传统计数据（CPU/内存/状态），不传配置详情
- 或端到端加密传输
- 用户可选择性开启/关闭双写

### 2. 网络连通性

内网 Agent 如何访问公网 PCS。

**解决方案：**
- 方案一：Agent 主动上报（需公网出口）
- 方案二：PCS 提供 Webhook，服务A 主动推送
- 方案三：用户通过 VPN/隧道打通

### 3. 版本兼容

开源版和 PCS 版的 API 要保持兼容。

**解决方案：**
- PCS 作为开源版的"增值层"，不 fork 代码
- 用 Django app 插件化，商业模块单独安装
- 保持 API 接口向后兼容

### 4. 套餐限制

不同套餐的集群数、Agent 数、数据保留天数限制。

**解决方案：**
- 在 `apps/plans/models.py` 定义 Plan 模型
- 在 `apps/agent_api/views.py` 中检查用户套餐限制
- 超出限制时返回 403 并提示升级套餐

---

## 实现步骤（待执行）

1. **创建 `apps/plans` app**
   - Plan 模型（套餐定义）
   - UserPlan 模型（用户订阅）
   - PCS_Token 生成与管理

2. **创建 `apps/sync` app**
   - SyncBinding 模型（token → cluster → user 绑定关系）
   - 接收自部署服务上传数据的 API
   - 数据存储与展示

3. **修改 `apps/agent_api`**
   - Agent 双写逻辑（读取 PCS_UPLOAD_URL 和 PCS_TOKEN）
   - 检查用户套餐限制

4. **前端页面**
   - 套餐购买页面
   - 同步管理页面（查看绑定的集群、Token 管理）

5. **文档更新**
   - 自部署版 README
   - PCS 版 README
   - API 文档更新

---

## 总结

| 问题 | 结论 |
|------|------|
| 需要新增项目？ | ❌ 不需要 |
| 代码复用率 | ~85%（新增 plans + sync 两个小 app） |
| 维护成本 | 低（一套代码，两种模式） |
| 自部署用户体验 | 不受影响（商业功能默认不启用） |
| 技术可行性 | ✅ 完全可行 |
| 工作量 | PCS 端新增：套餐系统 + Token 管理 + 同步接收，约 2-3 周 |
