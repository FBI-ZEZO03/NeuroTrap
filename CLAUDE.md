# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Layout

```
/home/neurotrap/
├── neurotrap/                  # Main Python application
│   ├── src/                    # All Python source modules (see Module Map below)
│   ├── tests/                  # pytest test suite (9 test files + conftest.py)
│   ├── dashboard/
│   │   ├── templates/          # Jinja2 HTML — index.html is the SPA; cbee/gadcf/fhim.html are legacy redirects
│   │   └── static/             # JS/CSS per section: app.js, dashboard.js, behavior.js, cbee.js,
│   │                           #   gadcf.js, fhim.js, intel.js, soc.js, twin.js + CSS files
│   ├── config/                 # Per-service config files (cowrie.cfg, userdb.txt,
│   │                           #   opencanary.conf, galah/config.yaml, nginx/nginx.conf)
│   │                           #   NOTE: dionaea.cfg is present but Dionaea is disabled (see Docker section)
│   ├── docker/                 # Dockerfile.api / .monitor / .behavior / .deception / .honeypots / .opencanary
│   ├── docker-compose.yml
│   ├── data/models/            # Pre-trained classifier.joblib, scaler.joblib, label_encoder.joblib
│   ├── requirements/           # Per-service pip files: api.txt, behavior.txt, honeypots.txt, monitor.txt, deception.txt
│   ├── scripts/                # generate_ssl_cert.sh, setup_db_indexes.py, simulate_attack.py
│   └── docs/architecture.md
└── neurotrap-db/               # MongoDB schema artifact repo (Mongoose / mongosh only — no Python)
    ├── schemas/                # *.schema.json — MongoDB $jsonSchema validators (28 collections)
    ├── models/                 # *.model.js — Mongoose model definitions
    ├── samples/                # *.sample.json — realistic sample documents
    ├── docs/                   # 12 markdown architecture/ops docs
    └── scripts/
        ├── init_db.js          # mongosh init: creates every collection with validator + indexes
        └── validate_samples.py # Python script to validate sample documents against schemas
```

---

## Commands

### Full stack (Docker — Ubuntu 22.04/24.04)

```bash
cd neurotrap
cp .env.example .env                    # fill MONGO_USER, MONGO_PASS, SECRET_KEY, JWT_SECRET, MONITOR_INTERFACE
bash scripts/generate_ssl_cert.sh
docker compose up -d
docker compose exec api python scripts/setup_db_indexes.py
docker compose exec behavior-engine python -m src.behavior.train_classifier
# Dashboard: https://localhost (accept self-signed cert)
```

### Local development (no Docker — SQLite fallback, no infrastructure)

```bash
cd neurotrap
pip install -r requirements/api.txt
NEUROTRAP_FORCE_FALLBACK=1 python -m src.api.app       # API on :5000, SQLite at data/neurotrap.db
```

### Native Python honeypots (no Docker — SSH:2222, HTTP:8081, FTP:2121, Telnet:2323)

```bash
pip install -r requirements/honeypots.txt
python -m src.honeypots.main
# Or opt-in Docker profile:
docker compose --profile native-honeypots up
```

### Tests

```bash
cd neurotrap
pip install pytest faker scikit-learn spacy
python -m pytest tests/ -v
python -m pytest tests/test_classifier.py -v           # single file
python -m pytest tests/test_twin.py::test_prediction -v  # single test
```

CI runs `pytest tests/ -v --tb=short --cov=src` + `ruff check src/ tests/ --ignore E501` on Python 3.11 (`.github/workflows/ci.yml`).

### Train the ML classifier

```bash
# In Docker:
docker compose exec behavior-engine python -m src.behavior.train_classifier
# Locally (pre-trained models already in data/models/):
python -m src.behavior.train_classifier
```

### E2E attack simulation

```bash
python scripts/simulate_attack.py   # 5-stage: recon → brute-force → login+commands → malware upload → lateral movement
```

### Init MongoDB schema (neurotrap-db)

```bash
cd neurotrap-db
mongosh "mongodb://localhost:27017/neurotrap" scripts/init_db.js
```

---

## Architecture — Data Flow (10 layers)

