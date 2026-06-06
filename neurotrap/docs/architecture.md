# NeuroTrap CADN — Architecture

## System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 — Capture                                              │
│  Cowrie (SSH/Telnet) · Dionaea (SMB/HTTP/FTP)                   │
│  OpenCanary (multi-service +RDP) · Galah (LLM web app)          │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON logs + raw packets
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 2 — Detection                                            │
│  Scapy PacketMonitor · Zeek IDS · LogIngestionPipeline          │
│  → Normalizes all sources into AlertEvent schema                 │
│  → Writes to MongoDB alert_events collection                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ AlertEvent stream
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 3 — Behavior Analysis                                    │
│  AttackerClassifier (RF+SVM ensemble, F1>0.85)                  │
│  TTPExtractor (MITRE ATT&CK rule + embedding matching)          │
│  AttackerProfile (per-IP persistent session aggregation)         │
└────────────────────────────┬────────────────────────────────────┘
                             │ AttackerProfile (enriched)
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 4 — Deception Engine                                     │
│  DeceptionEngine → ENV_TEMPLATES[tier]                          │
│  CredentialGenerator (Faker-based, seeded per IP)               │
│  Docker container spawner (personalized Cowrie instances)        │
└────────────────────────────┬────────────────────────────────────┘
                             │ AttackerProfile.threat_score
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 5 — Response & Visualization                             │
│  ResponseEngine (decision matrix: log/slow/isolate/block)        │
│  Flask REST API + SocketIO WebSocket                             │
│  Real-time dashboard (Leaflet heatmap, Chart.js timeline)        │
└─────────────────────────────────────────────────────────────────┘
```

## Docker Network Topology

```
Internet ──► honeypot-net (172.20.0.0/24)
              │
              ├── cowrie:2222/2223
              ├── dionaea:21,80,445,3306
              ├── opencanary:1433,161,5900,3389
              ├── galah:8088
              │
              ▼
            elk-net (internal)
              │
              ├── mongodb:27017
              ├── packet-monitor
              ├── behavior-engine
              └── deception-engine
                    │
                  management-net (internal)
                    │
                    ├── api:5000
                    └── nginx:443
```

## Data Flow: Cowrie Session → Dashboard

1. Attacker SSH-connects → Cowrie logs `cowrie.json`
2. LogTailer reads new lines → `AlertEvent.from_cowrie()`
3. `LogIngestionPipeline.ingest()` writes to `alert_events`
4. `BehaviorEngine._run_loop()` picks up session → classifies
5. `AttackerProfile` updated → `attacker_profiles` collection
6. `DeceptionEngine` spawns environment if score ≥ 30
7. `ResponseEngine.evaluate()` takes action if score ≥ 40
8. Flask SocketIO emits `new_event` → dashboard updates in ≤5s
