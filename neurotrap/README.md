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
        ├── alert_events    → Dashboard KPIs + Live Feed
        └── cowrie_sessions → BehaviorEngine
                                └── reclassify_intent() + threat score
                                      ├── attacker_profiles
                                      │     ├── ResponseEngine → response_log
                                      │     ├── DeceptionEngine → deception_environments
                                      │     └── CBEEEngine → cbee_profiles + cbee_injections
                                      └── Dashboard: Threat Actors, Behavior Analysis

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
MONGO_USER=admin
MONGO_PASS=<strong-random-password>
SECRET_KEY=<64-char-random-string>
JWT_SECRET=<64-char-random-string>
ADMIN_PASS=<strong-random-password>
ANALYST_PASS=<strong-random-password>
MONITOR_INTERFACE=eth0   # or your primary NIC
```

Optional MFA setup (admin login only):
```
MFA_ENABLED=1
MFA_SECRET=<base32-secret>    # generate: python -c "import pyotp; print(pyotp.random_base32())"
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

Accept the self-signed certificate warning.

Default credentials:

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Admin | `admin` | `neurotrap2024` | Full access — change via `ADMIN_PASS` in `.env` |
| Analyst | `analyst` | `analyst2024` | Read-only — change via `ANALYST_PASS` in `.env` |

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
| Behavior | `src/behavior/` | ML classifier, TTP extractor, attacker profiles, intent reclassification |
| Deception | `src/deception/` | Dynamic honeypot generator, fake credentials |
| Response | `src/response/` | Autonomous action engine (block/isolate/slow/log) |
| CBEE | `src/cbee/` | Cognitive Bias Exploitation Engine |
| GADCF | `src/gadcf/` | Generative Attacker-Driven Content Fabrication |
| FHIM | `src/fhim/` | Federated Honeypot Intelligence Mesh |
| Digital Twin | `src/twin/` | Attacker behavioral twin + kill-chain predictor |
| SOC Analyst | `src/soc_analyst/` | AI-powered triage and reporting |
| API | `src/api/` | Flask REST API + WebSocket backend |
| Dashboard | `dashboard/` | Real-time HTML/JS monitoring UI |

---

## Dashboard Sections

### Operations
| Section | What it shows |
|---------|---------------|
| Dashboard | KPI overview: total events, active sessions, IPs blocked, environments deployed, threat level, attack type breakdown; live feed (paginated, seeded from API on load) |
| Threat Actors | Attacker profiles with threat scores (LOW/MEDIUM/HIGH/CRITICAL), TTPs, intent classification, session history |
| Live Events | Full paginated event log from all honeypots with type/severity filters |
| Honeypots | Live sensor hit counts, recent attacker sessions, active deception environments |
| Response Log | Autonomous response actions: block_emergency, isolate_alert, slow_redirect, log_only |

### Intelligence
| Section | What it shows |
|---------|---------------|
| Threat Intel | IOC feed, top source countries, top targeted ports, attack type distribution |
| Geo Map | Live global attack origin map with animated arcs, threat-level markers, IP grid |
| MITRE ATT&CK | Full-viewport heatmap navigator, top observed techniques, technique detail panel |
| Behavior Analysis | ML intent distribution, tier breakdown, top commands (path-normalized), classified profiles table |

### Innovations
| Section | What it shows |
|---------|---------------|
| CBEE | Cognitive bias profiles per attacker, bait injection log, live session scorer |
| GADCF | Generative fake content assets (env files, emails, code repos, wiki pages, DB dumps) |
| FHIM | Federated learning node status, FedAvg rounds, differential privacy metrics |
| ADT | Attacker digital twins, kill-chain progression, predicted next moves, forward simulation |
| AI Analyst | AI triage queue, per-IP incident reports, natural-language SOC Q&A |

---

## Threat Score Calculation

Threat score (0–100) is computed on every session update in `src/behavior/attacker_profile.py`:

```
threat_score = (ML confidence × 40)
             + TTP score
             + tier_bonus
             + persistence_bonus
             + volume_bonus
```

