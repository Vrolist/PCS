# Agent 设计文档

PVE 集群扫描 Agent 的完整设计方案。

## 目录

- [架构概览](#架构概览)
- [用户交互流程](#用户交互流程)
- [一键安装脚本](#一键安装脚本)
- [Agent CLI 命令](#agent-cli-��令)
- [systemd 服务](#systemd-服务)
- [通信协议](#通信协议)
- [数据采集流程](#数据采集流程)
- [生命周期管理](#生命周期管理)
- [安全设计](#安全设计)
- [离线部署](#离线部署)
- [文件结构](#文件结构)

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Web 平台 (Django)                     │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 集群管理   │  │ Agent API    │  │ 安装脚本托管      │  │
│  │ (token)   │  │ (4个接口)    │  │ /api/agent/install│  │
│  └──────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │  PVE 节点1  │  │  PVE 节点2  │  │  PVE 节点3  │
    │            │  │            │  │            │
    │  pve-agent │  │  pve-agent │  │  pve-agent │
    │  (systemd) │  │  (systemd) │  │  (systemd) │
    │            │  │            │  │            │
    │  → PVE API │  │  → PVE API │  │  → PVE API │
    │  → 平台API │  │  → 平台API │  │  → 平台API │
    └───────────┘  └───────────┘  └───────────┘
```

**核心原则**：用户只需粘贴一条命令，Agent 自动完成安装、注册、运行。

---

## 用户交互流程

### 安装流程

```
1. 用户在 Web 平台创建集群
   → 平台生成 agent_token

2. Web 页面显示一键安装命令
   → 用户点击 [复制]

3. 用户 SSH 到 PVE 节点
   → 粘贴命令并执行

4. 脚本自动完成:
   ✅ 检测系统环境（Debian/Ubuntu/CentOS）
   ✅ 安装 Python3 + pip + venv
   ✅ 创建虚拟环境 /opt/pve-agent/
   ✅ pip install pve-agent
   ✅ 执行 pve-agent init（注册到平台）
   ✅ 安装 systemd 服务
   ✅ 启动服务
   ✅ 输出 "安装成功！Agent ID: xxx"

5. Agent 在后台持续运行
   → 心跳（60s）+ 扫描（3600s）+ 上报
```

### 卸载流程

```bash
# 方式一：一键卸载
curl -fsSL https://platform:8000/api/agent/install.sh | bash -s -- --uninstall

# 方式二：手动卸载
pve-agent uninstall
```

### 更新流程

```bash
pve-agent upgrade
```

---

## 一键安装脚本

### URL 设计

```
GET /api/agent/install.sh?token=<agent_token>&platform=<platform_url>
```

### 脚本内容（伪代码）

```bash
#!/bin/bash
set -e

# ============ 参数解析 ============
TOKEN=""
PLATFORM_URL=""
UNINSTALL=false

for arg in "$@"; do
  case $arg in
    --token=*)    TOKEN="${arg#*=}" ;;
    --platform=*) PLATFORM_URL="${arg#*=}" ;;
    --uninstall)  UNINSTALL=true ;;
  esac
done

# ============ 卸载模式 ============
if [ "$UNINSTALL" = true ]; then
  echo "停止 pve-agent 服务..."
  systemctl stop pve-agent 2>/dev/null || true
  systemctl disable pve-agent 2>/dev/null || true
  rm -f /etc/systemd/system/pve-agent.service
  systemctl daemon-reload

  # 通知平台
  if [ -f /opt/pve-agent/config.yaml ]; then
    AGENT_ID=$(grep "agent_id:" /opt/pve-agent/config.yaml | awk '{print $2}')
    curl -s -X POST "$PLATFORM_URL/api/agent/unregister/" \
      -H "Content-Type: application/json" \
      -d "{\"agent_id\": \"$AGENT_ID\"}" || true
  fi

  rm -rf /opt/pve-agent/
  rm -rf ~/.config/pve-agent/
  echo "✅ Agent 已卸载"
  exit 0
fi

# ============ 安装模式 ============
echo "PVE Agent 安装程序"
echo "=================="

# 1. 检测系统
detect_os() {
  if [ -f /etc/debian_version ]; then
    echo "debian"
  elif [ -f /etc/redhat-release ]; then
    echo "redhat"
  else
    echo "unknown"
  fi
}

OS=$(detect_os)
echo "检测到系统: $OS"

# 2. 安装依赖
install_deps() {
  if [ "$OS" = "debian" ]; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv curl
  elif [ "$OS" = "redhat" ]; then
    yum install -y python3 python3-pip curl
  fi
}

echo "安装系统依赖..."
install_deps

# 3. 创建安装目录
INSTALL_DIR="/opt/pve-agent"
mkdir -p "$INSTALL_DIR"

# 4. 创建虚拟环境
echo "创建 Python 虚拟环境..."
python3 -m venv "$INSTALL_DIR/venv"

# 5. 安装 Agent
echo "安装 pve-agent..."
"$INSTALL_DIR/venv/bin/pip" install --quiet pve-agent

# 6. 生成配置
echo "注册 Agent..."
"$INSTALL_DIR/venv/bin/pve-agent" init \
  --platform-url "$PLATFORM_URL" \
  --token "$TOKEN"

# 7. 安装 systemd 服务
cat > /etc/systemd/system/pve-agent.service << 'SERVICEEOF'
[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart=/opt/pve-agent/venv/bin/pve-agent start --foreground
Restart=always
RestartSec=10
WorkingDirectory=/opt/pve-agent

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable pve-agent
systemctl start pve-agent

# 8. 输出结果
AGENT_ID=$(grep "agent_id:" ~/.config/pve-agent/config.yaml | awk '{print $2}')
echo ""
echo "=============================="
echo "✅ Agent 安装成功！"
echo "   Agent ID: $AGENT_ID"
echo "   安装目录: $INSTALL_DIR"
echo "   配置文件: ~/.config/pve-agent/config.yaml"
echo "   状态查看: systemctl status pve-agent"
echo "   查看日志: journalctl -u pve-agent -f"
echo "   卸载命令: pve-agent uninstall"
echo "=============================="
```

---

## Agent CLI 命令

### 命令列表

| 命令 | 说明 | 参数 |
|------|------|------|
| `pve-agent` | 显示帮助信息 | — |
| `pve-agent status` | 查看运行状态 | — |
| `pve-agent update` | 更新到最新版本 | `--check` 仅检查不更新 |
| `pve-agent uninstall` | 卸载 Agent | `--force` 跳过确认 |

### 帮助信息

```
$ pve-agent

PVE 集群扫描 Agent v0.1.0

用法:
  pve-agent status      查看运行状态
  pve-agent update      更新到最新版本
  pve-agent uninstall   卸载 Agent

管理命令 (systemd):
  systemctl status pve-agent     查看服务状态
  systemctl stop pve-agent       停止服务
  systemctl restart pve-agent    重启服务
  journalctl -u pve-agent -f     查看实时日志

配置文件: ~/.config/pve-agent/config.yaml
安装目录: /opt/pve-agent/
```

### status 命令

```
$ pve-agent status

PVE Agent 状态
================
  版本:     0.1.0
  Agent ID: abc123def456
  平台:     https://platform:8000
  PVE:      https://192.168.1.100:8006
  扫描间隔: 3600s
  心跳间隔: 60s

  服务状态: active (running)
  运行时长: 2d 5h 30m
  扫描次数: 58
  失败次数: 0
  上次扫描: 2026-06-29 15:30:00
```

### update 命令

```
$ pve-agent update

检查更新中...
当前版本: 0.1.0
最新版本: 0.2.0
发现新版本，正在更新...

1. 下载新版本...
2. 更新虚拟环境...
3. 重启服务...
4. 验证服务状态...

✅ 更新完成！
   旧版本: 0.1.0
   新版本: 0.2.0
   服务状态: active (running)
```

### uninstall 命令

```
$ pve-agent uninstall

即将卸载 PVE Agent:
  Agent ID: abc123def456
  安装目录: /opt/pve-agent/
  配置文件: ~/.config/pve-agent/config.yaml

确认卸载? [y/N]: y

1. 停止服务...
2. 删除 systemd 服务...
3. 通知平台...
4. 删除文件...

✅ Agent 已卸载
```

---

## systemd 服务

### 服务文件

```ini
# /etc/systemd/system/pve-agent.service

[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart=/opt/pve-agent/venv/bin/pve-agent start --foreground
Restart=always
RestartSec=10
WorkingDirectory=/opt/pve-agent

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/pve-agent /root/.config/pve-agent

[Install]
WantedBy=multi-user.target
```

### 常用 systemd 命令

```bash
systemctl status pve-agent       # 查看状态
systemctl stop pve-agent         # 停止
systemctl start pve-agent        # 启动
systemctl restart pve-agent      # 重启
systemctl enable pve-agent       # 开机自启
systemctl disable pve-agent      # 取消开机自启
journalctl -u pve-agent -f       # 实时日志
journalctl -u pve-agent --since "1 hour ago"  # 最近日志
```

---

## 通信协议

### 接口列表

| 方法 | 路径 | 说明 | 频率 |
|------|------|------|------|
| POST | `/api/agent/register/` | Agent 注册 | 仅安装时 |
| POST | `/api/agent/heartbeat/` | 心跳上报 | 每 60s |
| POST | `/api/agent/scan/upload/` | 扫描数据上传 | 每 3600s |
| GET | `/api/agent/tasks/` | 查询下发任务 | 每次扫描后 |
| POST | `/api/agent/unregister/` | Agent 卸载通知 | 仅卸载时 |
| GET | `/api/agent/install.sh` | 获取安装脚本 | 仅安装时 |
| GET | `/api/agent/version/` | 查询最新版本号 | 升级时 |

### 认证方式

- **安装脚本**：通过 URL 参数 `token=<agent_token>` 鉴权
- **注册接口**：通过请求体 `agent_token` 鉴权
- **后续通信**：通过请求体 `agent_id` 鉴权
- **无 JWT 认证**：Agent API 独立于用户认证体系

### 心跳协议

```json
POST /api/agent/heartbeat/
{
  "agent_id": "hex-string",
  "status": "online",          // online | offline | error
  "current_task": ""           // 扫描时填 "scanning"
}
→ {"ok": true}
```

### 扫描上传协议

```json
POST /api/agent/scan/upload/
{
  "agent_id": "hex-string",
  "cluster_id": 1,
  "scanned_at": "2026-06-29T15:30:00Z",
  "version": "pve-manager/8.2.4",
  "nodes": [
    {
      "name": "pve-1",
      "status": "online",
      "cpu_load": 35.0,
      "memory_total_mb": 131072,
      "memory_used_mb": 65536,
      "disk_io_delay_ms": 12.5,
      "diskstat": [{"dev": "sda", "io_ms": 12.5}],
      "vms": [...],
      "containers": [...],
      "storages": [...],
      "networks": [...]
    }
  ],
  "ceph": { "health": "HEALTH_OK", ... }
}
→ {"ok": true, "scan_task_id": 1}
```

---

## 数据采集流程

### 采集顺序

```
1. POST /access/ticket          → 获取 PVE 认证票据
2. GET  /version                → PVE 版本
3. GET  /cluster/status         → 集群节点列表
4. FOR EACH node:
   ├── GET /nodes/{node}/status     → 节点状态 (CPU/内存/磁盘/Swap/I/O延迟)
   ├── GET /nodes/{node}/qemu       → VM 列表 (含实时性能)
   ├── GET /nodes/{node}/lxc        → LXC 列表
   ├── GET /nodes/{node}/storage    → 存储列表
   └── GET /nodes/{node}/network    → 网络接口
5. GET  /cluster/ceph/status    → Ceph 状态 (可选)
6. POST /api/agent/scan/upload/ → 上传到平台
```

### 单位转换规则

| 原始 (PVE API) | 目标 (DB) | 公式 |
|---------------|----------|------|
| bytes (内存) | MB | `value // 1048576` |
| bytes (磁盘) | GB | `round(value / 1073741824, 2)` |
| CPU 0~1 | 百分比 | `round(value * 100, 1)` |
| io_ms | 毫秒 | 直接使用 |

---

## 生命周期管理

### 状态机

```
                    ┌──────────┐
         安装脚本    │ 已安装    │
        ─────────→ │ (未运行)  │
                    └────┬─────┘
                         │ systemctl start
                         ▼
                    ┌──────────┐
                    │ 运行中    │ ←──────────────┐
                    │ (online) │                 │
                    └────┬─────┘                 │
                         │                       │
            ┌────────────┼────────────┐          │
            │            │            │          │
            ▼            ▼            ▼          │
       ┌────────┐  ┌────────┐  ┌────────┐       │
       │ 停止    │  │ 错误    │  │ 离线    │       │
       │        │  │ (error)│  │(offline)│       │
       └────────┘  └────────┘  └───┬────┘       │
            │            │         │             │
            │            │    3×60s 无心跳       │
            │            │         │             │
            ▼            ▼         ▼             │
       ┌─────────────────────────────────┐      │
       │     平台标记 Agent 为 offline     │      │
       └─────────────────────────────────┘      │
                         │                       │
                         │ systemctl restart     │
                         └───────────────────────┘

卸载: systemctl stop → 通知平台 → 删除文件
```

### Agent 运行时行为

| 事件 | 行为 |
|------|------|
| 启动 | 认证 PVE → 启动心跳线程 → 启动扫描循环 |
| 心跳失败 | 记录警告日志，继续运行 |
| 扫描失败 | 记录错误日志，更新 Agent.error_message，等待下次扫描 |
| PVE 认证失败 | 记录错误，等待下次扫描重试 |
| 平台不可达 | 记录警告，继续本地缓存，平台恢复后自动重连 |
| 进程异常退出 | systemd 自动重启（Restart=always） |
| 收到 SIGTERM | 优雅停止，通知平台 offline |

---

## 安全设计

### Agent Token

- `agent_token` 由平台生成，绑定到特定集群
- 仅在安装时使用一次（注册接口）
- 注册后改用 `agent_id` 通信
- 支持在平台重置 token（使旧 Agent 失效）

### 通信安全

- Agent → PVE API：HTTPS（自签证书，跳过验证）
- Agent → 平台：HTTPS（生产环境必须）
- 所有 API 无 JWT 认证，依赖 agent_id 保密

### 本地存储

- 配置文件：`~/.config/pve-agent/config.yaml`（权限 600）
- 包含 PVE 密码（明文，建议后续加密）
- 安装目录：`/opt/pve-agent/`

### systemd 加固

```ini
NoNewPrivileges=true       # 禁止提权
ProtectSystem=strict       # 只读系统目录
ProtectHome=read-only      # 只读用户目录
ReadWritePaths=...         # 仅允许写入必要路径
```

---

## 离线部署

### 离线安装包

```bash
# 在有网络的机器上打包
cd agent/
pip download -d ./packages pve-agent
tar czf pve-agent-offline.tar.gz packages/ install.sh

# 上传到 PVE 节点
scp pve-agent-offline.tar.gz root@192.168.1.100:/tmp/

# 在 PVE 节点上安装
cd /tmp && tar xzf pve-agent-offline.tar.gz
./install.sh --offline --token xxx --platform https://platform:8000
```

### 离线安装脚本逻辑

```bash
if [ "$OFFLINE" = true ]; then
  # 从本地 packages/ 安装
  "$INSTALL_DIR/venv/bin/pip" install --no-index \
    --find-links=./packages pve-agent
else
  # 从 PyPI 或平台安装
  "$INSTALL_DIR/venv/bin/pip" install pve-agent
fi
```

---

## 文件结构

```
agent/
├── pyproject.toml          # 打包配置
├── DESIGN.md               # 本文档
└── agent/
    ├── __init__.py          # 版本号
    ├── cli.py               # CLI 入口（status/update/uninstall）
    ├── config.py            # 配置管理
    ├── pve_client.py        # PVE API 客户端
    ├── scanner.py           # 数据采集 + 单位转换
    ├── uploader.py          # 上报到平台
    └── scheduler.py         # 心跳 + 扫描调度器

Django 平台新增:
├── apps/agent_api/
│   ├── views.py             # + unregister / version / install.sh
│   ├── install_script.py    # install.sh 模板生成
│   └── urls.py              # + 3 个新路由
```

---

## 开发计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1 | Agent 核心代码（采集+上传+心跳） | ✅ 已完成 |
| 2 | Django Agent API（4个接口） | ✅ 已完成 |
| 3 | 测试用例（40个） | ✅ 已完成 |
| 4 | CLI 命令（status/update/uninstall） | 待开发 |
| 5 | 一键安装脚本（install.sh） | 待开发 |
| 6 | systemd 服务模板 | 待开发 |
| 7 | 平台侧新增接口（unregister/version/install.sh） | 待开发 |
| 8 | 前端集群页展示安装命令 | 待开发 |
