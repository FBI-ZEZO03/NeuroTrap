# NeuroTrap — CADN (Cognitive Adaptive Deception Network)

> **Graduation Project · Cybersecurity · Active Defense & Threat Intelligence**
>
> An intelligent honeypot platform that detects attackers, profiles their behavior with ML,
> dynamically generates personalized deception environments, and surfaces everything through
> a real-time SOC dashboard.

---

## Live Demo

| | |
|-|-|
| Dashboard | `https://13.140.144.118` (accept self-signed cert) |
| SSH honeypot | `ssh root@13.140.144.118` (port 22 → Cowrie) |

---

## Architecture

```
Internet
  ├── :22/:23   → Cowrie (SSH/Telnet honeypot)
  ├── :80/:21/:445/:3306/:1433/:3389/:5900/:161 → OpenCanary (multi-service)
  ├── :443/:8080 → Nginx → Flask API + Dashboard
  └── :8088     → Galah (LLM web honeypot, requires API key)

Cowrie JSON logs
  └── LogIngestionPipeline + CowrieSessionBuilder
        ├── alert_events    → Dashboard KPIs
        └── cowrie_sessions → BehaviorEngine → attacker_profiles
                                              → DeceptionEngine → deception_environments

Scapy PacketMonitor (host network)
  └── alert_events → Dashboard KPIs
```

---

## Quick Start

### Prerequisites
- Ubuntu 22.04+ or Debian 12+
- Docker + Docker Compose v2
- Ports 22, 23, 80, 443, 8080 available

### 1. Clone & configure

```bash
git clone https://github.com/FBI-ZEZO03/NeuroTrap.git neurotrap
cd neurotrap/neurotrap
cp .env.example .env
nano .env   # set MONGO_PASS, SECRET_KEY, JWT_SECRET
```

Minimum `.env` values to set:
```
MONGO_PASS=<strong-random-password>
SECRET_KEY=<64-char-random-string>
JWT_SECRET=<64-char-random-string>
MONITOR_INTERFACE=eth0   # or your primary NIC
```

### 2. Generate SSL certificate

```bash
bash scripts/generate_ssl_cert.sh
```

### 3. Launch the stack

```bash
docker compose up -d
```

### 4. Open the dashboard

```
https://<your-server-ip>
```

Accept the self-signed certificate warning. Default credentials: `admin` / `neurotrap2024`.

---

## Production Deployment Notes

### SSH port
Real SSH must be moved off port 22 before starting the stack — Cowrie takes over port 22.

```bash
# Change SSH to port 50402 (or any high port)
sed -i 's/^#Port 22/Port 50402/' /etc/ssh/sshd_config
systemctl restart sshd

# Allow the new port and all honeypot ports in UFW
ufw allow 50402/tcp comment "SSH management"
ufw allow 22/tcp comment "Cowrie SSH honeypot"
ufw allow 23/tcp comment "Cowrie Telnet"
ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 8080/tcp
ufw allow 21/tcp 445/tcp 1433/tcp 3306/tcp 3389/tcp 5900/tcp
ufw allow 161/udp
ufw enable
```

### Network architecture
The stack uses three Docker networks:

| Network | Type | Purpose |
|---------|------|---------|
| `honeypot-net` | bridge (external) | Honeypot containers + Nginx |
| `elk-net` | bridge (internal) | MongoDB ↔ behavior/deception engines |
| `management-net` | bridge (internal) | MongoDB ↔ API |
| `monitor-bridge` | bridge (external, `172.25.0.0/24`) | MongoDB static IP for host-network monitor |

MongoDB has a static IP `172.25.0.10` on `monitor-bridge` so the packet monitor (which runs on the host network for raw packet capture) can reach it.

---

## Module Overview