| Component | Range | Details |
|-----------|-------|---------|
| ML confidence | 0–40 | Classifier confidence (0.0–1.0) × 40 |
| TTP score | 0–40 | Sum of tactic weights × confidence per tactic |
| Tier bonus | 0–30 | beginner: 0 · automated_bot: +15 · advanced_human: +30 |
| Persistence bonus | 5–65 | Scaled by session_count (see table below) |
| Volume bonus | 0–15 | `min(total_commands // 5, 15)` |

**Persistence bonus tiers** (based on `session_count`):

| Sessions | Bonus |
|----------|-------|
| 1 | 5 |
| 2 | 18 |
| 3–4 | 22 |
| 5–9 | 28 |
| 10–19 | 40 |
| 20–49 | 50 |
| 50–99 | 60 |
| 100+ | 65 |

**Tactic weights** (used in TTP score):

| Tactic | Weight |
|--------|--------|
| Impact | 40 |
| Privilege Escalation | 35 |
| Credential Access | 30 |
| Lateral Movement | 25 |
| Persistence | 20 |
| Command and Control | 15 |
| Defense Evasion | 10 |
| Discovery | 5 |

Score is capped at 100.

---

## Intent Classification

Intent is set by `reclassify_intent()` in `src/behavior/attacker_profile.py`, which examines all commands accumulated across a profile's sessions (not just the latest):

| Intent | Trigger |
|--------|---------|
| `cryptomining` | `xmrig`, miner-related keywords, or `grep.*miner` |
| `malware_deployment` | `wget`/`curl`/`tftp` + `chmod`/`bash`/`.sh`, or `scp -t` + execute |
| `credential_harvesting` | Access to `/etc/shadow`, or brute-force only (no commands) |
| `bot_enrollment` | `crontab`/`.bashrc` persistence, `/ip cloud`, CPU probing, fingerprint-only |
| `lateral_movement` | `ssh`/`scp`/`rsync` with > 3 occurrences |
| `reconnaissance` | Default fallback |

---

## Response Engine

Autonomous responses are triggered by threat score thresholds (`src/response/response_engine.py`):

| Score Range | Action | Description |
|-------------|--------|-------------|
| > 90 | `block_emergency` | iptables DROP + forensic pcap + emergency alert |
| 70–90 | `isolate_alert` | Rate-limit rule + alert |
| 40–70 | `slow_redirect` | tc netem 500ms delay |
| < 40 | `log_only` | Log to response_log only |

The **IPs Blocked** KPI counts both `block_emergency` and `isolate_alert` entries in `response_log`.

---

## Live Feed

The dashboard live feed (`#feed-list`) on the main dashboard:

- Seeded from `/api/events?limit=200` on page load — no empty state on startup
- New events from WebSocket (`new_event`) prepend to page 1 in real-time
- **Paginated**: 20 events per page with Prev/Next navigation
- **● LIVE** badge on page 1; **"N new ↑"** badge on other pages when new events arrive
- Scrollable within each page (390px fixed height, `overflow-y: auto`)
- Events/min rate counter color-coded: green < 3, amber 3–9, red ≥ 10
- Click any event card to open the attacker modal with full profile + threat score

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

### Enabling MFA (admin logins)

