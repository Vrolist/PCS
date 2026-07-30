# PVE Cluster Scan

[中文](README.md) | [English](README.en.md) | **Deutsch**

PVE-Cluster-Scanning- und Managementplattform — Eine Full-Stack-Lösung mit Django 5 + Vue 3, die Multi-Cluster- und Multi-Agent-Bereitstellung für das Echtzeit-Monitoring von Proxmox VE unterstützt.

## Funktionen

- **Multi-Cluster-Management**: Verwalten Sie mehrere PVE-Cluster von einem einzigen Konto aus mit einheitlichem Monitoring
- **Agent-Auto-Erfassung**: Einzel-Datei-Null-Abhängigkeiten-Python-Agent, Curl-Ein-Klick-Installation, automatisches Scannen von Knoten/VMs/Containern/Storage/Netzwerken/Ceph/SDN-Status
- **Echtzeit-Dashboard**: Statistik-Karten, Warnungsliste, Ressourcen-Trenddiagramme (ECharts), Knoten-Status-Tabelle
- **Ressourcen-Management**: Knoten, VMs (QEMU), LXC-Container, Storage, Netzwerkschnittstellen, Ceph-Speichercluster, HA-Hochverfügbarkeit, SDN-Virtual Networks
- **KI-Assistent mit Tool Calling**: LangChain-gestützter KI-Assistent, der über Tool Calling autonom Clusterdaten abruft — kein Daten-Stopfen in Prompts mehr
- **Agent-Auto-Update**: Plattform sendet Update-Befehle, Agent aktualisiert und startet automatisch neu
- **Netzwerktopologie**: Interaktive SVG-Visualisierung von Knoten-Netzwerk-Verbindungen
- **Abhängigkeitszuordnung**: Zoom- und verschiebbare SVG-Abhängigkeitsgraphen (VM/LXC → Knoten → Storage → Netzwerk)
- **Benutzerauthentifizierung**: JWT Login/Registrierung/Passwort-Zurücksetzung, Betriebsprotokoll-Audit
- **Hell/Dunkel-Theme**: Standard Dunkelmodus, Ein-Klick-Umschaltung, Einstellungspersistenz

## Technologie-Stack

| Schicht | Technologie |
|---------|------------|
| Backend | Python 3.12 + Django 5.0 + DRF + SimpleJWT |
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| Diagramme | ECharts + vue-echarts |
| KI | LangChain + LangChain-OpenAI (LLM-Streaming + Tool Calling) |
| Agent | Python stdlib (Null-Abhängigkeiten) |

## Schnellstart

### Ein-Klick-Start

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Datenbankmigration
python manage.py migrate

# Starten (Backend + Frontend-Build + uvicorn)
./dev_start.sh
```

### Separat starten

```bash
source .venv/bin/activate
uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --reload
cd frontend && npm run dev   # Vite Dev-Server
```

Besuchen Sie `http://localhost:8066`.

### Agent-Installation

Ein-Klick-Installation auf einem PVE-Knoten:

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?token=<token>&platform=<url>' | bash
```

Oder manuelle Installation:

```bash
curl -fsSL 'http://platform:8066/api/agent/install.sh?agent=1' -o agent.py
python3 agent.py install     # Interaktive Konfiguration + Registrierung + systemd-Installation
```

## Projektstruktur

```
pve-cluster-scan/
├── config/                 # Django-Projektkonfiguration
│   ├── asgi.py             #   ASGI-Einstiegspunkt (uvicorn)
│   └── sse_handler.py      #   SSE-Streaming-Handler (umgeht Django-Middleware)
├── apps/
│   ├── accounts/           # Benutzerauth. & Protokolle & KI-Assistent
│   │   ├── llm_service.py  #   LangChain-LLM-Wrapper (build_llm / stream_chat / stream_chat_with_tools)
│   │   ├── llm_tools.py    #   Tool Calling: 8 PVE-Datenabfrage-Tools für LLM
│   │   └── chat_context.py #   PVE-Kontext-Injektion (Fallback)
│   ├── clusters/           # Cluster-Management (CRUD + Agent-Liste)
│   ├── agent_api/          # Agent-Kommunikation (Registrierung/Heartbeat/Scan-Upload/Aufgabenvergabe)
│   ├── dashboard/          # Dashboard-Query-API
│   └── scanner/            # Scandaten & Auto-Erkennung
├── frontend/               # Vue 3 + Vite-Frontend
│   └── src/views/          # Seiten (Dashboard/Cluster/Knoten/VMs/Container/SDN/Einstellungen usw.)
├── agent/                  # Agent Einzeldatei (Null-Abhängigkeiten-Python-Skript)
├── data-structure/         # PVE-Datenstrukturanalyse-Dokumentation
└── dev_start.sh            # Ein-Klick-Startskript
```

## KI-Assistent (Tool Calling)

Der KI-Assistent verwendet **LangChain Tool Calling** statt statischer Kontextinjektion:

```
Benutzer fragt: "Wie ist der CPU-Status auf pve-1?"
  → LLM entscheidet, get_node_status(node_name="pve-1") aufzurufen
  → Tool führt Datenbankabfrage aus
  → LLM generiert Antwort basierend auf echten Daten
```

**Vorteile gegenüber statischer Injektion:**
- Nur relevante Daten werden abgerufen (~200 Tokens vs. Tausende)
- LLM entscheidet, was abgefragt wird — kein verschwendeter irrelevant
- Unterstützt mehrstufige Folgefragen
- Automatischer Fallback bei fehlender Tool-Calling-Unterstützung

**8 Datentools:**

| Tool | Beschreibung |
|------|-------------|
| `get_cluster_summary` | Cluster-Übersicht (PVE-Version, Knoten/VM/Container-Zahlen) |
| `get_node_status` | Knoten CPU, Arbeitsspeicher, Festplatte, Laufzeit |
| `get_vm_list` | VM-Liste oder bestimmte VM-Details |
| `get_container_list` | LXC-Container-Liste oder bestimmte Container-Details |
| `get_storage_list` | Storage-Kapazität und -Nutzung |
| `get_ceph_status` | Ceph-Gesundheit, OSD-Status, Storage-Pools |
| `get_network_info` | Netzwerkschnittstellen + SDN-Zonen/VNets/Subnetze |
| `get_ha_resources` | HA-Ressourcen-Status und -Konfiguration |

## API-Übersicht

| Modul | Endpunkt | Beschreibung |
|-------|----------|-------------|
| Auth | `/api/auth/` | Login/Registrierung/Passwort-Zurücksetzung/Benutzerinfo/Betriebsprotokolle |
| Agent | `/api/agent/` | Registrierung/Heartbeat/Scan-Upload/Aufgaben/Version/Installationsskript |
| Dashboard | `/api/dashboard/` | Statistiken/Warnungen/Trends/Knotenstatus |
| Cluster | `/api/clusters/` | Cluster-CRUD + Agent-Liste |
| Scanner | `/api/scanner/` | Knoten/VM/Container/Storage/Netzwerk/Ceph/HA/SDN-Abfragen |

Detaillierte API-Dokumentation: `data-structure/api-interfaces.md`.

## Tests

```bash
# Alle Tests ausführen (211+ Testfälle)
python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2

# Nur LLM/Tool Calling Tests
python manage.py test apps.accounts.tests_llm --verbosity=1
```

## Lizenz

Dieses Projekt steht unter der [GNU Affero General Public License v3.0](LICENSE).

Sie dürfen diese Software frei verwenden, ändern und verbreiten, aber wenn Sie die Software als Netzwerkdienst anbieten, müssen Sie den vollständigen geänderten Quellcode öffentlich verfügbar machen.