```
Internet ──► Honeypots (Layer 1)
              ↓  JSON logs / packets
         Detection Pipeline (Layer 2)  →  alert_events (MongoDB)
              ↓  AlertEvent stream
         Behavior Analysis (Layer 3)   →  attacker_profiles
              ↓  AttackerProfile
         Deception Engine (Layer 4)    →  deception_environments
              ↓  (parallel enrichment)
         CBEE Bias Scoring (Layer 5)   →  cbee_profiles, cbee_injections
         GADCF Content Gen (Layer 6)   →  gadcf_assets
         Attacker Digital Twin (Layer 7) → attacker_twins
         FHIM Federated Intel (Layer 8)
              ↓  threat_score / response decision
         Response Engine (Layer 9)     →  response_log
              ↓
         Flask API + WebSocket (Layer 10) → Dashboard SPA
```

> **Note:** ASHRTA (Autonomous Self-Hardening Red-Team Adversarial) was planned as Layer 9 but is **not implemented** — `src/ashrta/` does not exist in the codebase and `/api/ashrta/run` is not wired up.

---

## Module Map (`src/`)

### `src/detection/`
- **`alert_schema.py`** — `AlertEvent` dataclass: `src_ip, dst_port, attack_type, honeypot_source, severity, command, raw_payload` plus optional `src_port, session_id, username, password`. Factory methods `from_cowrie()` and `from_zeek()` normalize external log formats. `ATTACK_TYPES` and `SEVERITY_LEVELS` tuples enforce valid values.
- **`packet_monitor.py`** — `PacketMonitor` (Scapy): detects port scans (>10 unique ports/5 s), brute-force (>5 fails/min), protocol anomalies, tool fingerprints. Writes `AlertEvent` to DB.
- **`log_pipeline.py`** — `LogIngestionPipeline`: background threads tail Cowrie/Dionaea JSON log files and emit `AlertEvent` objects to `alert_events`. Also contains `CowrieSessionBuilder`: aggregates per-session Cowrie events and writes complete session docs to `cowrie_sessions` on `cowrie.session.closed`.
- **`main.py`** — starts both `PacketMonitor` and `LogIngestionPipeline` as threads.

### `src/behavior/`
- **`classifier.py`** — `SessionFeatureExtractor`: converts a Cowrie session dict → 13-dim numeric vector (total_commands, unique_commands, dangerous_count, recon_count, download_attempts, file_access, session_duration, login_attempts, failed_logins, has_persistence, has_lateral, and two ratio features). `AttackerClassifier`: `VotingClassifier(RF + SVM)` with 6 intent classes (`reconnaissance`, `credential_harvesting`, `malware_deployment`, `lateral_movement`, `cryptomining`, `bot_enrollment`) and 3 tiers (`beginner`, `automated_bot`, `advanced_human`). F1 macro > 0.85 target. Pre-trained models saved to `data/models/`.
- **`behavior_engine.py`** — `BehaviorEngine`: background polling loop that reads unprocessed `cowrie_sessions`, calls `AttackerClassifier.load()` + `TTPExtractor`, and writes enriched `AttackerProfile` records to `attacker_profiles`.
- **`ttp_extractor.py`** — `TTPExtractor`: 50+ rule-based patterns + spaCy/sentence-transformers embedding matching → `(technique_id, tactic, confidence, matched_command)` per command.
- **`attacker_profile.py`** — `AttackerProfile`: per-IP persistent record (src_ip, first_seen, last_seen, session_count, classified_intent, attacker_tier, threat_score 0–100, TTPs list, campaign_id, country, is_blocked, response_action). `ProfileStore`: MongoDB persistence with indexes on `src_ip`, `threat_score`, `last_seen`.
- **`train_classifier.py`** — Trains and saves classifier artifacts to `data/models/`.

### `src/deception/`
- **`deception_engine.py`** — `DeceptionEngine`: per-attacker environment generator. Templates for 3 tiers — `beginner` (Ubuntu, 2 services), `automated_bot` (CentOS, 4 services), `advanced_human` (Debian, 6 services + Docker). Tries to spawn a real Cowrie container; falls back to mock. Auto-GC: evicts stale envs after 1 hour; max 20 active. Customizes hostname/services based on detected TTPs.
- **`credential_generator.py`** — `CredentialGenerator`: Faker-seeded per attacker IP. Generates SSH users, AWS keys, DB creds, `.env` files, `/etc/shadow` hashes, fake shell history.
- **`main.py`** — entry point: polls `attacker_profiles` (top 5 by threat_score), spawns environments for any profile with `threat_score >= 10` and `is_blocked == False`. Calls `ResponseEngine.evaluate()` for each. Poll interval: 10 s.

