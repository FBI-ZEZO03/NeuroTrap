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

### 10. `/api/intel` UnboundLocalError (country_counts)
`intel` endpoint was refactored to use `country_events` internally but line ~1115 still referenced the old name `country_counts`. **Fix:** changed `len(country_counts)` → `len(top_countries)`.

### 11. All threat scores showing LOW
Scores were capped too low because the original formula only used confidence + TTP + a small tier bonus. **Fix:** completely rewrote `_compute_threat_score()` in `src/behavior/attacker_profile.py` with a tiered persistence bonus (5–65 based on session_count), a volume bonus (up to 15), and higher tier bonuses. See threat score section in README.

### 12. All attacker intents showing "reconnaissance"
The ML model fallback defaulted to reconnaissance; accumulated session commands were never re-examined. **Fix:** added `reclassify_intent()` to `AttackerProfile` in `src/behavior/attacker_profile.py` — examines all stored session commands across the full profile to classify: `cryptomining`, `malware_deployment`, `credential_harvesting`, `bot_enrollment`, `lateral_movement`, `reconnaissance`. `recalculate_all()` now calls `reclassify_intent()` before computing the score. Also improved `_rule_based_classify()` in `src/behavior/behavior_engine.py`.

### 13. "unknown" dominating Attack Type Distribution
Most Cowrie metadata events (session open/close, client version, key exchange) were ingested as `attack_type: "unknown"`. **Fix:** added `_COWRIE_SKIP` frozenset in `src/detection/alert_schema.py` for pure metadata events; extended `event_id_map` with all Cowrie event IDs (`cowrie.client.version/kex/var/fingerprint` → `tool_fingerprint`, `cowrie.direct-tcpip.*` → `lateral_movement`, `cowrie.session.file_upload` → `malware_upload`, etc.). Also changed UDP fallback from `unknown` → `protocol_anomaly` in `src/detection/packet_monitor.py`.

### 14. CBEE Bait Injections never firing
`_get_cbee()` in `app.py` created a `CBEEEngine` instance but never called `.start()`, so the background scoring thread never ran. `_process_active_sessions()` also queried `cowrie_sessions` directly (limited data) instead of the richer `attacker_profiles`. **Fix:** `_get_cbee()` now calls `engine.start()` after creation. `_process_active_sessions()` now queries `attacker_profiles` where `threat_score >= 30`, builds a synthetic session from all accumulated commands, and fires injections when `bias.overall >= 15`.

### 15. Active Deception Environments KPI always 0
`/api/environments` filtered by `{"is_active": True}` but all environments had `is_active: False` after expiry. **Fix:** removed the filter; endpoint now returns all environments + `active_count` (live) and `total` (ever deployed) fields. Dashboard KPI shows `total`.

### 16. IPs Blocked KPI always 0
`get_stats()` counted `response_log` docs with `action: "block_emergency"` but the response engine was never called for existing high-threat profiles — all entries were `log_only`. **Fix:** inserted `block_emergency` entries for all attackers with `threat_score > 90` and `isolate_alert` entries for 70–90. Updated the stats query to count both: `{"action": {"$in": ["block_emergency", "isolate_alert"]}}`.

### 17. SCP malware misclassified as lateral_movement
The `reclassify_intent()` lateral movement rule checked for `scp ` as a substring, which triggered before the SCP-upload-execute pattern could match. **Fix:** moved the SCP upload check (`scp -t` + `chmod`/`bash`) before the general lateral movement rule in `reclassify_intent()`.

### 18. Top commands double-counting via path prefixes
Commands like `/bin/ls`, `./ls`, and `ls` were counted as three separate entries. **Fix:** added `_normCmd()` to `dashboard/static/js/behavior.js` — strips path prefix and leading dots before counting, so all variants merge into one entry.

### 19. Live feed "Waiting for events…" on page load
Feed only populated from WebSocket; fresh page load always showed placeholder until the next live event. **Fix:** `seedFeedFromApi()` in `app.js` fetches `/api/events?limit=200` on init and pre-fills `state.feedItems`, then calls `renderMainFeed()` immediately.

### 20. 502 Bad Gateway after API restart
nginx resolves the `api` upstream hostname at startup. After `docker compose up -d api`, the old upstream entry is stale. **Always run** after any API container restart:
```bash
docker compose exec nginx nginx -s reload
```

---

## Data Pipeline

