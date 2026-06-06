# NeuroTrap — CADN (Cognitive Adaptive Deception Network)

> **Graduation Project · Cybersecurity · Active Defense & Threat Intelligence**
>
> An intelligent honeypot system that detects attackers, analyzes their behavior with ML,
> and dynamically generates personalized deception environments to engage and study them.

---

## Quick Start (Ubuntu 22.04)

```bash
# 1. Clone & configure
git clone <your-repo-url> neurotrap
cd neurotrap
cp .env.example .env
nano .env           # set MONGO_PASS, SECRET_KEY, JWT_SECRET, MONITOR_INTERFACE

# 2. Generate SSL cert (dev)
bash scripts/generate_ssl_cert.sh

# 3. Launch the stack
docker compose up -d

# 4. Set up DB indexes
docker compose exec api python scripts/setup_db_indexes.py

# 5. Train the classifier (first time)
docker compose exec behavior-engine python -m src.behavior.train_classifier

# 6. Open dashboard
open https://localhost   # (accept self-signed cert warning)
```

---

## System Architecture

```
Internet → Cowrie/Dionaea/OpenCanary/Galah → Scapy/Zeek Detection → ML Behavior Analysis
         → Deception Engine (personalized honeypots) → Response Engine → Dashboard
```

See [docs/architecture.md](docs/architecture.md) for the full layer diagram.

---

## Module Overview

| Module | Path | Purpose |
|--------|------|---------|
| Honeypots | `src/honeypots/` | Native Python SSH/HTTP/FTP/Telnet sensors (no Docker required) |
| Data layer | `src/db/` | Central DB access — MongoDB with embedded SQLite fallback |
| Detection | `src/detection/` | Packet capture, alert schema, log ingestion |
| Behavior | `src/behavior/` | ML classifier, TTP extractor, attacker profiles |
| Deception | `src/deception/` | Dynamic honeypot generator, fake data |
| Response | `src/response/` | Autonomous action engine + alerting |
| API | `src/api/` | Flask REST API + WebSocket dashboard backend |
| Dashboard | `dashboard/` | Real-time HTML/JS monitoring UI |

---

## Honeypots & Storage

NeuroTrap ships **two kinds of honeypots**:

1. **External (Docker)** — Cowrie (SSH/Telnet) and Dionaea (malware) are the
   hand-deployed core, joined by **OpenCanary** (maintained low-interaction
   multi-service sensor: SSH, FTP, HTTP, SMB, MySQL, MSSQL, SNMP, Telnet, VNC,
   RDP/3389) and **Galah** (LLM-powered web-application honeypot). All run as
   containers via `docker compose up`. Their JSON logs are tailed into the DB by
   `src/detection/log_pipeline.py`.
2. **Native Python** (`src/honeypots/`) — self-contained SSH, HTTP, FTP and
   Telnet sensors that run anywhere Python runs, **no Docker needed**. They
   capture credentials, commands and attack signatures and write them straight
   into the data layer as normalized `AlertEvent`s.

```bash
# Run the native honeypots locally (high ports; no root needed)
python -m src.honeypots.main
# → SSH 2222 · HTTP 8081 · FTP 2121 · Telnet 2323

# Or add them to the Docker stack (privileged ports, opt-in profile)
docker compose --profile native-honeypots up
```

> The SSH honeypot captures full credentials when `paramiko` is installed
> (`pip install -r requirements/honeypots.txt`); otherwise it runs as a
> low-interaction banner sensor.

**Storage** goes through `src/db` (`get_db()` / `get_collection()`). It uses
MongoDB when `MONGO_URI` is reachable and **auto-falls back to an embedded
SQLite document store** (`data/neurotrap.db`) otherwise — so the whole stack
runs end-to-end on a laptop with zero infrastructure. Force the fallback with
`NEUROTRAP_FORCE_FALLBACK=1`. Captures appear at `GET /api/honeypots` and
`GET /api/events`.

---

## Running Tests

```bash
pip install pytest faker scikit-learn spacy
python -m pytest tests/ -v
```

---

## Simulating an Attack (E2E Test)

```bash
python scripts/simulate_attack.py
```

This runs a 5-stage campaign through the local pipeline:
recon → brute-force → login+commands → malware upload → lateral movement.

---

## Key Metrics Targets

| Metric | Target |
|--------|--------|
| Classifier F1 (macro) | > 0.85 |
| Event → Dashboard latency | < 5 seconds |
| Environment spawn time | < 30 seconds |
| Response action time | < 10 seconds after threshold breach |
| Lynis hardening score | > 70 |

---

## Tech Stack

Python 3.11 · Docker Compose · Cowrie · Dionaea · OpenCanary · Galah · Scapy · Zeek ·
scikit-learn · spaCy · Flask · Flask-SocketIO · MongoDB · Chart.js · Leaflet.js

---

*NeuroTrap CADN — This is not just a honeypot. It is an active, thinking defense.*
