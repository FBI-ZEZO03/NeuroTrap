# NeuroTrap CADN — System Architecture

## Overview

NeuroTrap CADN (Cognitive Adaptive Deception Network) is a five-layer active defense platform. Attackers interact with honeypots, their behavior is classified by ML, personalized deception environments are generated, and the system autonomously responds — all surfaced through a real-time SOC dashboard.

---

## System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 — Capture                                              │
│  Cowrie (SSH/Telnet) · OpenCanary (FTP/HTTP/SMB/RDP/MySQL/SNMP) │
│  Scapy PacketMonitor (raw packets) · Galah (LLM web, optional)  │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON logs + raw packets
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 2 — Detection                                            │
│  LogIngestionPipeline · CowrieSessionBuilder · PacketMonitor    │
│  → Normalizes all sources into AlertEvent schema                 │
│  → Writes to MongoDB: alert_events, cowrie_sessions              │
└────────────────────────────┬────────────────────────────────────┘
                             │ AlertEvent stream + cowrie_sessions
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 3 — Behavior Analysis                                    │
│  AttackerClassifier (RF+SVM ensemble)                           │
│  TTPExtractor (MITRE ATT&CK rule + embedding matching)          │
│  AttackerProfile (per-IP persistent aggregation)                 │
│  reclassify_intent() · _compute_threat_score()                  │
│  → Writes to: attacker_profiles                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ AttackerProfile (enriched)
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 4 — Deception & CBEE                                     │
│  DeceptionEngine → personalized Cowrie environments             │
│  CBEEEngine → cognitive bias scoring → bait injection           │
│  → Writes to: deception_environments, cbee_profiles,            │
│               cbee_injections                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ threat_score threshold
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 5 — Response & Visualization                             │
│  ResponseEngine (log / slow / isolate / block)                   │
│  Flask REST API + SocketIO WebSocket                             │
│  Real-time dashboard: KPIs, live feed, geo map, MITRE heatmap   │
│  → Writes to: response_log                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Docker Network Topology

```
Internet
  │
  ├── :22/:23     ──► neurotrap-cowrie   (SSH/Telnet honeypot)
  ├── :21/:80/:445/:1433/:3306/:3389/:5900/:161/udp
  │               ──► neurotrap-opencanary
  ├── :443/:8080  ──► neurotrap-nginx ──► neurotrap-api:5000
  └── :8088       ──► neurotrap-galah (disabled, requires API key)

Docker networks:
  honeypot-net (172.20.0.0/24) — external bridge
    cowrie, opencanary, galah, nginx, api

  elk-net (internal bridge)
    mongodb, behavior-engine, deception-engine

  management-net (internal bridge)
    mongodb, api

  monitor-bridge (172.25.0.0/24) — external bridge
    mongodb (static 172.25.0.10)
    ← neurotrap-monitor (host network, raw packet capture)
```

MongoDB is not exposed to the internet. It is reachable only via Docker internal networks and via `monitor-bridge` at `172.25.0.10` for the host-network packet monitor.

---

## Data Flow: Cowrie Session → Dashboard

```
1. Attacker connects via SSH
2. Cowrie logs events to cowrie.json (JSONL)
3. LogTailer (log_pipeline.py) reads new lines
4. AlertEvent.from_cowrie() normalizes the event
     └─► alert_events (MongoDB) ── WebSocket ──► Live Feed
4b. CowrieSessionBuilder aggregates on cowrie.session.closed
     └─► cowrie_sessions (MongoDB)
5. BehaviorEngine._run_loop() picks up new sessions
     └─► AttackerClassifier.predict() → intent + confidence
     └─► TTPExtractor.extract() → MITRE TTPs
     └─► AttackerProfile.update() → reclassify_intent() + threat_score
         └─► attacker_profiles (MongoDB)
6. DeceptionEngine checks threat_score >= 10
     └─► spawns personalized Docker Cowrie env
         └─► deception_environments (MongoDB)
7. CBEEEngine (every 30s) scores bias dimensions
     └─► fires bait injection if bias.overall >= 15
         └─► cbee_injections (MongoDB)
8. ResponseEngine.evaluate()
     ├─ score > 90  → block_emergency (iptables DROP)
     ├─ score 70-90 → isolate_alert
     ├─ score 40-70 → slow_redirect (tc netem)
     └─ score < 40  → log_only
         └─► response_log (MongoDB)
9. Flask SocketIO emits new_event → dashboard updates in ≤5s
```

---

## Component Responsibilities