### `src/db/`
- **`database.py`** — `get_db()` / `get_collection()`: sole data access entry points. Tries MongoDB (`MONGO_URI`); falls back to embedded SQLite. `reset()` drops the cached handle (for tests). `backend()` returns `"mongodb"` or `"sqlite-fallback"`.
- **`fallback_store.py`** — `FallbackDB`: SQLite-backed document store. One table per collection (`_id TEXT PRIMARY KEY, doc TEXT JSON`). Supports `find`, `find_one`, `update_one` (with `$set`, `$inc`, `$push`, upsert), `count_documents`, `aggregate` (`$match`, `$group`, `$sort`, `$limit`, `$skip`, `$project`, `$switch`). Cursor chaining: `sort()`, `skip()`, `limit()`. Thread-safe (`RLock`). Set `NEUROTRAP_FORCE_FALLBACK=1` to skip Mongo entirely.

### `src/honeypots/`
- **`base.py`** — `BaseHoneypot`: threaded TCP server base class. `HoneypotSession` dataclass tracks credentials, commands, events per connection. `record_event()` normalizes interactions into `AlertEvent` and persists to `alert_events`; sessions persist to `honeypot_sessions`. `recv_line()` helper for line-oriented protocols.
- **`ssh_honeypot.py`** — paramiko-based SSH server. Full credential capture when paramiko available; banner-only mode otherwise.
- **`http_honeypot.py`**, **`ftp_honeypot.py`**, **`telnet_honeypot.py`** — self-contained sensors extending `BaseHoneypot`; write `AlertEvent` to DB.
- **`manager.py`** — starts and supervises all four honeypot servers as threads.
- **`main.py`** — entry point; reads `HONEYPOTS_ENABLED` env var.

### `src/cbee/` — Cognitive Bias Exploitation Engine
- **`bias_scorer.py`** — `BiasScorer`: scores sessions on 5 dimensions (each 0–100):
  - `curiosity_gap`: grep/find/cat on `.key/.env/.secret` files
  - `confirmation_bias`: early recon commands confirming attacker assumptions
  - `sunk_cost`: wget/curl/apt (time invested + downloads)
  - `authority_signal`: sudo/chmod 4xxx/shadow (privilege escalation)
  - `scarcity_framing`: crontab/nohup/high login_attempts (persistence + urgency)
  - `BiasProfile.overall` = mean of 5 dimensions; `BiasProfile.dominant` = argmax.
- **`cbee_engine.py`** — `CBEEEngine`: re-scores active sessions; fires bait injection when `overall >= 25` and fewer than 3 injections already sent for that IP.
- **`bait_injector.py`** — `BaitInjector`: generates personalized assets (files, creds, documents) keyed to the dominant bias dimension.

### `src/gadcf/` — Generative Adaptive Deception Content Factory
- **`content_generator.py`** — `ContentGenerator`: Ollama Mistral LLM (falls back to templates). Produces per-industry fake assets: `.env` files (AWS/DB/Stripe creds), email threads (credential rotation narratives), Flask code repos (hardcoded fallback creds), wiki runbooks (server IPs, SSH keys, service accounts), SQL dumps (hashed passwords).
- **`gadcf_engine.py`** — `GADCFEngine`: maps attacker intent → target industry; orchestrates generation and stores to `gadcf_assets`.

### `src/twin/` — Attacker Digital Twin
- **`digital_twin.py`** — `DigitalTwin` dataclass: identity (src_ip, countries, tools, honeypots_touched), capability (tier, sophistication 0–100, automation_score 0–100), intent, fingerprint (MITRE technique_ids, tactics_observed, tactic_sequence), synthesis (kill_chain, psychology from CBEE, predicted_next, recommendation), quality (fidelity, confidence, predictions_hit/made). `AttackerDigitalTwin`: builds twins from `alert_events` + `attacker_profiles` + `cbee_profiles`; persists to `attacker_twins`. `_automation_score()` uses inter-event timing + known bot tool signatures.
- **`predictor.py`** — `TacticPredictor`: Markov chain over 14 MITRE tactics. Hand-crafted prior transition matrix; blends 40% learned from observed sequences + 60% prior. `predict_next()` → top-3 tactics with probabilities. `simulate_forward(N, seed)` → deterministic N-step forward path.
- **`kill_chain.py`** — `build_kill_chain()`: maps MITRE tactics → 7-stage Lockheed Martin Kill Chain (Recon → Weaponization → Delivery → Exploitation → Installation → C&C → Actions on Objectives). `tactic_for_attack_type()` maps `AlertEvent.attack_type` strings to MITRE tactic names.
- **`main.py`** — entry point for the twin container.

