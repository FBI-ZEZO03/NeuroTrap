# Attacker Digital Twin

The Attacker Digital Twin (ADT) module builds a rich behavioral model of each threat actor — a persistent, evolving representation that tracks not just what an attacker did, but who they are, how capable they are, what they're likely to do next, and where they sit in the kill chain.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `DigitalTwin` | `src/twin/digital_twin.py` | Twin data model + `AttackerDigitalTwin` builder |
| `TacticPredictor` | `src/twin/predictor.py` | Markov-chain next-tactic predictor |
| `KillChainMapper` | `src/twin/kill_chain.py` | MITRE tactics → Lockheed Martin Kill Chain |
| `main.py` | `src/twin/main.py` | Container entry point |

---

## DigitalTwin Data Model

```python
@dataclass
class DigitalTwin:
    # Identity
    src_ip: str
    countries: list[str]
    tools_observed: list[str]
    honeypots_touched: list[str]

    # Capability
    attacker_tier: str          # beginner / automated_bot / advanced_human
    sophistication: float       # 0–100
    automation_score: float     # 0–100

    # Intent
    classified_intent: str
    confidence: float

    # MITRE Fingerprint
    technique_ids: list[str]
    tactics_observed: list[str]
    tactic_sequence: list[str]  # ordered timeline of tactics

    # Synthesis
    kill_chain: dict            # stage → evidence
    psychology: dict            # CBEE bias profile summary
    predicted_next: list[str]   # top-3 predicted next tactics
    recommendation: str         # recommended SOC action

    # Quality metrics
    fidelity: float             # 0–100, how complete this twin is
    predictions_hit: int
    predictions_made: int
    built_at: float
```

---

## Building a Twin

`AttackerDigitalTwin.build(src_ip)` aggregates data from three sources:

1. **`alert_events`** — all events for the IP: tools used, ports hit, timing patterns
2. **`attacker_profiles`** — ML-classified intent, TTP list, threat score, tier
3. **`cbee_profiles`** — cognitive bias scores, dominant bias dimension

### Automation Score

`_automation_score()` estimates whether the attacker is a human or a bot:

```python
def _automation_score(events: list) -> float:
    # Bots have very consistent inter-event timing
    intervals = [events[i+1].timestamp - events[i].timestamp
                 for i in range(len(events)-1)]
    timing_variance = statistics.variance(intervals) if len(intervals) > 2 else 1000

    # Known bot tool signatures in event data
    tool_hits = sum(1 for e in events if any(sig in (e.raw_payload or "")
                                              for sig in BOT_SIGNATURES))

    # Low variance + tool signatures → high automation score
    return min(100, (1000 / max(timing_variance, 1)) * 50 + tool_hits * 10)
```

High automation score → `automated_bot` tier. Low score + multi-stage attack → `advanced_human`.

---

## Tactic Predictor

`TacticPredictor` (`src/twin/predictor.py`) uses a Markov chain over 14 MITRE tactics to predict what the attacker is likely to do next.

### Transition Model

The predictor blends:
- **40% learned** — transitions observed in the attacker's real tactic sequence
- **60% prior** — hand-crafted prior matrix based on real-world attack chain statistics

```python
def predict_next(self, current_tactic: str) -> list[tuple[str, float]]:
    """Returns top-3 next tactics with probabilities."""
    row = self.blend_matrix[tactic_index(current_tactic)]
    top3 = sorted(enumerate(row), key=lambda x: -x[1])[:3]
    return [(TACTICS[i], p) for i, p in top3]
```

### Forward Simulation

```python
def simulate_forward(self, n_steps: int, seed_tactic: str) -> list[str]:
    """Deterministic N-step forward simulation from a seed tactic."""
    path = [seed_tactic]
    current = seed_tactic
    for _ in range(n_steps - 1):
        next_tactic = self.predict_next(current)[0][0]  # take top prediction
        path.append(next_tactic)
        current = next_tactic
    return path
```

API: `POST /api/twin/simulate` with `{"src_ip": "...", "steps": 5}`.

---

## Kill Chain Mapping

`build_kill_chain()` (`src/twin/kill_chain.py`) maps MITRE tactics to the 7-stage Lockheed Martin Cyber Kill Chain:

| Kill Chain Stage | MITRE Tactics Mapped |
|-----------------|---------------------|
| Reconnaissance | Reconnaissance, Resource Development |
| Weaponization | Execution, Defense Evasion |
| Delivery | Initial Access, Command and Control |
| Exploitation | Privilege Escalation, Lateral Movement |
| Installation | Persistence |
| Command & Control | Command and Control |
| Actions on Objectives | Credential Access, Collection, Exfiltration, Impact |

The current kill chain stage is determined by the latest tactic in the attacker's observed sequence. The dashboard displays:
- Stages completed (solid)
- Current stage (highlighted)
- Predicted next stages (dashed)

---

## Dashboard Integration

The **ADT** (Attacker Digital Twins) section shows:

- **Twin list** — all twins sorted by `threat_score`, with kill chain stage and predicted next moves
- **Twin detail panel** — click any twin for full view: identity, capabilities, MITRE fingerprint, kill chain visualization, forward simulation
- **Forward simulator** — admin can trigger an N-step simulation for any twin (calls `POST /api/twin/simulate`)

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/twin/list` | GET | — | All twins sorted by threat score |
| `/api/twin/<src_ip>` | GET | — | Full detail for one twin |
| `/api/twin/build` | POST | admin | Build/refresh twin(s) |
| `/api/twin/simulate` | POST | admin | N-step forward simulation |

### Build Request

```json
{ "src_ip": "203.0.113.45" }
```

Omit `src_ip` to rebuild all twins.

### Simulate Request

```json
{ "src_ip": "203.0.113.45", "steps": 5 }
```

Or use an ad-hoc tactics list (no twin needed):

```json
{
  "tactics": ["Reconnaissance", "Initial Access", "Execution"],
  "steps": 3
}
```

---

## Verification

```bash
# Build twins for all known attackers
curl -s -X POST http://localhost:5000/api/twin/build \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{}'

# List all twins
curl -s http://localhost:5000/api/twin/list | python3 -m json.tool

# Simulate 5 steps from an attacker's current position
curl -s -X POST http://localhost:5000/api/twin/simulate \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"src_ip": "203.0.113.45", "steps": 5}' | python3 -m json.tool
```