### `src/detection/`

| File | Role |
|------|------|
| `alert_schema.py` | `AlertEvent` dataclass; `from_cowrie()` maps all Cowrie event IDs to attack types; `_COWRIE_SKIP` filters metadata-only events |
| `log_pipeline.py` | `LogIngestionPipeline` — tails Cowrie JSON; `CowrieSessionBuilder` — aggregates per-session docs |
| `packet_monitor.py` | Scapy-based raw packet capture; TCP SYN → `port_scan`, UDP → `protocol_anomaly` |

### `src/behavior/`

| File | Role |
|------|------|
| `classifier.py` | RF+SVM ensemble classifier; `extract()` builds feature vector from session; `_base_cmd()` strips path prefixes |
| `behavior_engine.py` | `BehaviorEngine` run loop; `_rule_based_classify()` fallback classifier |
| `attacker_profile.py` | `AttackerProfile` per-IP aggregation; `reclassify_intent()` examines all accumulated commands; `_compute_threat_score()` tiered formula; `recalculate_all()` |
| `ttp_extractor.py` | MITRE ATT&CK tactic/technique mapping from commands + session features |

### `src/deception/`

| File | Role |
|------|------|
| `deception_engine.py` | Monitors `attacker_profiles`; spawns environments at score ≥ 10 |
| `env_generator.py` | `ENV_TEMPLATES` by attacker tier; fake filesystem, credentials, banners |

### `src/cbee/`

| File | Role |
|------|------|
| `cbee_engine.py` | Background loop (every 30s); reads `attacker_profiles`; fires injections when bias.overall ≥ 15 |
| `bias_scorer.py` | Scores 5 cognitive bias dimensions from session features |
| `bait_injector.py` | Generates `BaitInjection` assets targeting the dominant bias |

### `src/response/`

| File | Role |
|------|------|
| `response_engine.py` | Decision matrix; `_firewall_block()` via iptables; `_isolate_session()` rate-limit rule; `_apply_rate_limit()` tc netem; alerts via email/Slack/Telegram |

### `src/api/`

| File | Role |
|------|------|
| `app.py` | Flask app; all REST routes; SocketIO server; `@cached()` decorator; `_get_cbee()` singleton; JWT auth middleware |

### `dashboard/`

| File | Role |
|------|------|
| `templates/index.html` | Single-page app shell; all section HTML |
| `static/js/app.js` | Core: navigation, WebSocket, live feed pagination, KPIs, geo map, charts, attacker modal |
| `static/js/behavior.js` | Behavior Analysis section: intent chart, tier chart, top commands, profiles table |
| `static/js/intel.js` | Threat Intel section: IOC feed, country bars, port bars, attack type donut |
| `static/css/dashboard.css` | Full dark-theme stylesheet |

---

## Threat Score Formula

```
score = (ML_confidence × 40)
      + TTP_score
      + tier_bonus        { beginner:0, automated_bot:15, advanced_human:30 }
      + persistence_bonus { 1 session:5 … 100+ sessions:65 }
      + volume_bonus      { min(total_commands ÷ 5, 15) }

capped at 100.0
```

---

## Intent Classes

`reclassify_intent()` in `attacker_profile.py` examines all stored commands across sessions:

| Intent | Primary signals |
|--------|-----------------|
| `cryptomining` | xmrig, miner keywords |
| `malware_deployment` | wget/curl/tftp + chmod/bash, or scp -t + execute |
| `credential_harvesting` | /etc/shadow access; or brute-force with zero commands |
| `bot_enrollment` | crontab/.bashrc persistence; /ip cloud; CPU probing |
| `lateral_movement` | ssh/scp/rsync with > 3 occurrences |
| `reconnaissance` | Fallback |

---

## MongoDB Collections

| Collection | Written by | Read by |
|-----------|-----------|---------|
| `alert_events` | Detection | API, Dashboard, BehaviorEngine |
| `cowrie_sessions` | CowrieSessionBuilder | BehaviorEngine |
| `attacker_profiles` | BehaviorEngine | API, DeceptionEngine, CBEEEngine, ResponseEngine |
| `deception_environments` | DeceptionEngine | API |
| `cbee_profiles` | CBEEEngine | API |
| `cbee_injections` | CBEEEngine | API |
| `response_log` | ResponseEngine | API (KPIs) |
| `attacker_twins` | Digital Twin module | API |
| `gadcf_assets` | GADCF module | API |
| `soc_reports` | SOC Analyst module | API |