### `src/fhim/` — Federated Honeypot Intelligence Mesh
- **`federated_node.py`** — `FederatedNode`: trains locally (RF + SVM); applies differential privacy (Gaussian noise, epsilon-delta); transmits noisy delta to server.
- **`aggregation_server.py`** — `FedAvgServer`: collects deltas from ≥ 2 nodes; averages weights via numpy; returns updated global model. Pre-seeded with 4 demo orgs (Cairo Uni, Acme Financial, Fraunhofer FKIE, SaudiTelecom). `NodeStatus` and `AggregationRound` dataclasses track federation state.

### `src/soc_analyst/`
- **`soc_analyst.py`** — `SOCAnalyst`: triage queue (ranks active IPs by threat_score with risk band + recommended action), per-attacker incident report (`generate_report()`), analyst Q&A (`answer_question()`), shift summary (`summary()`). Works offline with heuristic text or with `ANTHROPIC_API_KEY` for LLM output. Demo triage data ensures non-empty UI with no DB.
- **`llm_client.py`** — thin wrapper over Anthropic API (Claude). Falls back to heuristic text when key absent.
- Risk bands: < 40 = low/monitor · 40–70 = elevated/slow · 70–90 = high/isolate · ≥ 90 = critical/block

### `src/response/`
- **`response_engine.py`** — `ResponseEngine`: decision matrix on `threat_score`:
  - < 40: `log_only`
  - 40–70: `slow_redirect` — `tc netem` rate-limiting
  - 70–90: `isolate_alert` — iptables + log rule + alert
  - ≥ 90: `block_emergency` — iptables DROP + SMTP/Slack/Telegram alert + tcpdump PCAP (10 K-packet cap)
  - All network ops fail gracefully when iptables/tc unavailable (mock mode).

### `src/api/app.py`
Flask + Flask-SocketIO. All innovation engines are lazy-loaded by `_get_<name>()` singletons that return `None` on import failure and serve built-in demo data instead. A 30-second in-memory response cache (`@cached(key)`) is applied to expensive read endpoints; cache keys include the query string so different `limit`/`filter` params get separate entries.

**Auth**: Two built-in user roles — `admin` (full access) and `analyst` (read-only). JWT issued by `flask-jwt-extended`. Optional MFA/TOTP via `pyotp` — enabled by `MFA_ENABLED=1` + `MFA_SECRET=<base32>` (admin-only).

**Background threads**: `_live_feed_poller()` polls `alert_events` and `attacker_profiles` every 2 s and pushes new documents to connected WebSocket clients. Geo-resolution (`_resolve_geo()`) runs in a daemon thread when profiles lack lat/lon, calling the ip-api.com batch endpoint and updating `attacker_profiles` in-place.

**Key REST endpoints:**

