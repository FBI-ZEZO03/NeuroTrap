# Developer Guide

This guide covers local development setup, code organization, contribution patterns, and common operations.

---

## Local Development Setup

### Option A — SQLite Fallback (fastest, no Docker)

```bash
cd /home/neurotrap/neurotrap
pip install -r requirements/api.txt
NEUROTRAP_FORCE_FALLBACK=1 python -m src.api.app
# API on http://localhost:5000
# SQLite database at data/neurotrap.db
```

The FallbackDB SQLite store implements the same interface as MongoDB for all operations used in the codebase. All API endpoints and dashboard features work in this mode.

### Option B — Docker (full stack)

```bash
cp .env.example .env   # fill required values
bash scripts/generate_ssl_cert.sh
docker compose up -d
# Dashboard at https://localhost (accept self-signed cert)
```

### Native Honeypots (optional supplement)

```bash
pip install -r requirements/honeypots.txt
python -m src.honeypots.main
# SSH :2222  HTTP :8081  FTP :2121  Telnet :2323
```

---

## Project Structure

```
neurotrap/
├── src/                    # All Python source
│   ├── api/app.py          # Flask REST API + WebSocket
│   ├── behavior/           # ML classifier, TTP extractor, profiling
│   ├── cbee/               # Cognitive Bias Exploitation Engine
│   ├── db/                 # Database layer (MongoDB + SQLite fallback)
│   ├── deception/          # Deception environment spawner
│   ├── detection/          # Packet monitor, log pipeline, AlertEvent
│   ├── fhim/               # Federated Honeypot Intelligence Mesh
│   ├── gadcf/              # Generative fake content factory
│   ├── honeypots/          # Native Python sensors
│   ├── response/           # Autonomous response engine
│   ├── soc_analyst/        # AI SOC Analyst
│   └── twin/               # Attacker Digital Twin
├── dashboard/
│   ├── templates/index.html    # SPA HTML template
│   └── static/
│       ├── js/             # app.js, dashboard.js, behavior.js, ...
│       └── css/            # main.css, dashboard.css, ...
├── config/                 # Honeypot configs (cowrie.cfg, opencanary.conf, etc.)
├── docker/                 # Per-service Dockerfiles
├── data/
│   └── models/             # Pre-trained classifier.joblib, scaler.joblib
├── requirements/           # Per-service requirements files
├── scripts/                # setup_db_indexes.py, simulate_attack.py, etc.
├── tests/                  # pytest test suite
└── docs/                   # This documentation
```

---

## Database Layer

The DB layer is in `src/db/`. **Never import `pymongo` directly** in modules — always use `get_db()`:

```python
from src.db.database import get_db

db = get_db()
col = db["alert_events"]
col.insert_one(event.to_dict())
results = list(col.find({"src_ip": "1.2.3.4"}).sort("timestamp", -1).limit(10))
```

### Testing Without MongoDB

Set `NEUROTRAP_FORCE_FALLBACK=1` to always use the SQLite fallback:

```bash
NEUROTRAP_FORCE_FALLBACK=1 python -m pytest tests/ -v
```

### FallbackDB Supported Operations

`FallbackDB` supports the following MongoDB-compatible operations:

| Operation | Notes |
|-----------|-------|
| `find(filter)` | `$gt`, `$lt`, `$gte`, `$lte`, `$ne`, `$in` operators supported |
| `find_one(filter)` | Returns first match or None |
| `insert_one(doc)` | Assigns `_id` if not present |
| `update_one(filter, update, upsert=False)` | `$set`, `$inc`, `$push` operators |
| `count_documents(filter)` | Returns int |
| `aggregate(pipeline)` | `$match`, `$group`, `$sort`, `$limit`, `$skip`, `$project`, `$switch` |
| cursor `.sort(key, direction)` | ASCENDING=1, DESCENDING=-1 |
| cursor `.limit(n)` / `.skip(n)` | Chainable |

---

## API Conventions

### Lazy Module Loading

All innovation engines are loaded lazily in `app.py` via `_get_<name>()` singletons:

```python
_cbee_engine = None

def _get_cbee():
    global _cbee_engine
    if _cbee_engine is None:
        try:
            from src.cbee.cbee_engine import CBEEEngine
            _cbee_engine = CBEEEngine()
            _cbee_engine.start()  # starts background thread
        except Exception:
            return None
    return _cbee_engine
```

