# NeuroTrap CADN — System Overview

**CADN — Cognitive Adaptive Deception Network**

NeuroTrap is an active-defense honeypot platform for defensive SOC operations. It lures attackers into fully instrumented decoy environments, profiles their behavior with machine learning, and adapts the deception in real time to keep attackers engaged while extracting maximum intelligence.

---

## Design Philosophy

Traditional perimeter security focuses on blocking. NeuroTrap focuses on *engaging*: it presents a believable attack surface, studies what the attacker does once inside, classifies who they are and what they want, then generates a personalized decoy tailored to that specific threat actor.

Three principles drive every design decision:

1. **Isolation** — attacker-facing infrastructure is physically separated from analytics and management by Docker network segmentation. A fully compromised honeypot cannot reach the database or the operator dashboard.
2. **Normalization** — all heterogeneous sensor outputs (JSON logs, raw packets, Zeek flows) converge into a single `AlertEvent` schema, enabling every downstream module to consume one clean stream.
3. **Adaptability** — classification and deception are per-attacker, not generic. A script-kiddie and an APT actor see different environments, different planted credentials, and different bait content.

---

## Ten-Layer Architecture

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────┐
│  Layer 1 — CAPTURE                               │
│  Cowrie (SSH/Telnet)  OpenCanary (multi-service) │
│  Galah (LLM web app)  Native Python sensors      │
└─────────────────────────┬────────────────────────┘
                          │  JSON logs + raw packets
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 2 — DETECTION                             │
│  Scapy PacketMonitor  LogIngestionPipeline        │
│  CowrieSessionBuilder  AlertEvent schema          │
│  → alert_events (MongoDB)                        │
└─────────────────────────┬────────────────────────┘
                          │  normalized AlertEvent stream
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 3 — BEHAVIOR ANALYSIS                     │
│  SessionFeatureExtractor  AttackerClassifier      │
│  TTPExtractor (MITRE ATT&CK)  AttackerProfile     │
│  → attacker_profiles (MongoDB)                   │
└─────────────────────────┬────────────────────────┘
                          │  AttackerProfile + threat_score
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 4 — DECEPTION ENGINE                      │
│  DeceptionEngine  CredentialGenerator             │
│  Tiered environment templates (3 archetypes)     │
│  → deception_environments                        │
└─────────────────────────┬────────────────────────┘
                          │  (parallel enrichment)
              ┌───────────┴──────────┐
              ▼                      ▼
┌─────────────────────┐  ┌──────────────────────────┐
│  Layer 5 — CBEE     │  │  Layer 6 — GADCF          │
│  Cognitive Bias      │  │  Generative fake content  │
│  Exploitation Engine │  │  (env files, emails,      │
│  → cbee_profiles     │  │   code, wikis, DB dumps)  │
│  → cbee_injections   │  │  → gadcf_assets           │
└─────────────────────┘  └──────────────────────────┘
              │                      │
              └───────────┬──────────┘
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 7 — ATTACKER DIGITAL TWIN                 │
│  DigitalTwin dataclass  TacticPredictor (Markov)  │
│  KillChainMapper  → attacker_twins               │
└─────────────────────────┬────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 8 — FHIM                                  │
│  Federated Honeypot Intelligence Mesh             │
│  FederatedNode (differential privacy)             │
│  FedAvgServer  → fhim_rounds                     │
└─────────────────────────┬────────────────────────┘
                          │  threat_score / response decision
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 9 — RESPONSE ENGINE                       │
│  Decision matrix (log / slow / isolate / block)  │
│  iptables + tc netem + PCAP forensics            │
│  → response_log                                  │
└─────────────────────────┬────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 10 — API + DASHBOARD                      │
│  Flask REST API + Flask-SocketIO                  │
│  AI SOC Analyst (triage / reports / Q&A)          │
│  Real-time SPA dashboard                          │
└──────────────────────────────────────────────────┘
```

> **Note:** ASHRTA (Autonomous Self-Hardening Red-Team Adversarial) was planned as an additional response layer but is not implemented — `src/ashrta/` does not exist and `/api/ashrta/run` is not wired.

---

## Data Flow: Cowrie Session to Dashboard

```
1. Attacker SSH-connects → Cowrie logs cowrie.json
2. CowrieSessionBuilder tails the file line-by-line
3. AlertEvent.from_cowrie() normalizes each event
4. alert_events collection receives every interaction
5. On cowrie.session.closed, a complete session doc is written to cowrie_sessions
6. BehaviorEngine._run_loop() processes unclassified sessions
7. SessionFeatureExtractor builds a 13-dim feature vector
8. AttackerClassifier predicts intent (6 classes) and tier (3 classes)
9. TTPExtractor maps commands → MITRE technique IDs
10. AttackerProfile upserted in attacker_profiles
11. _compute_threat_score() calculates composite 0–100 score
12. reclassify_intent() re-examines all session commands
13. DeceptionEngine spawns personalized environment if score ≥ 10
14. CBEEEngine scores cognitive biases; fires bait injection if overall ≥ 25
15. GADCFEngine generates fake content assets matching intent + industry
16. AttackerDigitalTwin built from all enriched data
17. ResponseEngine.evaluate() takes action based on score thresholds
18. Flask SocketIO emits new_event → dashboard updates in < 5 s
```

---

## Docker Network Topology

```
Internet
    │
    ▼  (published ports: 22, 23, 80, 443, 8080, 8088)