| Route | Method | Auth | Notes |
|-------|--------|------|-------|
| `/api/auth/login` | POST | — | Returns JWT; `otp` field required when `MFA_ENABLED=1` |
| `/api/auth/mfa/status` | GET | — | Returns `mfa_enabled`, `mfa_configured` flags |
| `/api/auth/otp/setup` | GET | admin | Returns new TOTP secret + provisioning URI + QR PNG (base64) |
| `/api/auth/otp/verify` | POST | — | Pre-check a TOTP code without full login |
| `/api/events` | GET | — | Query `alert_events`; filters: `attack_type`, `severity`; pagination: `limit`, `offset` |
| `/api/events/stats` | GET | — | Aggregation: total events, active sessions (last hour), blocked IPs, by-type breakdown |
| `/api/attackers` | GET | — | Top profiles by `threat_score` DESC; `sessions=1` to include session list; `avg_confidence` computed |
| `/api/attackers/<src_ip>` | GET | — | Single profile |
| `/api/response/block` | POST | admin | Manual iptables block; logs to `response_log` |
| `/api/response/log` | GET | — | Last 100 response actions |
| `/api/environments` | GET | — | Active deception environments |
| `/api/honeypots` | GET | — | Per-sensor hit counts + unique attacker IPs + recent Cowrie sessions |
| `/api/honeypots/sessions/<src_ip>` | GET | — | All sessions + events + command history for one IP |
| `/api/intel` | GET | — | IOC list, top countries, top ports, attack type distribution, active campaigns |
| `/api/cbee/profiles` | GET | — | Bias profiles (top 50); auto-scores from attacker_profiles when empty |
| `/api/cbee/injections` | GET | — | Last 20 bait injection records |
| `/api/cbee/score` | POST | admin | Ad-hoc session scoring |
| `/api/gadcf/assets` | GET | — | Recent generated deception assets |
| `/api/gadcf/generate` | POST | admin | Trigger content generation (industry, intent, sophistication) |
| `/api/fhim/nodes` | GET | — | Federated node status + global F1 score |
| `/api/fhim/rounds` | GET | — | Aggregation round history |
| `/api/twin/list` | GET | — | All digital twins sorted by threat_score |
| `/api/twin/<src_ip>` | GET | — | Single twin detail |
| `/api/twin/build` | POST | admin | Build/refresh twin(s); `src_ip` for one, omit for all |
| `/api/twin/simulate` | POST | admin | N-step forward simulation (live twin or ad-hoc `tactics` list) |
| `/api/soc/summary` | GET | — | Shift summary (window settable via `?hours=`) |
| `/api/soc/triage` | GET | — | Ranked action queue |
| `/api/soc/reports` | GET | — | Recent SOC incident reports (metadata only, no `report_md`) |
| `/api/soc/report` | POST | admin | Generate LLM incident report for one IP |
| `/api/soc/chat` | POST | admin | Analyst Q&A |

WebSocket events: `connect` → `"connected"`, `subscribe_events` → `"subscribed"`, server pushes `new_event` and `profile_update`.

---

## Database Layer

`get_db()` (in `src/db/database.py`) is the only entry point — never import pymongo directly in modules. Returns either a live MongoDB `neurotrap` database or a `FallbackDB` wrapping SQLite. The interface is identical to pymongo's `Database` for all operations used in this codebase.

**Active collections** (Python app):
`alert_events`, `honeypot_sessions`, `cowrie_sessions`, `attacker_profiles`, `attacker_twins`, `cbee_profiles`, `cbee_injections`, `gadcf_assets`, `fhim_rounds`, `fhim_aggregation_rounds`, `deception_environments`, `response_log`, `soc_reports`

**Full schema set** (neurotrap-db — 28 collections across 14 domains):
User Management (users, roles, permissions, login_history, analyst_profiles) · Attack Sessions · Threat Actors · Threat Intel · MITRE Mappings · Response Actions · Alerts · Reports · Digital Twins · Deception Engine (11 collections) · Deception Effectiveness · AI SOC Analyst Outputs · AI Insights · Attack Campaigns.

**Schema conventions** (neurotrap-db):
- `snake_case` field names; `ObjectId` `_id`; human-readable business key as a separate unique-indexed field
- `created_at` / `updated_at` (ISODate UTC)
- Scores 0–100 (`threat_score`, `risk_score`, etc.); confidence 0–1
- `additionalProperties: false` on top-level objects (unless noted)
- Embed bounded/owned sub-documents; reference shared/large data by ObjectId

---

## Docker Services