If an engine fails to import or start, the singleton returns `None` and the endpoint serves demo/mock data instead of crashing.

### Response Cache

Expensive GET endpoints are cached for 30 seconds using `@cached(key)`:

```python
@app.route('/api/attackers')
def get_attackers():
    key = f"attackers:{request.args.get('limit', 50)}"
    if cached := response_cache.get(key):
        return jsonify(cached)
    data = ...  # expensive DB query
    response_cache[key] = data
    return jsonify(data)
```

Cache keys include query string parameters, so `?limit=50` and `?limit=100` get separate entries.

### Auth Pattern

```python
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/api/some-admin-endpoint', methods=['POST'])
@jwt_required()
def admin_action():
    claims = get_jwt_identity()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    ...
```

---

## Adding a New API Endpoint

1. Add the route to `src/api/app.py`
2. Follow existing patterns: lazy engine loading, response cache for GETs, JWT check for writes
3. Add a test in `tests/`
4. Update `docs/api-reference.md`

## Adding a New Module

1. Create `src/<module>/` with `__init__.py`
2. Implement the engine class; provide a `start()` method if it runs a background thread
3. Add a lazy loader `_get_<module>()` in `app.py`
4. Add API endpoints
5. Add dashboard section: JS file in `dashboard/static/js/`, section div in `index.html`
6. Write tests in `tests/test_<module>.py`
7. Add documentation in `docs/`

---

## Rebuilding the ML Classifier

After capturing enough real Cowrie sessions (recommend ≥ 200 labeled sessions):

```bash
# In Docker
docker compose exec behavior-engine python -m src.behavior.train_classifier

# Locally
python -m src.behavior.train_classifier
```

This saves updated models to `data/models/` which are used by the running behavior engine (it reloads on next poll cycle).

---

## Common Development Commands

```bash
# Tail API logs (Flask requests)
docker logs -f neurotrap-api

# Tail behavior engine (classification events)
docker logs -f neurotrap-behavior

# Reset all data (keep config, delete events/profiles)
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "['alert_events','attacker_profiles','cowrie_sessions','attacker_twins',
           'response_log','deception_environments'].forEach(c=>db[c].deleteMany({}))"

# Force profile recalculation
curl -s -X POST http://localhost:5000/api/profiles/recalculate

# Check DB collection sizes
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.getCollectionNames().forEach(c=>print(c+': '+db[c].countDocuments()))"

# After any API restart, reload nginx
docker compose exec nginx nginx -s reload
```

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONGO_URI` | `mongodb://localhost:27017/neurotrap` | MongoDB connection |
| `MONGO_USER` / `MONGO_PASS` | `admin` / `neurotrap_secret` | MongoDB credentials |
| `MONGO_TIMEOUT_MS` | `1000` | Ping timeout before SQLite fallback |
| `SECRET_KEY` | `change_me` | Flask session secret |
| `JWT_SECRET` | `change_me_jwt` | JWT signing key |
| `ADMIN_USER` / `ADMIN_PASS` | `admin` / `neurotrap2024` | Admin credentials |
| `ANALYST_USER` / `ANALYST_PASS` | `analyst` / `analyst2024` | Analyst credentials |
| `MFA_ENABLED` | `0` | `1` = require TOTP on admin login |
| `MFA_SECRET` | unset | Base32 TOTP secret |
| `MONITOR_INTERFACE` | `eth0` | NIC for Scapy capture |
| `NEUROTRAP_FORCE_FALLBACK` | unset | `1` = always use SQLite |
| `NEUROTRAP_DB_PATH` | `data/neurotrap.db` | SQLite path |
| `ANTHROPIC_API_KEY` | unset | Enables Galah + LLM SOC reports |
| `OPENAI_API_KEY` | unset | Alternative LLM for Galah |
| `GALAH_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `GALAH_MODEL` | `claude-opus-4-8` | LLM model ID |
| `HONEYPOTS_ENABLED` | `ssh,http,ftp,telnet` | Which native sensors to start |

---

## Linting

```bash
ruff check src/ tests/ --ignore E501
```

CI enforces this on every push.