```bash
# 1. Get your TOTP secret
docker compose exec api python -c "import pyotp; print(pyotp.random_base32())"

# 2. Add to .env
echo "MFA_SECRET=<secret-from-above>" >> .env
echo "MFA_ENABLED=1" >> .env

# 3. Scan the QR code from the setup endpoint
#    GET https://<host>/api/auth/otp/setup  (requires admin JWT)
#    Returns a base64 PNG you can display in any QR scanner / authenticator app

# 4. Restart the API
docker compose restart api
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
| `alert_events` | Normalized events from all honeypot sources |
| `honeypot_sessions` | Native Python honeypot session records |
| `cowrie_sessions` | Aggregated attacker sessions (commands, duration, credentials) |
| `attacker_profiles` | ML-enriched profiles with threat scores, TTPs, and reclassified intents |
| `attacker_twins` | Behavioral digital twins with kill-chain and predictions |
| `deception_environments` | Tailored honeypot environments per attacker (all, including expired) |
| `cbee_profiles` | Cognitive bias scores per attacker |
| `cbee_injections` | Bait injection log |
| `gadcf_assets` | Generated deception content (env files, emails, code, wikis) |
| `fhim_rounds` / `fhim_aggregation_rounds` | Federated learning round history |
| `response_log` | Autonomous response action log (block_emergency, isolate_alert, slow_redirect, log_only) |
| `soc_reports` | AI-generated SOC incident reports |

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

## Development Workflow

The `./src` and `./dashboard` directories are bind-mounted into the API container, so file changes are picked up immediately.

| Change type | What to do |
|-------------|-----------|
| HTML templates (`dashboard/templates/`) | Normal browser refresh |
| CSS / JS (`dashboard/static/`) | Normal browser refresh (caching disabled) |
| Python source (`src/`) | `docker compose build api && docker compose up -d api` then `docker compose exec nginx nginx -s reload` |

When bumping static assets after major changes, increment the version query string in `index.html`:
```html
<link rel="stylesheet" href="/static/css/main.css?v=3"/>
```

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
scikit-learn · spaCy · Flask · Flask-SocketIO · flask-jwt-extended · pyotp ·
MongoDB · Chart.js · Leaflet.js

---

## Changelog

### v2.1 — Dashboard Polish & KPI Fixes
- **Live feed redesigned** — truly real-time WebSocket feed; paginated (20/page), scrollable within page, seeded from API on load (no "Waiting…" placeholder), ● LIVE badge, "N new ↑" badge when navigated away, events/min rate counter
- **IPs Blocked KPI** — was always 0; now counts `block_emergency` + `isolate_alert` from `response_log`; seeded block/isolate entries for all high-threat attackers
- **Environments Deployed KPI** — was always 0; `/api/environments` now returns all (not just active) + `total` / `active_count` fields
- **CBEE Bait Injections** — engine thread was never started; fixed `_get_cbee()` to call `.start()`; scoring now reads from richer `attacker_profiles` instead of `cowrie_sessions`
- **Top Attack Origins** — expanded to show up to 22 countries

### v2.0 — Behavior & Detection Overhaul
- **Threat scores** — rewrote score formula with tiered persistence bonus (5–65 by session count), volume bonus, higher tier bonuses; attackers with 100+ sessions now correctly reach CRITICAL
- **Intent classification** — added `reclassify_intent()` examining all accumulated commands; 6 intent classes now populated correctly (was 100% reconnaissance)
- **Attack type distribution** — mapped all Cowrie event IDs; `_COWRIE_SKIP` filters pure metadata; `unknown` replaced with `tool_fingerprint` / `protocol_anomaly`
- **Top commands** — path normalization (`_normCmd()`) prevents `/bin/ls`, `./ls`, `ls` from counting as separate entries
- **SCP misclassification** — fixed SCP upload (`scp -t`) being classified as `lateral_movement` instead of `malware_deployment`

### v1.x — Foundation
- **MFA / TOTP support** — admin login now supports TOTP second factor via `pyotp`
- **Analyst role** — second built-in user with read-only access; role encoded in JWT
- **Response cache** — 30-second in-memory cache with query-string-aware keys on all expensive read endpoints
- **GeoIP enrichment** — background daemon resolves lat/lon for attacker profiles via ip-api.com
- **Threat Intel API** (`GET /api/intel`) — IOC list, top countries, top targeted ports, attack type distribution, active campaigns
- **Honeypot session drill-down** (`GET /api/honeypots/sessions/<src_ip>`) — all sessions, events, credentials, and command history for one IP
- **Deception threshold lowered** — environments now spawn at `threat_score >= 10` (was 30)
- **Dashboard preload** — all sections loaded on page open; no per-section loading spinners
- **MITRE ATT&CK page** — full-viewport height with scrollable technique list
- **Geo Map** — full-page section under Intelligence with animated attack arcs and IP grid
- **Dionaea disabled** — crashes (SIGTRAP) on kernel 6.8; OpenCanary now covers its ports

---

*NeuroTrap CADN — Not just a honeypot. An active, thinking defense.*
