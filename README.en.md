# PVE Cluster Scan

[中文](README.md) | [Deutsch](README.de.md)

PVE Cluster Scanning & Management Platform — A full-stack solution built with Django 5 + Vue 3, supporting multi-cluster and multi-agent deployment for real-time Proxmox VE monitoring.

## Features

- **Multi-Cluster Management**: Manage multiple PVE clusters from a single account with unified monitoring
- **Agent Auto-Collection**: Single-file zero-dependency Python Agent, one-click curl installation, auto-scanning nodes/VMs/containers/storage/networks/Ceph status
- **Real-Time Dashboard**: Stat cards, alert list, resource trend charts (ECharts), node status table
- **Resource Management**: Nodes, VMs (QEMU), LXC containers, storage, network interfaces, Ceph storage clusters, HA high availability
- **Agent Auto-Update**: Platform sends update commands, Agent auto-upgrades and restarts
- **User Authentication**: JWT login/register/password reset, operation log audit
- **Light/Dark Theme**: Default dark mode, one-click switch, preference persistence

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12 + Django 5.0 + DRF + SimpleJWT |
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| Charts | ECharts + vue-echarts |
| Agent | Python stdlib (zero dependencies) |

## Quick Start

### One-Click Start

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Database migration
python manage.py migrate

# Start (backend + Vite frontend)
./dev_start.sh
```

### Start Separately

```bash
python manage.py runserver 0.0.0.0:8066    # Django
cd frontend && npm run dev                  # Vite (:5173)
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
├── apps/
│   ├── accounts/           # User authentication & operation logs
│   ├── clusters/           # Cluster management (CRUD + Agent list)
│   ├── agent_api/          # Agent communication (register/heartbeat/scan upload/task dispatch)
│   ├── dashboard/          # Dashboard query API
│   └── scanner/            # Scan data & auto-detection
├── frontend/               # Vue 3 + Vite frontend
│   └── src/views/          # Pages (dashboard/clusters/nodes/VMs/containers/settings etc.)
├── agent/                  # Agent single file (zero-dependency Python script)
├── data-structure/         # PVE data structure analysis docs
└── dev_start.sh            # One-click start script
```

## API Overview

| Module | Endpoint | Description |
|--------|----------|-------------|
| Auth | `/api/auth/` | Login/register/password reset/user info/operation logs |
| Agent | `/api/agent/` | Register/heartbeat/scan upload/tasks/version/install script |
| Dashboard | `/api/dashboard/` | Stats/alerts/trends/node status |
| Clusters | `/api/clusters/` | Cluster CRUD + Agent list |
| Scanner | `/api/scanner/` | Node/VM/container/storage/network/Ceph/HA queries |

Detailed API docs: `data-structure/api-interfaces.md`.

## Testing

```bash
python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2
```

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).

You are free to use, modify, and distribute this software, but if you provide the software as a network service, you must make the complete modified source code publicly available.