| Module | Path | Purpose |
|--------|------|---------|
| Data layer | `src/db/` | MongoDB + embedded SQLite fallback |
| Detection | `src/detection/` | Packet capture, log ingestion, session builder |
| Behavior | `src/behavior/` | ML classifier, TTP extractor, attacker profiles |
| Deception | `src/deception/` | Dynamic honeypot generator, fake data |
| Response | `src/response/` | Autonomous action engine |
| CBEE | `src/cbee/` | Cognitive Bias Exploitation Engine |
| GADCF | `src/gadcf/` | Generative Attacker-Driven Content Fabrication |
| FHIM | `src/fhim/` | Federated Honeypot Intelligence Mesh |
| ASHRTA | `src/ashrta/` | Adaptive Self-Hardening & Red Team Automation |
| Digital Twin | `src/twin/` | Attacker behavioral twin + kill-chain predictor |
| SOC Analyst | `src/soc_analyst/` | AI-powered triage and reporting |
| API | `src/api/` | Flask REST API + WebSocket backend |
| Dashboard | `dashboard/` | Real-time HTML/JS monitoring UI |

---

## Dashboard Sections

| Section | What it shows |
|---------|---------------|
| Dashboard | KPI overview: events, active sessions, threat level, attack breakdown |
| Threat Actors | Attacker profiles with threat scores, TTPs, intent classification |
| Live Events | Real-time event feed from all honeypots |
| Honeypots | Live sensor hits, recent attacker sessions, dynamic deception environments |
| Response Log | Autonomous response actions |
| CBEE | Cognitive bias profiles, bait injections, live session scorer |
| GADCF | Generative fake content assets |
| FHIM | Federated learning node status |
| ASHRTA | Hardening reports and automated patches |
| Digital Twin | Attacker behavioral models and kill-chain forecasts |
| SOC Analyst | AI triage queue, incident reports, natural-language Q&A |

---

## Honeypots

### External (Docker)

| Honeypot | Protocol | Ports | Notes |
|----------|----------|-------|-------|
| Cowrie | SSH, Telnet | 22, 23 | Full shell emulation, credential capture |
| OpenCanary | SSH, FTP, HTTP, SMB, MySQL, MSSQL, SNMP, VNC, RDP | 21, 80, 445, 1433, 3306, 161, 5900, 3389 | Replaces Dionaea (incompatible with kernel 6.8) |
| Galah | HTTP | 8088 | LLM-powered dynamic responses — requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |

### Enabling Galah

```bash
# Add to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
docker compose up -d galah
```

### Native Python honeypots (optional, no Docker)

```bash
pip install -r requirements/honeypots.txt
python -m src.honeypots.main
# → SSH :2222  HTTP :8081  FTP :2121  Telnet :2323
```

---

## Storage

`src/db.get_db()` returns MongoDB when reachable, or an embedded SQLite fallback automatically. Force SQLite with `NEUROTRAP_FORCE_FALLBACK=1`.

### MongoDB collections

| Collection | Purpose |
|-----------|---------|
| `alert_events` | Normalized events from all sources |
| `cowrie_sessions` | Aggregated attacker sessions (commands, duration, credentials) |
| `attacker_profiles` | ML-enriched profiles with threat scores and TTPs |
| `deception_environments` | Active tailored honeypot environments per attacker |
| `cbee_profiles` | Cognitive bias scores per attacker |
| `cbee_injections` | Bait injection log |
| `attacker_twins` | Behavioral digital twins |
| `response_log` | Autonomous response action log |

---

## Running Tests

```bash
pip install pytest faker scikit-learn spacy
python -m pytest tests/ -v
```

---

## Simulating an Attack

```bash
python scripts/simulate_attack.py
```

Runs a 5-stage campaign through the local pipeline:
recon → brute-force → login + commands → malware upload → lateral movement.

---

## Key Performance Targets

| Metric | Target |
|--------|--------|
| Classifier F1 (macro) | > 0.85 |
| Event → Dashboard latency | < 5 seconds |
| Environment spawn time | < 30 seconds |
| Response action time | < 10 seconds after threshold |

---

## Tech Stack

Python 3.11 · Docker Compose · Cowrie · OpenCanary · Galah · Scapy ·
scikit-learn · spaCy · Flask · Flask-SocketIO · MongoDB · Chart.js · Leaflet.js

---

*NeuroTrap CADN — Not just a honeypot. An active, thinking defense.*