┌─────────────────────────────────────────┐
│  honeypot-net  (172.20.0.0/24)          │
│  bridge, external                       │
│  cowrie  opencanary  galah  nginx       │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐   ┌──────────────────────┐
│  elk-net     │   │  management-net      │
│  internal    │   │  internal            │
│  mongodb     │   │  api ↔ nginx         │
│  behavior    │   │  deception           │
│  monitor*    │   │                      │
└──────────────┘   └──────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  monitor-bridge  (172.25.0.0/24)       │
│  non-internal bridge                   │
│  mongodb static IP 172.25.0.10         │
│  packet-monitor (host network mode)    │
└────────────────────────────────────────┘
```

The `packet-monitor` container uses host-network mode to sniff raw packets, so it cannot join the internal `elk-net`. The `monitor-bridge` solves this: MongoDB gets a static IP on a non-internal bridge, and the monitor's `MONGO_URI` addresses it directly.

---

## Component Map

| Component | Source | Container | Purpose |
|-----------|--------|-----------|---------|
| Cowrie | `cowrie/cowrie:latest` | `neurotrap-cowrie` | SSH/Telnet honeypot, full shell emulation |
| OpenCanary | `Dockerfile.opencanary` | `neurotrap-opencanary` | Low-interaction multi-service sensor (FTP, HTTP, SMB, MySQL, MSSQL, SNMP, VNC, RDP) |
| Galah | `0x4d31/galah:latest` | `neurotrap-galah` | LLM-powered web honeypot |
| Packet Monitor | `Dockerfile.monitor` | `neurotrap-monitor` | Scapy raw-packet capture + Cowrie log ingestion |
| Behavior Engine | `Dockerfile.behavior` | `neurotrap-behavior` | ML classifier, TTP extractor, attacker profiling |
| Deception Engine | `Dockerfile.deception` | `neurotrap-deception` | Per-attacker environment spawner |
| MongoDB | `mongo:6.0` | `neurotrap-mongodb` | Primary data store |
| API | `Dockerfile.api` | `neurotrap-api` | Flask REST + WebSocket + dashboard |
| Nginx | `nginx:alpine` | `neurotrap-nginx` | TLS termination + reverse proxy |

---

## MongoDB Collections

| Collection | Writer | Purpose |
|-----------|--------|---------|
| `alert_events` | PacketMonitor, LogIngestionPipeline | All normalized attack events |
| `cowrie_sessions` | CowrieSessionBuilder | Aggregated SSH/Telnet sessions |
| `honeypot_sessions` | Native Python sensors | Sessions from Python honeypots |
| `attacker_profiles` | BehaviorEngine | ML-enriched per-IP profiles |
| `attacker_twins` | AttackerDigitalTwin | Behavioral digital twin snapshots |
| `deception_environments` | DeceptionEngine | Per-attacker decoy envs |
| `cbee_profiles` | CBEEEngine | Cognitive bias scores |
| `cbee_injections` | BaitInjector | Bait injection log |
| `gadcf_assets` | GADCFEngine | Generated fake content |
| `fhim_rounds` | FedAvgServer | Federated learning round metadata |
| `fhim_aggregation_rounds` | FedAvgServer | Per-round weight deltas |
| `response_log` | ResponseEngine | Autonomous response actions |
| `soc_reports` | SOCAnalyst | AI-generated incident reports |

---

## Key Performance Targets

| Metric | Target |
|--------|--------|
| Classifier F1 (macro, 6-class intent) | > 0.85 |
| Event → Dashboard latency | < 5 s |
| Honeypot environment spawn time | < 30 s |
| Response action time after threshold breach | < 10 s |
| Lynis hardening score | > 70 |

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Language | Python 3.11+ |
| Web framework | Flask + Flask-SocketIO + flask-jwt-extended |
| ML | scikit-learn (VotingClassifier: RF + SVM), spaCy, sentence-transformers |
| Data store | MongoDB 6.0 (fallback: SQLite via FallbackDB) |
| Honeypots | Cowrie, OpenCanary, Galah (LLM) |
| Packet capture | Scapy (NET_ADMIN + NET_RAW caps) |
| Auth | JWT + TOTP/MFA via pyotp |
| Infrastructure | Docker Compose, Nginx (SSL termination) |
| Frontend | Vanilla JS + Chart.js + Leaflet.js |
| Fake data | Faker library |
| Federated learning | NumPy (FedAvg) + differential privacy (Gaussian noise) |