| Service | Image / Dockerfile | Ports | Notes |
|---------|-------------------|-------|-------|
| `cowrie` | `cowrie/cowrie:latest` | 22→2222, 23→2223 | SSH/Telnet emulator; logs at `/cowrie/cowrie-git/var/log/cowrie/` |
| `opencanary` | `Dockerfile.opencanary` | 21, 80, 445, 3306, 1433, 161/udp, 5900, 3389 | Multi-service honeypot; **also handles FTP/HTTP/SMB/MySQL** (Dionaea's former ports) |
| `galah` | `0x4d31/galah:latest` | 8088→8080 | LLM web honeypot; disabled without `ANTHROPIC_API_KEY` |
| `honeypots` | `Dockerfile.honeypots` | 2222, 2323, 2121, 8081 | Native Python — opt-in profile `native-honeypots` |
| `mongodb` | `mongo:6.0` | 27017 (internal) | Static IP `172.25.0.10` on `monitor-bridge` network |
| `packet-monitor` | `Dockerfile.monitor` | host network | Scapy; needs `NET_ADMIN`+`NET_RAW` caps; uses `MONGO_URI` via `172.25.0.10` |
| `behavior-engine` | `Dockerfile.behavior` | — | Polling loop; reads `cowrie_sessions`, writes `attacker_profiles` |
| `deception-engine` | `Dockerfile.deception` | — | Needs `/var/run/docker.sock`; threshold `threat_score >= 10` |
| `api` | `Dockerfile.api` | 5000 (internal) | Flask + SocketIO; also on `monitor-bridge` for MongoDB access |
| `nginx` | `nginx:alpine` | 443, 8080→80 | SSL termination |

> **Dionaea is disabled**: `dinotools/dionaea:latest` crashes (SIGTRAP) on kernel 6.8 due to `libemu`. The service is commented out in `docker-compose.yml`. Its ports (21/80/445/3306) are now covered by OpenCanary.

**Networks:**
- `honeypot-net` (172.20.0.0/24) — internet-facing; cowrie, opencanary, galah, nginx
- `elk-net` (internal) — honeypots ↔ backends
- `management-net` (internal) — backends ↔ API ↔ Nginx
- `monitor-bridge` (172.25.0.0/24) — non-internal bridge so `packet-monitor` (host network mode) can reach MongoDB at `172.25.0.10`

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONGO_URI` | `mongodb://localhost:27017/neurotrap` | MongoDB connection string |
| `MONGO_USER` | `admin` | MongoDB root username |
| `MONGO_PASS` | `neurotrap_secret` | MongoDB root password |
| `MONGO_TIMEOUT_MS` | `1000` | Mongo ping timeout before SQLite fallback |
| `SECRET_KEY` | `change_me_in_production` | Flask session secret |
| `JWT_SECRET` | `change_me_jwt` | JWT signing secret |
| `ADMIN_USER` / `ADMIN_PASS` | `admin` / `neurotrap2024` | Admin role credentials |
| `ANALYST_USER` / `ANALYST_PASS` | `analyst` / `analyst2024` | Read-only analyst role credentials |
| `MFA_ENABLED` | `0` | `1` = require TOTP on admin login |
| `MFA_SECRET` | unset | Base32 TOTP secret; generate with `python -c "import pyotp; print(pyotp.random_base32())"` |
| `MONITOR_INTERFACE` | `eth0` | NIC for Scapy packet capture |
| `NEUROTRAP_FORCE_FALLBACK` | unset | `1` = always use SQLite, skip Mongo |
| `NEUROTRAP_DB_PATH` | `data/neurotrap.db` | SQLite file path |
| `ANTHROPIC_API_KEY` | unset | Enables LLM features (Galah web honeypot, SOC Analyst narrative) |
| `OPENAI_API_KEY` | unset | Alternative LLM provider for Galah |
| `GALAH_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `GALAH_MODEL` | `claude-opus-4-8` | LLM model for Galah |
| `HONEYPOTS_ENABLED` | `ssh,http,ftp,telnet` | Which native sensors to start |

---

## Testing

All tests live in `neurotrap/tests/`. `conftest.py` adds the project root to `sys.path` (no `pip install -e` needed). Tests use in-process mocks or the `FallbackDB` SQLite store — no live MongoDB or Docker required.

| Test file | Covers |
|-----------|--------|
| `test_alert_schema.py` | `AlertEvent` validation, `from_cowrie()`, `from_zeek()` |
| `test_classifier.py` | `SessionFeatureExtractor`, training, prediction, tier classification |
| `test_ttp_extractor.py` | Command → MITRE mapping, confidence scoring |
| `test_deception_engine.py` | Environment generation, personalization, Docker mock |
| `test_credential_generator.py` | SSH users, AWS/DB creds, `.env`, shadow, history |
| `test_response_engine.py` | Threshold evaluation, action execution, alerting |
| `test_database.py` | `FallbackDB` vs Mongo interface equivalence |
| `test_honeypots.py` | SSH/HTTP/FTP/Telnet mock servers |
| `test_twin.py` | Twin building, tactic prediction, simulation |

---

## Key Performance Targets

| Metric | Target |
|--------|--------|
| Classifier F1 (macro, 6-class intent) | > 0.85 |
| Event → Dashboard latency | < 5 s |
| Honeypot environment spawn time | < 30 s |
| Response action time after threshold breach | < 10 s |
| Lynis hardening score | > 70 |