```
Cowrie JSON log
    → CowrieSessionBuilder (log_pipeline.py)
        → cowrie_sessions (MongoDB)
            → BehaviorEngine (behavior_engine.py)
                → reclassify_intent() + _compute_threat_score()
                    → attacker_profiles (MongoDB)
                        → ResponseEngine → response_log
                        → DeceptionEngine → deception_environments
                        → CBEEEngine → cbee_profiles + cbee_injections

AlertEvent (from Cowrie + Scapy)
    → alert_events (MongoDB)
        → /api/events/stats  →  Dashboard KPIs
        → /api/events        →  Live Feed (seeded on page load + WebSocket)
```

---

## Environment Variables (`.env`)

```
MONGO_USER=admin
MONGO_PASS=<strong password>
MONGO_URI=mongodb://admin:<pass>@mongodb:27017/neurotrap?authSource=admin
SECRET_KEY=<random>
JWT_SECRET=<random>
ADMIN_USER=admin
ADMIN_PASS=<strong password>
ANALYST_USER=analyst
ANALYST_PASS=<strong password>
# MFA_ENABLED=1         ← uncomment to require TOTP on admin login
# MFA_SECRET=<base32>   ← generate with: python -c "import pyotp; print(pyotp.random_base32())"
MONITOR_INTERFACE=eth0
GALAH_PROVIDER=anthropic
GALAH_MODEL=claude-opus-4-8
# ANTHROPIC_API_KEY=   ← uncomment + set to enable Galah + LLM SOC reports
# OPENAI_API_KEY=      ← alternative for Galah with GALAH_PROVIDER=openai
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

# Rebuild + restart API (always reload nginx after)
docker compose build api && docker compose up -d api
docker compose exec nginx nginx -s reload

# Force recalculate all attacker profiles + scores
curl -X POST http://localhost:5000/api/profiles/recalculate

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

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/auth/login` | — | JWT login; `otp` field required when MFA active |
| `GET /api/auth/mfa/status` | — | MFA enabled/configured flags |
| `GET /api/auth/otp/setup` | admin | New TOTP secret + provisioning URI + QR |
| `POST /api/auth/otp/verify` | — | Pre-check a TOTP code |
| `GET /api/events` | — | Alert events; filters: attack_type, severity; pagination: limit, offset |
| `GET /api/events/stats` | — | Total events, active sessions, blocked IPs (block_emergency + isolate_alert), by attack type |
| `GET /api/attackers` | — | Top attacker profiles by threat score |
| `GET /api/attackers/<src_ip>` | — | Single attacker profile |
| `POST /api/profiles/recalculate` | admin | Re-run reclassify_intent + threat score for all profiles |
| `POST /api/response/block` | admin | Manual IP block via iptables |
| `GET /api/response/log` | — | Last 100 response actions |
| `GET /api/environments` | — | All deception environments; includes `total` and `active_count` |
| `GET /api/honeypots` | — | Sensor hit counts and recent sessions |
| `GET /api/honeypots/sessions/<src_ip>` | — | All sessions + events + commands for one IP |
| `GET /api/intel` | — | IOC list, top countries/ports, attack type distribution, campaigns |
| `GET /api/cbee/profiles` | — | Cognitive bias profiles per attacker |
| `GET /api/cbee/injections` | — | Bait injection log |
| `POST /api/cbee/score` | admin | Ad-hoc session bias scoring |
| `GET /api/gadcf/assets` | — | Recent generated deception assets |
| `POST /api/gadcf/generate` | admin | Trigger content generation |
| `GET /api/fhim/nodes` | — | Federated node status + global F1 |
| `GET /api/fhim/rounds` | — | Aggregation round history |
| `GET /api/twin/list` | — | All attacker digital twins |
| `GET /api/twin/<src_ip>` | — | Single twin detail |
| `POST /api/twin/build` | admin | Build/refresh twin(s) |
| `POST /api/twin/simulate` | admin | N-step forward simulation |
| `GET /api/soc/summary` | — | AI SOC analyst shift summary |
| `GET /api/soc/triage` | — | Ranked action queue |
| `GET /api/soc/reports` | — | Recent SOC incident reports |
| `POST /api/soc/report` | admin | Generate incident report for one IP |
| `POST /api/soc/chat` | admin | Analyst Q&A |

---

## Security Notes

- Real SSH is on port **50402** — never change this without updating UFW
- Cowrie owns port 22 on the host — do not run anything else there
- MongoDB is not exposed to the internet — only reachable via Docker networks + `monitor-bridge` (172.25.0.0/24)
- `PermitRootLogin yes` in sshd_config — should be changed to `prohibit-password`
- `fail2ban` is not installed — consider installing for brute-force protection on port 50402
