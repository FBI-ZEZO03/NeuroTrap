# NeuroTrap CADN — Claude Code Guide

## Project Overview

NeuroTrap CADN (Cognitive Adaptive Deception Network) is a production honeypot and threat-analysis platform. It detects attackers, profiles their behavior with ML, generates personalized deception environments, and surfaces everything through a real-time SOC dashboard.

---

## Production Deployment

| Property | Value |
|----------|-------|
| Server | VPS · Ubuntu 24.04 · 6 CPU · 11 GB RAM · 193 GB disk |
| Public IP | 13.140.144.118 |
| SSH port | **50402** (port 22 is owned by Cowrie honeypot) |
| OS user | `neuro` (sudo, no-password) |
| Project path | `/home/neuro/neurotrap/neurotrap/` |
| Dashboard | `https://13.140.144.118` (self-signed cert) |

---

## Stack

```
docker compose up -d   # from /home/neuro/neurotrap/neurotrap/
```

| Container | Role | Ports |
|-----------|------|-------|
| neurotrap-nginx | Reverse proxy + SSL | 443, 8080 |
| neurotrap-api | Flask REST API + dashboard | 5000 (internal) |
| neurotrap-cowrie | SSH/Telnet honeypot | 22→2222, 23→2223 |
| neurotrap-opencanary | Multi-service honeypot | 21, 80, 445, 1433, 3306, 3389, 5900, 161/udp |
| neurotrap-mongodb | Event & profile storage | internal only |
| neurotrap-monitor | Scapy packet capture + log ingestion | host network |
| neurotrap-behavior | ML classifier & attacker profiler | internal |
| neurotrap-deception | Dynamic honeypot environment spawner | internal |
| neurotrap-galah | LLM-powered web honeypot (disabled) | 8088 |

---

## Known Fixes Applied (do not revert)

### 1. Monitor → MongoDB connectivity
`neurotrap-monitor` uses `network_mode: host` for packet capture. Docker internal networks (`elk-net`, `management-net`) block host port publishing, so MongoDB cannot be exposed to localhost. **Fix:** a non-internal `monitor-bridge` network (subnet `172.25.0.0/24`) connects MongoDB at static IP `172.25.0.10`. The monitor's `MONGO_URI` uses this IP directly.

### 2. Cowrie log volume wrong path
Cowrie's working directory is `/cowrie/cowrie-git`, not `/cowrie`. Logs land at `/cowrie/cowrie-git/var/log/cowrie/`. The volume was previously mounted at `/cowrie/var/log/cowrie` (wrong). **Fix:** volume now mounted at `/cowrie/cowrie-git/var/log/cowrie`.

### 3. Cowrie log volume permissions
Volume created owned by root; Cowrie runs as uid 999. **Fix:** `chown 999:999` on the volume host path.

### 4. Cowrie log volume not mounted in monitor
The monitor container was missing the `cowrie-logs` volume. **Fix:** added `cowrie-logs:/cowrie/logs:ro` to monitor volumes.

### 5. No cowrie_sessions being built
The behavior engine reads from `cowrie_sessions` to build attacker profiles, but nothing was populating that collection. **Fix:** `CowrieSessionBuilder` added to `src/detection/log_pipeline.py` — aggregates per-session Cowrie JSON events and writes complete session docs to `cowrie_sessions` on `cowrie.session.closed`.

### 6. Honeypot sensor hits always 0
`/api/honeypots` queried `alert_events` by `honeypot_source` ("ssh", "http", …) but events store `honeypot_source: "cowrie"`. **Fix:** query changed to use `dst_port` instead.

### 7. Honeypots page showing nothing
The Honeypots nav section only showed deception environments (empty). **Fix:** page rebuilt to show three sections: live sensors (hit counts + status), recent attacker sessions table, and dynamic deception environments.

### 8. Deception environments not being created
Threshold was `threat_score >= 30`; real attacker scores were ~15–25 after a few sessions. **Fix:** threshold lowered to `>= 10` in `src/deception/main.py`.

### 9. CBEE profiles loading forever
`/api/cbee/injections` crashed with HTTP 500 due to `if db:` check on a PyMongo database object (PyMongo raises `NotImplementedError` for truth-value testing). The `Promise.all` in the frontend silently swallowed the error, leaving the profiles panel stuck on "Loading…". **Fix:** changed to `if db is not None:`. Also added auto-scoring of bias profiles from `attacker_profiles` when `cbee_profiles` is empty.

---

## Data Pipeline

```
Cowrie JSON log
    → CowrieSessionBuilder (log_pipeline.py)
        → cowrie_sessions (MongoDB)
            → BehaviorEngine (behavior_engine.py)
                → attacker_profiles (MongoDB)
                    → DeceptionEngine (deception_engine.py)
                        → deception_environments (MongoDB)

AlertEvent (from Cowrie + Scapy)
    → alert_events (MongoDB)
        → /api/events/stats  →  Dashboard KPIs
```

---

## Environment Variables (`.env`)

```
MONGO_USER=admin
MONGO_PASS=<strong password>
MONGO_URI=mongodb://admin:<pass>@mongodb:27017/neurotrap?authSource=admin
SECRET_KEY=<random>
JWT_SECRET=<random>
MONITOR_INTERFACE=eth0
GALAH_PROVIDER=anthropic
GALAH_MODEL=claude-opus-4-8
# ANTHROPIC_API_KEY=   ← uncomment + set to enable Galah
```

---

## Galah (LLM Honeypot)

Currently disabled — crashes without an API key.  
To enable: add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`, then:

```bash
cd /home/neuro/neurotrap/neurotrap
docker compose up -d galah
```

---

## Useful Commands

```bash
# View all container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Live monitor logs
docker logs -f neurotrap-monitor

# Live Cowrie attacker activity
docker logs -f neurotrap-cowrie

# Check event counts in MongoDB
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.getCollectionNames().forEach(c=>print(c+': '+db[c].countDocuments()))"

# Reset all KPI data
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "['alert_events','attacker_profiles','cowrie_sessions','attacker_twins',
           'response_log','deception_environments'].forEach(c=>db[c].deleteMany({}))"

# Restart full stack
cd /home/neuro/neurotrap/neurotrap && docker compose restart
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/events/stats` | Total events, active sessions, by attack type |
| `GET /api/attackers` | Attacker profiles with threat scores and TTPs |
| `GET /api/honeypots` | Sensor hit counts and recent sessions |
| `GET /api/environments` | Active deception environments |
| `GET /api/cbee/profiles` | Cognitive bias profiles per attacker |
| `GET /api/cbee/injections` | Bait injection log |
| `GET /api/twin/list` | Attacker digital twins |
| `GET /api/soc/summary` | AI SOC analyst summary |
| `GET /api/response/log` | Response action log |

---

## Security Notes

- Real SSH is on port **50402** — never change this without updating UFW
- Cowrie owns port 22 on the host — do not run anything else there
- MongoDB is not exposed to the internet — only reachable via Docker networks + `monitor-bridge` (172.25.0.0/24)
- `PermitRootLogin yes` in sshd_config — should be changed to `prohibit-password`
- `fail2ban` is not installed — consider installing for brute-force protection on port 50402
