# PVE Cluster Scan

[中文](README.md) | **English** | [Deutsch](README.de.md)

PVE Cluster Scanning & Management Platform — A full-stack solution built with Django 5 + Vue 3, supporting multi-cluster and multi-agent deployment for real-time Proxmox VE monitoring.

## Features

- **Multi-Cluster Management**: Manage multiple PVE clusters from a single account with unified monitoring
- **Agent Auto-Collection**: Single-file zero-dependency Python Agent, one-click curl installation, auto-scanning nodes/VMs/containers/storage/networks/Ceph/SDN status
- **Real-Time Dashboard**: Stat cards, alert list, resource trend charts (ECharts), node status table
- **Resource Management**: Nodes, VMs (QEMU), LXC containers, storage, network interfaces, Ceph storage clusters, HA high availability, SDN virtual networks
- **AI Assistant with Tool Calling**: LangChain-powered AI assistant that autonomously queries cluster data via Tool Calling — no more stuffing all data into prompts
- **Agent Auto-Update**: Platform sends update commands, Agent auto-upgrades and restarts
- **Network Topology**: Interactive SVG visualization of node-network connections
- **Dependency Mapping**: Drag-andzoomable SVG dependency graph (VM/LXC → Node → Storage → Network)
- **User Authentication**: JWT login/register/password reset, operation log audit
- **Light/Dark Theme**: Default dark mode, one-click switch, preference persistence

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12 + Django 5.0 + DRF + SimpleJWT |
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| Charts | ECharts + vue-echarts |
| AI | LangChain + LangChain-OpenAI (LLM streaming + Tool Calling) |
| Agent | Python stdlib (zero dependencies) |

## Quick Start

### One-Click Start

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Database migration
python manage.py migrate

# Start (backend + frontend build + uvicorn)
./dev_start.sh
```

### Start Separately

```bash
source .venv/bin/activate
uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --reload
cd frontend && npm run dev   # Vite dev server
```

Visit `http://localhost:8066`.

### Agent Installation

One-click install on a PVE node:

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?token=<token>&platform=<url>' | bash
```

Or manual install:

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?agent=1' -o agent.py
python3 agent.py install     # Interactive config + register + systemd install
```

## Project Structure

```
pve-cluster-scan/
├── config/                 # Django project configuration
│   ├── asgi.py             #   ASGI entry (uvicorn)
│   └── sse_handler.py      #   SSE streaming handler (bypasses Django middleware)
├── apps/
│   ├── accounts/           # User auth & logs & AI assistant
│   │   ├── llm_service.py  #   LangChain LLM wrapper (build_llm / stream_chat / stream_chat_with_tools)
│   │   ├── llm_tools.py    #   Tool Calling: 8 PVE data query tools for LLM
│   │   └── chat_context.py #   PVE context injection (fallback)
│   ├── clusters/           # Cluster management (CRUD + Agent list)
│   ├── agent_api/          # Agent communication (register/heartbeat/scan upload/task dispatch)
│   ├── dashboard/          # Dashboard query API
│   └── scanner/            # Scan data & auto-detection
├── frontend/               # Vue 3 + Vite frontend
│   └── src/views/          # Pages (dashboard/clusters/nodes/VMs/containers/sdn/settings etc.)
├── agent/                  # Agent single file (zero-dependency Python script)
├── data-structure/         # PVE data structure analysis docs
└── dev_start.sh            # One-click start script
```

## AI Assistant (Tool Calling)

The AI assistant uses **LangChain Tool Calling** instead of static context injection:

```
User asks: "What's the CPU status on pve-1?"
  → LLM decides to call get_node_status(node_name="pve-1")
  → Tool executes, queries database
  → LLM generates answer based on real data
```

**Benefits over static injection:**
- Only fetches relevant data (~200 tokens vs thousands)
- LLM decides what to query — no irrelevant data wasted
- Supports multi-round follow-up questions
- Automatic fallback if LLM doesn't support tool calling

**8 Data Tools:**

| Tool | Description |
|------|-------------|
| `get_cluster_summary` | Cluster overview (PVE version, node/VM/container counts) |
| `get_node_status` | Node CPU, memory, disk, uptime (all or specific) |
| `get_vm_list` | VM list or specific VM details |
| `get_container_list` | LXC container list or specific container details |
| `get_storage_list` | Storage capacity and usage |
| `get_ceph_status` | Ceph health, OSD status, storage pools |
| `get_network_info` | Network interfaces + SDN zones/VNets/subnets |
| `get_ha_resources` | HA resource status and configuration |

## API Overview

| Module | Endpoint | Description |
|--------|----------|-------------|
| Auth | `/api/auth/` | Login/register/password reset/user info/operation logs |
| Agent | `/api/agent/` | Register/heartbeat/scan upload/tasks/version/install script |
| Dashboard | `/api/dashboard/` | Stats/alerts/trends/node status |
| Clusters | `/api/clusters/` | Cluster CRUD + Agent list |
| Scanner | `/api/scanner/` | Node/VM/container/storage/network/Ceph/HA/SDN queries |

Detailed API docs: `data-structure/api-interfaces.md`.

## Testing

```bash
# Run all tests (211+ test cases)
python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2

# Run LLM/Tool Calling tests only
python manage.py test apps.accounts.tests_llm --verbosity=1
```

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).

You are free to use, modify, and distribute this software, but if you provide the software as a network service, you must make the complete modified source code publicly available.
