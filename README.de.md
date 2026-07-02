# PVE Cluster Scan

[中文](README.md) | [English](README.en.md)

PVE-Cluster-Scanning- und Managementplattform — Eine Full-Stack-Lösung mit Django 5 + Vue 3, die Multi-Cluster- und Multi-Agent-Bereitstellung für das Echtzeit-Monitoring von Proxmox VE unterstützt.

## Funktionen

- **Multi-Cluster-Management**: Verwalten Sie mehrere PVE-Cluster von einem einzigen Konto aus mit einheitlichem Monitoring
- **Agent-Auto-Erfassung**: Einzel-Datei-Null-Abhängigkeiten-Python-Agent, Curl-Ein-Klick-Installation, automatisches Scannen von Knoten/VMs/Containern/Storage/Netzwerken/Ceph-Status
- **Echtzeit-Dashboard**: Statistik-Karten, Warnungsliste, Ressourcen-Trenddiagramme (ECharts), Knoten-Status-Tabelle
- **Ressourcen-Management**: Knoten, VMs (QEMU), LXC-Container, Storage, Netzwerkschnittstellen, Ceph-Speichercluster, HA-Hochverfügbarkeit
- **Agent-Auto-Update**: Plattform sendet Update-Befehle, Agent aktualisiert und startet automatisch neu
- **Benutzerauthentifizierung**: JWT Login/Registrierung/Passwort-Zurücksetzung, Betriebsprotokoll-Audit
- **Hell/Dunkel-Theme**: Standard Dunkelmodus, Ein-Klick-Umschaltung, Einstellungspersistenz

## Technologie-Stack

| Schicht | Technologie |
|---------|------------|
| Backend | Python 3.12 + Django 5.0 + DRF + SimpleJWT |
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| Diagramme | ECharts + vue-echarts |
| Agent | Python stdlib (Null-Abhängigkeiten) |

## Schnellstart

### Ein-Klick-Start

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Datenbankmigration
python manage.py migrate

# Starten (Backend + Vite-Frontend)
./dev_start.sh
```

### Separat starten

```bash
python manage.py runserver 0.0.0.0:8066    # Django
cd frontend && npm run dev                  # Vite (:5173)
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
├── apps/
│   ├── accounts/           # Benutzerauthentifizierung & Betriebsprotokolle
│   ├── clusters/           # Cluster-Management (CRUD + Agent-Liste)
│   ├── agent_api/          # Agent-Kommunikation (Registrierung/Heartbeat/Scan-Upload/Aufgabenvergabe)
│   ├── dashboard/          # Dashboard-Query-API
│   └── scanner/            # Scandaten & Auto-Erkennung
├── frontend/               # Vue 3 + Vite-Frontend
│   └── src/views/          # Seiten (Dashboard/Cluster/Knoten/VMs/Container/Einstellungen usw.)
├── agent/                  # Agent Einzeldatei (Null-Abhängigkeiten-Python-Skript)
├── data-structure/         # PVE-Datenstrukturanalyse-Dokumentation
└── dev_start.sh            # Ein-Klick-Startskript
```

## API-Übersicht

| Modul | Endpunkt | Beschreibung |
|-------|----------|-------------|
| Auth | `/api/auth/` | Login/Registrierung/Passwort-Zurücksetzung/Benutzerinfo/Betriebsprotokolle |
| Agent | `/api/agent/` | Registrierung/Heartbeat/Scan-Upload/Aufgaben/Version/Installationsskript |
| Dashboard | `/api/dashboard/` | Statistiken/Warnungen/Trends/Knotenstatus |
| Cluster | `/api/clusters/` | Cluster-CRUD + Agent-Liste |
| Scanner | `/api/scanner/` | Knoten/VM/Container/Storage/Netzwerk/Ceph/HA-Abfragen |

Detaillierte API-Dokumentation: `data-structure/api-interfaces.md`.

## Tests

```bash
python manage.py test apps.agent_api apps.clusters apps.dashboard --verbosity=2
```

## Lizenz

Dieses Projekt steht unter der [GNU Affero General Public License v3.0](LICENSE).

Sie dürfen diese Software frei verwenden, ändern und verbreiten, aber wenn Sie die Software als Netzwerkdienst anbieten, müssen Sie den vollständigen geänderten Quellcode öffentlich verfügbar machen.
