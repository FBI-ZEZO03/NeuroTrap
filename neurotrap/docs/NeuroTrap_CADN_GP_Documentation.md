# NeuroTrap CADN
## Cognitive Adaptive Deception Network
### Graduation Project Documentation

---

**Project Title:** NeuroTrap CADN — Cognitive Adaptive Deception Network

**Submitted in Partial Fulfillment of the Requirements for the Degree of Bachelor of Science in Computer Science / Cybersecurity**

---

## Table of Contents

1. [Abstract](#abstract)
2. [Chapter 1: Introduction](#chapter-1-introduction)
3. [Chapter 2: Literature Review](#chapter-2-literature-review)
4. [Chapter 3: System Design and Architecture](#chapter-3-system-design-and-architecture)
5. [Chapter 4: Implementation](#chapter-4-implementation)
6. [Chapter 5: Testing and Evaluation](#chapter-5-testing-and-evaluation)
7. [Chapter 6: Conclusion and Future Work](#chapter-6-conclusion-and-future-work)
8. [References](#references)
9. [Appendices](#appendices)

---

## Abstract

**English**

NeuroTrap CADN (Cognitive Adaptive Deception Network) is an active-defense honeypot platform designed for real-world Security Operations Center (SOC) deployments. Unlike traditional honeypots that present a static decoy, NeuroTrap dynamically profiles each attacker using machine learning, classifies their intent and behavioral tier, and generates a personalized deception environment tailored to that specific threat actor. The system is composed of ten integrated layers: honeypot capture, event detection, machine learning behavior analysis, adaptive deception environment generation, cognitive bias exploitation, generative fake content production, attacker digital twin modeling, federated threat intelligence sharing, autonomous response enforcement, and a real-time SOC dashboard. The platform captures live attacker telemetry through Cowrie (SSH/Telnet), OpenCanary (multi-service), and Scapy packet monitoring. A VotingClassifier (Random Forest + SVM) ensemble classifies attacker sessions into six intent classes with a target macro-F1 score above 0.85. Threat scores are computed using a composite formula incorporating ML confidence, MITRE ATT&CK TTP mapping, attacker tier, session persistence, and command volume. Personalized deception environments, cognitive bias bait injections, and generative fake content assets are deployed in response to real-time threat intelligence. The system is fully containerized with Docker Compose and runs in production on a live internet-facing VPS, where it has captured and profiled over 90 real-world attack sources.

**Keywords:** Honeypot, Deception Technology, Machine Learning, Cybersecurity, MITRE ATT&CK, Threat Intelligence, SOC, Active Defense

---

## Chapter 1: Introduction

### 1.1 Background

Cybersecurity threats continue to grow in sophistication and frequency. Traditional perimeter-based defenses — firewalls, intrusion detection systems, and antivirus software — focus primarily on blocking known attack patterns. This reactive posture leaves organizations vulnerable to novel attack techniques and provides little intelligence about attacker methods, infrastructure, and intent.

Honeypot technology represents a fundamentally different approach: instead of blocking attackers, a honeypot lures them into a controlled, monitored environment where their every action is observed and recorded. This yields actionable threat intelligence that cannot be obtained from network logs or blocked connection attempts alone.

However, existing honeypot systems suffer from a critical limitation: they present a static environment that sophisticated attackers can recognize and avoid. A single low-interaction honeypot offering the same shell prompt to every visitor will quickly be identified and abandoned by experienced threat actors.

### 1.2 Problem Statement

Current honeypot solutions lack three critical capabilities:

1. **Personalization** — a script-kiddie and an Advanced Persistent Threat (APT) actor should not see the same environment. A generic honeypot fails to engage either effectively.

2. **Intelligence Extraction** — capturing commands is insufficient. Security teams need classified intent, mapped MITRE ATT&CK techniques, predicted next moves, and actionable response recommendations — not raw log files.

3. **Adaptation** — attackers learn. A honeypot that looks the same every visit will be recognized. The deception environment must adapt to each attacker's behavior, feeding them increasingly convincing artifacts tailored to their specific goals.

### 1.3 Objectives

NeuroTrap CADN addresses these gaps through the following objectives:

- Build a multi-sensor honeypot infrastructure capturing SSH, Telnet, HTTP, FTP, SMB, MySQL, RDP, VNC, SNMP, and MSSQL traffic
- Classify attacker behavior in real time using an ML ensemble classifier (intent + tier)
- Map observed commands to MITRE ATT&CK techniques automatically
- Generate personalized deception environments based on attacker tier and TTP profile
- Exploit cognitive biases to extend attacker engagement and extract deeper intelligence
- Produce generative fake content assets (credentials, code, email threads, database dumps) as bait
- Build a behavioral digital twin for each attacker with Markov-chain next-move prediction
- Enable federated threat intelligence sharing with differential privacy
- Enforce autonomous proportional responses (log / throttle / isolate / block)
- Surface all intelligence through a real-time SOC dashboard

### 1.4 Scope

The project covers the full stack: from raw packet capture on internet-facing honeypots to AI-generated incident reports viewed by SOC analysts. It is deployed and operational on a live Ubuntu 24.04 VPS with a public IP address, capturing real attacker traffic 24/7.

### 1.5 Report Organization

This report is organized as follows:
- **Chapter 2** reviews related work in honeypot technology, deception systems, and ML-based intrusion detection
- **Chapter 3** presents the system architecture, design decisions, and component interactions
- **Chapter 4** details the implementation of each module
- **Chapter 5** covers testing methodology and evaluation results
- **Chapter 6** concludes with lessons learned and future work directions

---

## Chapter 2: Literature Review

### 2.1 Honeypot Systems

Honeypots are decoy systems designed to attract attackers and study their behavior. Spitzner (2002) defined the foundational taxonomy of honeypots by interaction level:

- **Low-interaction honeypots** (e.g., Honeyd) emulate limited services with minimal risk. They are easy to deploy but quickly identified by experienced attackers.
- **Medium-interaction honeypots** (e.g., Cowrie) simulate a full shell environment. Attackers can execute commands, but the commands are intercepted and logged without affecting the real system.
- **High-interaction honeypots** run real operating systems in isolated environments, offering maximum realism at higher operational risk.

**Cowrie** (Oosterhof, 2014) is the most widely deployed SSH/Telnet medium-interaction honeypot. It records all credentials, commands, and file transfers in structured JSON format. NeuroTrap uses Cowrie as its primary capture sensor.

**OpenCanary** (Thinkst Applied Research, 2015) provides a multi-service low-interaction honeypot covering FTP, HTTP, SMB, MySQL, MSSQL, RDP, VNC, and SNMP. NeuroTrap deploys it to cover the full attack surface.

### 2.2 Deception Technology

Modern deception technology moves beyond static honeypots to active, adaptive systems. Key contributions include:

- **HoneyPy** and **OpenHoneypot** extended the basic honeypot model with pluggable service emulation
- **Canarytokens** (Thinkst, 2015) introduced the concept of embedded tripwires — fake credentials that generate alerts when used externally
- **Galah** (0x4d31, 2023) pioneered LLM-powered web honeypots that dynamically generate realistic HTTP responses, defeating fingerprinting tools

NeuroTrap extends these concepts by making the entire environment adaptive — not just individual service responses, but the hostname, file system, planted credentials, and bait content all vary per attacker.

### 2.3 Machine Learning for Intrusion Detection

Several research directions are relevant to NeuroTrap's behavior analysis layer:

- **CICIDS datasets** (Canadian Institute for Cybersecurity, 2017–2018) established benchmarks for network intrusion classification using Random Forest, SVM, and neural network classifiers
- **UNSW-NB15** (Moustafa & Slay, 2015) provided a comprehensive labeled dataset for evaluating multi-class intrusion detection
- **KDD Cup 99 / NSL-KDD** remain reference benchmarks despite age concerns

NeuroTrap's classifier departs from network-flow based approaches. Instead of classifying packets or flows, it classifies **command sequences** — the series of shell commands executed inside a honeypot session. This is closer to work by Veeramachaneni et al. (2016) on user behavior analytics.

The VotingClassifier ensemble (Random Forest + SVM) follows established practice for tabular classification tasks where diversity between base learners improves robustness.

### 2.4 MITRE ATT&CK Framework

The MITRE ATT&CK framework (Strom et al., 2018) provides a globally accessible knowledge base of adversary tactics, techniques, and procedures (TTPs). NeuroTrap's TTPExtractor maps honeypot commands to ATT&CK technique IDs through rule-based matching and sentence-transformer embedding similarity. This allows SOC analysts to understand attacker behavior in a standardized, universally recognized taxonomy.

### 2.5 Cognitive Bias in Security

Research in behavioral security (Workman, 2008; Vishwanath et al., 2011) demonstrates that attackers, like all humans, are subject to cognitive biases. Key biases exploited in social engineering include:

- **Curiosity gap**: the drive to discover hidden information
- **Confirmation bias**: tendency to seek information confirming existing assumptions
- **Sunk cost fallacy**: continued investment based on prior effort rather than current value
- **Authority bias**: deference to signals of authority or privilege
- **Scarcity framing**: urgency when perceiving limited time or access

NeuroTrap's CBEE module is the first known implementation of algorithmic cognitive bias detection and exploitation in a honeypot context.

### 2.6 Federated Learning with Differential Privacy

Federated learning (McMahan et al., 2017) enables collaborative model training without sharing raw data. Each participant trains locally and shares only model weight updates, which are aggregated centrally. Dwork's differential privacy framework (2006) adds mathematical noise to shared updates, preventing reconstruction of individual training data. NeuroTrap's FHIM module applies these techniques to enable threat intelligence sharing across organizations without exposing sensitive incident data.

### 2.7 Gap Analysis

Existing solutions address some of these challenges in isolation:

| System | Multi-sensor | ML Classification | Adaptive Deception | Cognitive Bias | Federated Intel |
|--------|-------------|------------------|-------------------|---------------|----------------|
| Cowrie | No | No | No | No | No |
| OpenCanary | Yes | No | No | No | No |
| Deception as a Service platforms | Partial | Limited | Yes | No | No |
| NeuroTrap CADN | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

NeuroTrap is the first integrated platform combining all five capabilities in a fully open, deployable system.

---

## Chapter 3: System Design and Architecture

### 3.1 Design Philosophy

Three principles drive every design decision in NeuroTrap:

1. **Isolation** — attacker-facing infrastructure is physically separated from analytics and management by Docker network segmentation. A fully compromised honeypot container cannot reach the database or the operator dashboard.

2. **Normalization** — all heterogeneous sensor outputs (Cowrie JSON logs, raw packets, OpenCanary alerts) converge into a single `AlertEvent` schema, enabling every downstream module to consume one clean data stream.

3. **Adaptability** — classification and deception are per-attacker, not generic. A script-kiddie and an APT actor see different environments, different planted credentials, and different bait content.

### 3.2 Ten-Layer Architecture

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
                          ▼
┌──────────────────────────────────────────────────┐
│  Layer 10 — API + DASHBOARD                      │
│  Flask REST API + Flask-SocketIO                  │
│  AI SOC Analyst (triage / reports / Q&A)          │
│  Real-time SPA dashboard                          │
└──────────────────────────────────────────────────┘
```

### 3.3 Docker Network Topology

Network isolation is a core security requirement. NeuroTrap uses four Docker networks to strictly segment communication:

```
Internet
    │  (ports: 22, 23, 80, 443, 8080, 8088)
    ▼
┌─────────────────────────────────────────┐
│  honeypot-net  (172.20.0.0/24)          │
│  External bridge                        │
│  cowrie  opencanary  galah  nginx       │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐   ┌──────────────────────┐
│  elk-net     │   │  management-net      │
│  Internal    │   │  Internal            │
│  mongodb     │   │  api ↔ nginx         │
│  behavior    │   │  deception           │
└──────────────┘   └──────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  monitor-bridge  (172.25.0.0/24)       │
│  Non-internal bridge                   │
│  mongodb static IP 172.25.0.10         │
│  packet-monitor (host network mode)    │
└────────────────────────────────────────┘
```

Key isolation properties:
- MongoDB is never exposed to the internet
- Honeypot containers cannot reach the management network
- The packet monitor uses host-network mode (required for raw packet capture) but reaches MongoDB only via a dedicated bridge at a static IP

### 3.4 Technology Stack

| Layer | Technologies |
|-------|-------------|
| Language | Python 3.11+ |
| Web Framework | Flask + Flask-SocketIO + flask-jwt-extended |
| Machine Learning | scikit-learn (VotingClassifier: RF + SVM), spaCy, sentence-transformers |
| Data Store | MongoDB 6.0 (SQLite fallback for local development) |
| Honeypots | Cowrie, OpenCanary, Galah (LLM-powered) |
| Packet Capture | Scapy (NET_ADMIN + NET_RAW Linux capabilities) |
| Authentication | JWT + TOTP/MFA via pyotp |
| Infrastructure | Docker Compose, Nginx (SSL termination) |
| Frontend | Vanilla JavaScript + Chart.js + Leaflet.js |
| Fake Data | Faker library |
| Federated Learning | NumPy (FedAvg) + Gaussian differential privacy |
| LLM Integration | Groq API (llama-3.3-70b-versatile), Anthropic Claude (fallback) |

### 3.5 Database Design

MongoDB is used as the primary data store with 13 active collections:

| Collection | Writer | Purpose |
|-----------|--------|---------|
| `alert_events` | PacketMonitor, LogPipeline | All normalized attack events |
| `cowrie_sessions` | CowrieSessionBuilder | Aggregated SSH/Telnet sessions |
| `attacker_profiles` | BehaviorEngine | ML-enriched per-IP profiles |
| `attacker_twins` | DigitalTwin module | Behavioral digital twin snapshots |
| `deception_environments` | DeceptionEngine | Per-attacker decoy environments |
| `cbee_profiles` | CBEEEngine | Cognitive bias scores per attacker |
| `cbee_injections` | BaitInjector | Bait injection log |
| `gadcf_assets` | GADCFEngine | Generated fake content assets |
| `fhim_rounds` | FedAvgServer | Federated learning round metadata |
| `fhim_aggregation_rounds` | FedAvgServer | Per-round weight deltas |
| `response_log` | ResponseEngine | Autonomous response actions |
| `soc_reports` | SOCAnalyst | AI-generated incident reports |
| `honeypot_sessions` | Native sensors | Sessions from Python sensors |

### 3.6 Data Flow

The complete data flow from attacker connection to dashboard update:

```
1.  Attacker SSH-connects → Cowrie emulates shell, logs cowrie.json
2.  CowrieSessionBuilder tails the JSON file line-by-line
3.  AlertEvent.from_cowrie() normalizes each Cowrie event ID
4.  alert_events collection receives every interaction in real time
5.  On cowrie.session.closed, a complete session document is written to cowrie_sessions
6.  BehaviorEngine._run_loop() processes all unclassified sessions
7.  SessionFeatureExtractor builds a 13-dimensional feature vector
8.  AttackerClassifier predicts intent (6 classes) and tier (3 classes)
9.  TTPExtractor maps commands → MITRE ATT&CK technique IDs
10. AttackerProfile is upserted in attacker_profiles
11. _compute_threat_score() calculates composite 0–100 threat score
12. reclassify_intent() re-examines all accumulated session commands
13. DeceptionEngine spawns personalized environment if threat_score ≥ 10
14. CBEEEngine (every 30s) scores cognitive biases; fires bait injection if bias.overall ≥ 15
15. GADCFEngine generates fake content assets matching intent + target industry
16. AttackerDigitalTwin built from all enriched data sources
17. ResponseEngine.evaluate() takes autonomous action based on score thresholds
18. Flask-SocketIO emits new_event to connected dashboard clients in < 5 seconds
```

---

## Chapter 4: Implementation

### 4.1 Layer 1 — Honeypot Sensors

#### 4.1.1 Cowrie (SSH/Telnet Honeypot)

Cowrie is the primary capture sensor. It runs as a Docker container listening on ports 22 (SSH) and 23 (Telnet). Attackers connect and interact with a full emulated shell environment. Cowrie records:
- All login attempts (username, password, success/failure)
- Every command executed
- File uploads and downloads (stored locally)
- Client version strings and key exchange fingerprints

Cowrie logs are written in JSONL format to a Docker volume shared with the packet monitor container.

#### 4.1.2 OpenCanary (Multi-Service Honeypot)

OpenCanary covers the full port matrix: FTP (21), HTTP (80), SMB (445), MySQL (3306), MSSQL (1433), SNMP (161/UDP), VNC (5900), and RDP (3389). It emits JSON alert records to a shared log volume that the ingestion pipeline monitors.

#### 4.1.3 Packet Monitor

The `PacketMonitor` (`src/detection/packet_monitor.py`) uses Scapy in host-network mode to capture raw packets. It detects:
- **Port scans**: more than 10 unique destination ports within 5 seconds from one source → `port_scan` alert
- **Brute force**: more than 5 failed login attempts per minute → `brute_force` alert
- **Protocol anomalies**: malformed packets, unexpected UDP traffic → `protocol_anomaly`
- **Tool fingerprints**: known scanner User-Agents, tool signatures in payload

#### 4.1.4 AlertEvent Schema

All sensor outputs are normalized into the `AlertEvent` dataclass:

```python
@dataclass
class AlertEvent:
    src_ip: str
    dst_port: int
    attack_type: str        # port_scan | brute_force | ssh_login | ...
    honeypot_source: str    # cowrie | opencanary | packet_monitor
    severity: str           # critical | high | medium | low | info
    timestamp: float
    command: Optional[str]
    raw_payload: Optional[str]
    session_id: Optional[str]
    username: Optional[str]
    password: Optional[str]
```

A `_COWRIE_SKIP` frozenset filters Cowrie metadata events (key exchange, version strings) that carry no attack signal, preventing `unknown` attack types from dominating the dataset.

### 4.2 Layer 2 — Detection Pipeline

#### 4.2.1 Log Ingestion Pipeline

`LogIngestionPipeline` (`src/detection/log_pipeline.py`) runs background threads that tail Cowrie and OpenCanary JSONL log files. For each new line:
1. Parse the JSON record
2. Call `AlertEvent.from_cowrie()` or `AlertEvent.from_opencanary()` to normalize
3. Insert into `alert_events` collection
4. Emit the event to the Flask-SocketIO live feed

#### 4.2.2 CowrieSessionBuilder

`CowrieSessionBuilder` aggregates individual Cowrie events into complete session documents. It maintains an in-memory session buffer keyed by `session_id`. On `cowrie.session.closed`, it flushes the complete session (all commands, login attempts, duration, source IP) into `cowrie_sessions` for the behavior engine to process.

### 4.3 Layer 3 — Behavior Analysis

#### 4.3.1 Feature Engineering

`SessionFeatureExtractor` converts a Cowrie session document into a 13-dimensional numeric vector:

| Feature | Description |
|---------|-------------|
| `total_commands` | Number of commands executed |
| `unique_commands` | Count of distinct commands |
| `dangerous_count` | Commands matching danger patterns (wget, chmod, shadow, etc.) |
| `recon_count` | Commands matching recon patterns (id, uname, netstat, etc.) |
| `download_attempts` | wget / curl / tftp invocations |
| `file_access` | /etc/, /home/, .ssh/ accesses |
| `session_duration` | Session end time − start time in seconds |
| `login_attempts` | Total login attempts in the session |
| `failed_logins` | Failed login count |
| `has_persistence` | 1 if crontab / systemctl / bashrc found |
| `has_lateral` | 1 if ssh / scp / rsync to another host |
| `dangerous_ratio` | dangerous_count / total_commands |
| `recon_ratio` | recon_count / total_commands |

#### 4.3.2 Intent Classifier

`AttackerClassifier` uses a `VotingClassifier` combining a `RandomForestClassifier` and an `SVC` (soft voting). The model is trained on synthetically generated labeled session data: 900 sessions × 6 intent classes × template-based command patterns.

**Intent Classes:**

| Class | Behavioral Signature |
|-------|---------------------|
| `reconnaissance` | Enumeration commands (id, uname, ls, netstat). Default fallback. |
| `credential_harvesting` | /etc/shadow, ~/.ssh, bash_history access. Brute-force with zero commands. |
| `malware_deployment` | wget/curl/tftp + chmod +x + execute, or scp upload + execute. |
| `lateral_movement` | ssh/scp/rsync to other hosts, network sweeps. |
| `cryptomining` | xmrig, miner binaries, pool URLs, high-CPU fingerprints. |
| `bot_enrollment` | Fetch-and-run loader + cron/bashrc persistence, router fingerprinting. |

**Attacker Tiers:**

| Tier | Characteristics |
|------|----------------|
| `beginner` | Simple brute-force or single recon commands; short sessions |
| `automated_bot` | High-speed credential stuffing; consistent tool signatures |
| `advanced_human` | Multi-stage attack; lateral movement; privilege escalation |

#### 4.3.3 TTP Extraction

`TTPExtractor` maps commands to MITRE ATT&CK technique IDs via two layers:

**Layer 1 — Rule-Based Matching (50+ rules):**
```
wget  → T1105 (Command and Control, confidence: 0.95)
crontab → T1053.003 (Persistence, confidence: 0.90)
/etc/shadow → T1003.008 (Credential Access, confidence: 0.95)
chmod +s → T1548.001 (Privilege Escalation, confidence: 0.90)
ssh → T1021.004 (Lateral Movement, confidence: 0.85)
```

**Layer 2 — Embedding Fallback:**
Commands not matching any rule are encoded with `sentence-transformers` (`all-MiniLM-L6-v2`) and compared against pre-embedded MITRE technique descriptions. Matches with cosine similarity > 0.65 are accepted.

#### 4.3.4 Threat Score Formula

```
threat_score = (ML_confidence × 40)
             + TTP_score          [0–40]
             + tier_bonus         [beginner:0, automated_bot:15, advanced_human:30]
             + persistence_bonus  [27–65 based on session_count]
             + volume_bonus       [min(total_commands ÷ 5, 15)]

Capped at 100.0
```

**Persistence Bonus Table:**

| Sessions | Bonus |
|----------|-------|
| 1 | 27 |
| 2 | 32 |
| 3–4 | 37 |
| 5–9 | 42 |
| 10–19 | 48 |
| 20–49 | 55 |
| 50–99 | 62 |
| 100+ | 65 |

The high single-session bonus (27) ensures that even a first-time honeypot visitor scores in the MEDIUM range (~49), reflecting the inherent suspicion of any honeypot contact.

**TTP Tactic Weights:**

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

**Risk Bands:**

| Score | Band | Action |
|-------|------|--------|
| ≥ 75 | CRITICAL | Block immediately |
| 55–74 | HIGH | Isolate and alert |
| 35–54 | MEDIUM | Monitor closely |
| < 35 | LOW | Log only |

### 4.4 Layer 4 — Deception Engine

#### 4.4.1 Environment Templates

Three environment archetypes are defined, mapped to attacker tier:

| Attacker Tier | Template | What the Attacker Sees |
|--------------|----------|----------------------|
| `beginner` | `simple-linux` | Ubuntu 20.04, 2 services (SSH + HTTP), standard user files |
| `automated_bot` | `baited-server` | CentOS 7, 4 services, seeded with common credential-stuffing targets |
| `advanced_human` | `advanced-corporate` | Debian 11, 6 services + Docker, planted AWS keys, `.env` files, populated fake database |

Hostnames are randomized from a pool (e.g., `fin-db-01`, `vpn-gw-02`, `jenkins-prod`) so the same attacker sees a different machine each visit.

#### 4.4.2 TTP-Based Customization

The deception environment is further personalized based on detected MITRE TTPs:

| Detected Tactic | Environment Customization |
|----------------|--------------------------|
| Credential Access | Add `/etc/shadow` with seeded password hashes |
| Lateral Movement | Add SSH config with fake internal hostnames |
| Persistence | Add existing cron entries in `/var/spool/cron/` |
| Command and Control | Add fake outbound connection logs suggesting C2 |

#### 4.4.3 CredentialGenerator

`CredentialGenerator` uses `Faker` seeded deterministically per attacker IP (same attacker always gets same fake identity). It generates:
- SSH user accounts with realistic names and passwords
- AWS credentials file (`~/.aws/credentials`) with `AKIA...` key pattern
- `.env` files with `DB_PASSWORD`, `SECRET_KEY`, `STRIPE_KEY` fields
- `/etc/shadow` entries with bcrypt-hashed fake passwords
- Shell history with plausible timestamped command sequences
- 500+ fake database user records with emails and bcrypt hashes

Planted AWS key patterns serve as tripwires — if used externally, they signal the attacker took the bait.

#### 4.4.4 Environment Lifecycle

```
threat_score ≥ 10
    └── DeceptionEngine.generate_environment(profile)
            ↓
        [SPAWNED] Container running, is_active=True
            ↓  attacker interacts
        [ENGAGED] Events flow through detection pipeline
            ↓
        [TEARDOWN: idle > 60 minutes OR container stopped]
        is_active=False, historical record preserved
```

Constraints: maximum 20 active environments; auto-expire after 1 hour.

### 4.5 Layer 5 — Cognitive Bias Exploitation Engine (CBEE)

#### 4.5.1 The Five Bias Dimensions

Each attacker is scored on five cognitive bias dimensions (0–100):

**1. Curiosity Gap** — attacker actively hunts hidden/sensitive files (`.key`, `.env`, `.secret`, `.pem` extensions; `/var/log/`, `~/.ssh/` access)

**2. Confirmation Bias** — attacker runs discovery commands that confirm a consistent target hypothesis (`ls /var/www`, `ps aux | grep apache`)

**3. Sunk Cost** — attacker has invested significant time/bandwidth (`wget`/`curl` downloads, `apt install`, long sessions)

**4. Authority Signal** — attacker pursues privilege escalation (`sudo`, `chmod 4xxx`, `/etc/shadow`, kernel exploits)

**5. Scarcity Framing** — attacker establishes persistence urgently (`crontab -e`, `nohup`, `disown`, high login-attempt rate)

#### 4.5.2 Bait Injection

Injections fire when `bias.overall ≥ 15` and fewer than 3 injections have been sent for that IP.

| Dominant Bias | Injected Bait |
|--------------|---------------|
| `curiosity_gap` | Fake credential file at predictable path (`/tmp/.db_backup_credentials`) |
| `confirmation_bias` | Configuration confirming the attacker's assumed target identity |
| `sunk_cost` | Fake admin credentials behind a "requires authentication" endpoint |
| `authority_signal` | Fake `/etc/sudoers` entry granting full no-password sudo |
| `scarcity_framing` | Time-limited credential with expiry comment |

### 4.6 Layer 6 — Generative Adaptive Deception Content Factory (GADCF)

GADCF generates five types of fake digital assets tailored to the attacker's classified intent and apparent target industry:

| Asset Type | Example Content |
|-----------|----------------|
| `env_file` | `.env` with `AWS_ACCESS_KEY_ID`, `STRIPE_SECRET_KEY`, `DB_PASSWORD` |
| `email_thread` | IT helpdesk thread announcing credential rotation for production database |
| `code_repo` | Flask/Django project with hardcoded fallback credentials in connection strings |
| `wiki_page` | Internal runbook with server IPs, SSH keys, service account passwords |
| `db_dump` | SQL dump with fake user records including bcrypt-hashed passwords |

**Intent-to-Industry Mapping:**

| Intent | Target Industry | Asset Focus |
|--------|----------------|-------------|
| `credential_harvesting` | Financial Services | Banking API keys, high-value credentials |
| `malware_deployment` | E-Commerce | Payment processor keys, customer database |
| `lateral_movement` | Enterprise IT | Domain admin credentials, network diagrams |
| `cryptomining` | Cloud Infrastructure | AWS/Azure credentials, Kubernetes configs |
| `bot_enrollment` | ISP/Hosting | SSH keys, server lists, automation scripts |
| `reconnaissance` | Generic | Internal wikis, employee directories |

### 4.7 Layer 7 — Attacker Digital Twin

The Attacker Digital Twin (ADT) builds a persistent behavioral model for each threat actor:

**Identity:** Source IP, observed countries, tools used, honeypots touched

**Capability:** Attacker tier, sophistication score (0–100), automation score (0–100)

**MITRE Fingerprint:** Observed technique IDs, tactic sequence (chronological), kill chain stage

**Synthesis:** Current kill chain stage, cognitive bias profile summary, top-3 predicted next tactics, recommended SOC action

**Tactic Predictor:** A Markov chain blending 40% learned transitions from the attacker's observed sequence with 60% prior matrix based on real-world attack chain statistics. Outputs top-3 next tactics with probabilities.

**Kill Chain Mapping:** MITRE tactics are mapped to the 7-stage Lockheed Martin Cyber Kill Chain (Reconnaissance → Weaponization → Delivery → Exploitation → Installation → C&C → Actions on Objectives).

### 4.8 Layer 8 — Federated Honeypot Intelligence Mesh (FHIM)

FHIM enables multiple organizations to collaboratively improve the shared threat classifier without exposing raw attacker data.

**Protocol:**
1. Each `FederatedNode` trains a local RF+SVM classifier on its own honeypot sessions
2. It computes the weight delta vs. the current global model
3. Gaussian noise is added to the delta (epsilon-delta differential privacy, ε=1.0, δ=1e-5)
4. The noisy delta is submitted to the `FedAvgServer`
5. When ≥ 2 nodes have submitted, the server averages the deltas (FedAvg algorithm)
6. The updated global model is broadcast back to all nodes

**Demo Nodes:** Cairo University, Acme Financial, Fraunhofer FKIE, SaudiTelecom

### 4.9 Layer 9 — Response Engine

The Response Engine enforces autonomous proportional responses:

| Threat Score | Action | Enforcement |
|-------------|--------|-------------|
| ≥ 90 | `block_emergency` | `iptables -I INPUT -s <IP> -j DROP` + forensic PCAP (10K packets) + multi-channel alert |
| 70–89 | `isolate_alert` | iptables LOG rule + `tc netem delay 200ms` + alert |
| 40–69 | `slow_redirect` | `tc netem delay 500ms ± 50ms` (degrades automated tool reliability) |
| < 40 | `log_only` | Write to `response_log` only, no network intervention |

Alert channels: Email (SMTP), Slack webhook, Telegram bot. All network operations fail gracefully when `iptables`/`tc` are unavailable (mock mode for development).

### 4.10 Layer 10 — API and SOC Dashboard

#### 4.10.1 Flask REST API

The Flask API (`src/api/app.py`) provides 30+ REST endpoints with JWT authentication, role-based access control (admin / analyst), optional TOTP/MFA, and a 30-second in-memory response cache for expensive read endpoints.

Key endpoint groups:
- `/api/auth/` — login, MFA setup, OTP verification
- `/api/events/` — alert events, statistics
- `/api/attackers/` — attacker profiles, recalculate scores
- `/api/environments/` — deception environments
- `/api/cbee/` — bias profiles, injections, ad-hoc scoring
- `/api/gadcf/` — generated assets, manual generation
- `/api/twin/` — digital twins, forward simulation
- `/api/fhim/` — federated nodes, aggregation rounds
- `/api/soc/` — AI analyst triage, reports, Q&A, summary
- `/api/response/` — manual block, response log

#### 4.10.2 Real-Time Dashboard

The dashboard is a single-page application (SPA) built with vanilla JavaScript, Chart.js, and Leaflet.js. It communicates with the server via:
- REST API polling (every 15 seconds) for KPIs and section data
- Flask-SocketIO WebSocket for live event feed (< 5 second latency)

Dashboard sections:
- **Overview** — KPI cards (total events, active sessions, blocked IPs, deception environments), live event feed, geographic attack map
- **Behavior Analysis** — intent distribution, tier chart, top commands, attacker profiles table with MITRE heatmap
- **Honeypots** — per-sensor hit counts, recent attacker sessions, dynamic environments
- **Threat Intel** — IOC feed, top countries/ports, attack type distribution, active campaigns
- **CBEE** — bias profiles with 5-dimension radar charts, bait injection log
- **GADCF** — generated asset library with content preview
- **Digital Twins** — twin list with kill chain visualization, forward simulator
- **FHIM** — federated node status, aggregation round history
- **AI SOC Analyst** — triage queue, shift summary, incident reports, Q&A chat
- **Response Log** — autonomous action history with color-coded severity

#### 4.10.3 AI SOC Analyst

The AI SOC Analyst module uses an LLM (Groq llama-3.3-70b-versatile as primary, Anthropic Claude as fallback) to generate:
- **Triage queue** — all active attackers ranked by threat score with recommended action
- **Incident reports** — structured Markdown reports with executive summary, MITRE TTP table, timeline, and recommendations
- **Analyst Q&A** — natural-language interface grounded in live SOC data
- **Shift summary** — narrative summary of the past N hours of activity

The system operates fully in heuristic mode without any API key, with LLM mode purely additive.

---

## Chapter 5: Testing and Evaluation

### 5.1 Testing Strategy

NeuroTrap's test suite covers all major modules with 9 test files in `neurotrap/tests/`. Tests use in-process mocks and the `FallbackDB` SQLite store — no live MongoDB or Docker required for CI.

| Test File | Coverage |
|-----------|---------|
| `test_alert_schema.py` | `AlertEvent` validation, `from_cowrie()`, `from_zeek()` factory methods |
| `test_classifier.py` | `SessionFeatureExtractor`, training pipeline, prediction, tier classification |
| `test_ttp_extractor.py` | Command → MITRE technique mapping, confidence scoring |
| `test_deception_engine.py` | Environment generation, TTP personalization, Docker mock |
| `test_credential_generator.py` | SSH users, AWS/DB credentials, `.env`, shadow, history generation |
| `test_response_engine.py` | Threshold evaluation, action execution, alert dispatching |
| `test_database.py` | `FallbackDB` vs MongoDB interface equivalence |
| `test_honeypots.py` | SSH/HTTP/FTP/Telnet mock server sessions |
| `test_twin.py` | Twin building, tactic prediction, forward simulation |

### 5.2 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Classifier Macro-F1 (6-class intent) | > 0.85 | Achieved on synthetic test split |
| Event → Dashboard latency | < 5 seconds | Achieved (SocketIO push) |
| Honeypot environment spawn time | < 30 seconds | Achieved |
| Response action time after threshold | < 10 seconds | Achieved |
| Lynis hardening score | > 70 | Achieved |

### 5.3 Live Deployment Results

The system has been deployed on a live internet-facing VPS (Ubuntu 24.04, 6 CPU, 11 GB RAM) and has captured real-world attacker traffic continuously. As of the documentation date:

**Threat Score Distribution (91 captured attackers):**

| Risk Band | Count | Percentage |
|-----------|-------|-----------|
| CRITICAL (≥ 75) | 16 | 17.6% |
| HIGH (55–74) | 13 | 14.3% |
| MEDIUM (35–54) | 62 | 68.1% |
| LOW (< 35) | 0 | 0% |

**Active System Status:**
- 10 active deception environments (17 total ever spawned)
- 20 CBEE bait injections recorded
- 20 GADCF fake content assets generated
- 91 attacker profiles with MITRE TTP mappings
- AI SOC Analyst generating LLM-powered incident reports via Groq

**Top Attack Sources:** Multiple Eastern European and Asian IPs with CRITICAL threat scores (100/100), classified as `bot_enrollment` (automated_bot tier), with hundreds of SSH sessions each.

### 5.4 Attack Simulation

NeuroTrap includes an end-to-end attack simulation script (`scripts/simulate_attack.py`) that exercises all 5 stages of a realistic attack:

1. **Reconnaissance** — port scanning, service enumeration
2. **Brute Force** — credential stuffing with common username/password combinations
3. **Initial Access** — successful login, system fingerprinting (`id`, `uname`, `cat /etc/passwd`)
4. **Malware Stage** — `wget` download, `chmod +x`, execution attempt, `crontab -e` persistence
5. **Lateral Movement** — `ssh` attempts to internal addresses, `scp` data exfiltration

Running the simulation verifies the full pipeline: events flow through detection → behavior analysis → deception engine → CBEE → response engine → dashboard, all within the < 5 second latency target.

### 5.5 CI/CD Pipeline

GitHub Actions runs on every push to `master`:
1. Python 3.11 environment setup
2. `pytest tests/ -v --tb=short --cov=src`
3. `ruff check src/ tests/ --ignore E501` (lint)
4. Coverage report generation

---

## Chapter 6: Conclusion and Future Work

### 6.1 Achievements

NeuroTrap CADN successfully demonstrates that adaptive deception technology can be built as a unified, deployable platform. The key achievements are:

1. **Full-stack active defense** — 10 integrated layers from raw packet capture to AI-generated SOC reports, running as a production system capturing real internet traffic

2. **Personalized deception** — three attacker tier archetypes with TTP-based customization, ensuring that each threat actor encounters an environment tailored to their skill level and goals

3. **Cognitive bias exploitation** — the first known implementation of algorithmic cognitive bias detection and bait injection in a honeypot context, with five dimensions scored in real time

4. **Comprehensive ML pipeline** — VotingClassifier (RF+SVM) with 6 intent classes, 13 features, MITRE ATT&CK TTP mapping via rule-based and embedding-based matching

5. **AI-powered SOC** — LLM-generated incident reports and natural-language analyst Q&A, working in both heuristic and LLM modes

6. **Privacy-preserving federation** — FedAvg aggregation with differential privacy, enabling threat intelligence sharing without exposing raw incident data

### 6.2 Limitations

1. **Synthetic training data** — the ML classifier is trained on synthetically generated sessions. While the synthetic data is modeled on real attacker patterns, a classifier trained on real labeled Cowrie sessions would generalize better.

2. **GADCF template mode** — the generative content factory currently uses Faker-based templates rather than LLM-generated content (Ollama/Mistral not deployed). LLM mode would produce more contextually varied and convincing assets.

3. **FHIM demo mode** — the federated learning mesh runs with pre-computed demo deltas. Real FedAvg rounds require external partner organizations to submit updates from their own honeypot data.

4. **No TLS between FHIM nodes** — inter-node communication is not production-hardened; mutual TLS would be required for real federation.

5. **Cowrie-only session data** — the behavior engine processes Cowrie sessions. OpenCanary events flow to alert_events but not to cowrie_sessions, so multi-service attackers are partially profiled.

### 6.3 Future Work

**Short-term (0–6 months):**
- Train the classifier on real Cowrie session data from the live deployment using the `--from-db` flag
- Deploy Ollama on the VPS to enable LLM-mode GADCF content generation
- Add GeoIP-based country filtering and ISP reputation scoring to the threat score formula
- Implement canary token tripwire alerts: AWS-style keys that call home when used

**Medium-term (6–18 months):**
- Develop real FHIM integration with partner organizations, including mutual TLS and a federated node SDK
- Implement ASHRTA (Autonomous Self-Hardening Red-Team Adversarial) — a planned Layer 9 module that uses RL to optimize deception strategies based on attacker engagement metrics
- Add honeypot fingerprint randomization (OS version, kernel, installed packages) to defeat active fingerprinting tools
- Integrate with SIEM platforms (Splunk, Elastic SIEM) via Syslog/CEF output

**Long-term (18+ months):**
- Multi-tenant architecture enabling managed honeypot-as-a-service deployments
- Real-time threat intelligence sharing via STIX/TAXII feeds based on profiled attackers
- Automated canary deployment: when an attacker's credentials are confirmed to be active externally (via honeyclient), automatically expand the deception campaign

---

## References

1. Spitzner, L. (2002). *Honeypots: Tracking Hackers*. Addison-Wesley.

2. Oosterhof, M. (2014). *Cowrie SSH/Telnet Honeypot*. GitHub. https://github.com/cowrie/cowrie

3. Thinkst Applied Research. (2015). *OpenCanary: A Multi-Service Honeypot*. GitHub. https://github.com/thinkst/opencanary

4. MITRE Corporation. (2018). *ATT&CK: Adversarial Tactics, Techniques, and Common Knowledge*. https://attack.mitre.org/

5. Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2018). *MITRE ATT&CK: Design and Philosophy*. MITRE Technical Report.

6. McMahan, H. B., Moore, E., Ramage, D., Hampson, S., & y Arcas, B. A. (2017). Communication-Efficient Learning of Deep Networks from Decentralized Data. *AISTATS*.

7. Dwork, C. (2006). Differential Privacy. *Proceedings of ICALP*, 4052, 1–12.

8. Workman, M. (2008). Wisecrackers: A Theory-Grounded Investigation of Phishing and Pretext Social Engineering Threats to Information Security. *Journal of the American Society for Information Science and Technology*, 59(4), 662–674.

9. Vishwanath, A., et al. (2011). Phishing Susceptibility: An Investigation Into the Processing of a Targeted Spear Phishing Email. *IEEE Transactions on Professional Communication*, 54(4), 345–362.

10. Moustafa, N., & Slay, J. (2015). UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems. *MilCIS Conference*.

11. Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5–32.

12. Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. *JMLR*, 12, 2825–2830.

13. 0x4d31. (2023). *Galah: An LLM-powered Web Honeypot*. GitHub. https://github.com/0x4d31/galah

14. Lockheed Martin. (2011). *Intelligence-Driven Computer Network Defense Informed by Analysis of Adversary Campaigns and Intrusion Kill Chains*. Lockheed Martin White Paper.

15. Veeramachaneni, K., et al. (2016). AI^2: Training a Big Data Machine to Defend. *IEEE International Conference on Big Data Security*.

---

## Appendices

### Appendix A: System Requirements

| Component | Minimum | Recommended (Production) |
|-----------|---------|-------------------------|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| CPU | 4 cores | 6+ cores |
| RAM | 8 GB | 11 GB |
| Disk | 50 GB | 200+ GB (log retention) |
| Docker Engine | 24.x | Latest stable |
| Open Ports | 22, 23, 80, 443 | + 21, 445, 1433, 3306, 3389, 5900, 161/UDP |

### Appendix B: Environment Variables

| Variable | Purpose |
|----------|---------|
| `MONGO_URI` | MongoDB connection string |
| `MONGO_USER` / `MONGO_PASS` | MongoDB credentials |
| `SECRET_KEY` | Flask session secret |
| `JWT_SECRET` | JWT signing key |
| `ADMIN_USER` / `ADMIN_PASS` | Admin dashboard credentials |
| `ANALYST_USER` / `ANALYST_PASS` | Read-only analyst credentials |
| `MFA_ENABLED` / `MFA_SECRET` | Enable TOTP MFA for admin |
| `GROQ_API_KEY` | Groq LLM API key (SOC Analyst + GADCF) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (fallback LLM + Galah) |
| `MONITOR_INTERFACE` | Network interface for packet capture (e.g., `eth0`) |
| `SLACK_WEBHOOK_URL` | Slack alert channel |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram alert channel |

### Appendix C: Quick-Start Deployment

```bash
# 1. Clone the repository
git clone https://github.com/FBI-ZEZO03/NeuroTrap.git
cd NeuroTrap/neurotrap

# 2. Configure environment
cp .env.example .env
# Edit .env: set MONGO_PASS, SECRET_KEY, JWT_SECRET, ADMIN_PASS

# 3. Generate SSL certificate
bash scripts/generate_ssl_cert.sh

# 4. Move SSH to port 50402 (port 22 is used by Cowrie)
sudo sed -i 's/^#Port 22/Port 50402/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 5. Start the full stack
docker compose up -d

# 6. Initialize database indexes
docker compose exec api python scripts/setup_db_indexes.py

# 7. Train the ML classifier
docker compose exec behavior-engine python -m src.behavior.train_classifier

# 8. Access dashboard
# https://<your-ip>  (accept self-signed certificate)
# Login: admin / neurotrap2024 (change in .env)
```

### Appendix D: API Quick Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | — | JWT login |
| `/api/events` | GET | — | Alert events with filters |
| `/api/events/stats` | GET | — | KPI statistics |
| `/api/attackers` | GET | — | Top attacker profiles |
| `/api/profiles/recalculate` | POST | admin | Recalculate all threat scores |
| `/api/environments` | GET | — | All deception environments |
| `/api/cbee/profiles` | GET | — | Cognitive bias profiles |
| `/api/cbee/injections` | GET | — | Bait injection log |
| `/api/gadcf/assets` | GET | — | Generated deception assets |
| `/api/gadcf/generate` | POST | admin | Trigger asset generation |
| `/api/twin/list` | GET | — | All attacker digital twins |
| `/api/twin/simulate` | POST | admin | N-step attack simulation |
| `/api/soc/triage` | GET | — | AI SOC triage queue |
| `/api/soc/report` | POST | admin | Generate incident report |
| `/api/soc/summary` | GET | — | Shift summary |
| `/api/soc/chat` | POST | admin | AI analyst Q&A |
| `/api/response/block` | POST | admin | Manual IP block |
| `/api/response/log` | GET | — | Response action history |

### Appendix E: Glossary

| Term | Definition |
|------|-----------|
| **APT** | Advanced Persistent Threat — a sophisticated, sustained cyberattack |
| **CADN** | Cognitive Adaptive Deception Network — NeuroTrap's full name |
| **CBEE** | Cognitive Bias Exploitation Engine — Layer 5 of NeuroTrap |
| **Cowrie** | An open-source SSH/Telnet honeypot that emulates a full Linux shell |
| **Differential Privacy** | A mathematical framework for adding calibrated noise to prevent data reconstruction |
| **FedAvg** | Federated Averaging — an algorithm for aggregating distributed model updates |
| **FHIM** | Federated Honeypot Intelligence Mesh — Layer 8 of NeuroTrap |
| **GADCF** | Generative Adaptive Deception Content Factory — Layer 6 of NeuroTrap |
| **Honeypot** | A decoy system designed to attract and monitor attackers |
| **IOC** | Indicator of Compromise — observable evidence of an attack |
| **MITRE ATT&CK** | A framework of adversary tactics, techniques, and procedures |
| **SOC** | Security Operations Center |
| **TTP** | Tactics, Techniques, and Procedures — the methods used by attackers |
| **VotingClassifier** | An ensemble ML model combining multiple classifiers via voting |
