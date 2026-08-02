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

## Screenshots

### Dark Theme
![Dark Theme](screenshots/image_black.png)

### Light Theme
![Light Theme](screenshots/image_white.png)

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

## Docker Deployment

PCS images are published on GitHub Container Registry (ghcr.io), supporting multi-arch (amd64/arm64).

### Quick Start (SQLite)

1. Pull the image

```bash
docker pull ghcr.io/vrolist/pcs:latest
```

2. Run (SQLite by default, data stored in volumes)

```bash
docker run -d --name pcs \
  -p 8066:8066 \
  -e DB_ENGINE=sqlite \
  -v pcs_data:/app/data \
  -v pcs_media:/app/media \
  ghcr.io/vrolist/pcs:latest
```

3. Visit `http://<server-ip>:8066`
   Default admin: `pcs` / `123456` (auto-created on first start)

### Using docker compose (recommended)

```yaml
services:
  app:
    image: ghcr.io/vrolist/pcs:latest
    container_name: pcs-app
    environment:
      DB_ENGINE: sqlite
      DB_PATH: /app/data/db.sqlite3
    ports:
      - "8066:8066"
    volumes:
      - app_data:/app/data
      - app_media:/app/media

volumes:
  app_data:
  app_media:
```

### Updating to the Latest Version (all three databases)

One command does it all:

```bash
docker compose up -d --pull always --force-recreate
```

| Flag | Purpose |
|:-----|:--------|
| `up -d` | Start services (background) |
| `--pull always` | Force pull the latest image (overrides local cache) |
| `--force-recreate` | Force recreate the container (with the new image) |
| Named volumes untouched | Data preserved ✅ |

Per-database complete commands:

| Database | Command | Data location |
|:---------|:--------|:--------------|
| SQLite | `cd /opt/pcs-test && docker compose up -d --pull always --force-recreate` | `app_data` volume → `/app/data/db.sqlite3` ✅ |
| MySQL | `cd /opt/pcs-mysql && docker compose up -d --pull always --force-recreate` | `mysql_data` volume → MySQL data directory ✅ |
| PostgreSQL | `cd /opt/pcs-postgres && docker compose up -d --pull always --force-recreate` | `pg_data` volume → PostgreSQL data directory ✅ |

> ⚠️ **Why your data is safe**: `docker compose up -d --pull always --force-recreate` only touches the image and container layers, **never the named volumes** (`app_data` / `mysql_data` / `pg_data`). The old container is removed → the new container mounts the same volume → data stays intact.

| Volume | Database | Contents |
|:-------|:---------|:---------|
| `app_data` | SQLite | db.sqlite3 |
| `mysql_data` | MySQL | MySQL data files |
| `pg_data` | PostgreSQL | PG data files |

> 🚫 **Never use (it deletes data)**: `docker compose down -v` (`-v` removes named volumes = all data gone); `docker volume rm xxx` (manually deleting volumes).

**One-click script (for all databases, recommended to keep in your project):**

```bash
#!/bin/bash
# update_pcs.sh - Update the PCS image and restart (data preserved)
set -e

# Enter the compose directory (accept an argument or auto-detect)
COMPOSE_DIR="${1:-.}"
cd "$COMPOSE_DIR"

echo "=== Updating PCS image ==="
docker compose pull          # pull the latest image

echo "=== Recreating container (data preserved) ==="
docker compose up -d --force-recreate

echo "=== Verifying ==="
docker compose ps
echo "✅ Update complete, data untouched"
```

Usage:

```bash
./update_pcs.sh /opt/pcs-test      # SQLite
./update_pcs.sh /opt/pcs-mysql     # MySQL
./update_pcs.sh /opt/pcs-postgres  # PostgreSQL
```

**Verification after updating:**

```bash
# 1. New image is in effect
docker compose ps

# 2. Service health
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8066/

# 3. Data still there (the pcs superuser should still exist)
docker compose exec app python3 manage.py shell -c \
  "from apps.accounts.models import User; print(f'User count: {User.objects.count()}')"

# 4. Database tables still there
docker compose exec mysql mysql -uroot -p* -e "USE pveclusterscan; SHOW TABLES;" 2>/dev/null | head -5
```

| Requirement | Satisfied |
|:------------|:---------:|
| One command to update + restart | ✅ `docker compose up -d --pull always --force-recreate` |
| Supports all three databases | ✅ Just run it in each compose directory |
| Data not lost | ✅ Named volumes untouched, only image and container replaced |
| Also works for first deployment | ✅ The command is compatible with first start |

Or manually in two steps

```bash
docker pull ghcr.io/vrolist/pcs:latest
docker compose up -d
```

> ⚠️ Updates preserve your data (SQLite lives in named volumes). Never use `docker compose down -v` — it deletes the data volumes.

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
