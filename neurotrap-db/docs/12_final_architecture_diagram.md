# 12 · Final Architecture Diagram

Enterprise view tying the sensor fleet, data platform, processing, and consumers
together.

```mermaid
flowchart TB
    subgraph Sensors["Deception / Sensor Fleet"]
      direction LR
      CW[Cowrie]:::hp
      DI[Dionaea]:::hp
      OC[OpenCanary]:::hp
      GA[Galah]:::hp
    end

    subgraph Ingest["Ingestion & Processing"]
      direction LR
      Q[[Ingest queue]]
      ENR[Enrichment worker]
      MAP[ATT&CK mapper]
      TWIN[Twin / campaign engine]
      RESP[Response engine]
      DECP[Deception orchestrator]
      AIA[AI SOC analyst]
    end

    subgraph Data["Data Platform — MongoDB rs0 (TLS · CSFLE · sharded hot)"]
      direction TB
      OPER[("Operational hot<br/>attack_sessions · alerts · response_actions · active_environments")]
      ANALY[("Analytical warm<br/>threat_actors · digital_twins · attack_campaigns · mitre_mappings · deception_effectiveness · ai_*")]
      REFC[("Reference / config<br/>users · roles · permissions · *_templates · deception_profiles")]
      CACHE[("Cache / audit<br/>threat_intel · login_history")]
    end

    ES[("Elasticsearch 8.x<br/>search & aggregation mirror")]
    COLD[("Cold archive<br/>object store + lifecycle")]
    KMS[("KMS / Vault")]

    subgraph Consumers["Consumers"]
      direction LR
      DASH[SOC Dashboards]
      API[REST / WebSocket API]
      RPTS[Reports / PDF]
      EXT[TAXII / threat sharing]
    end

    Sensors --> Q --> OPER
    OPER --> ENR --> CACHE
    ENR --> ANALY
    OPER --> MAP --> ANALY
    ANALY --> TWIN --> ANALY
    OPER --> RESP --> OPER
    RESP --> DECP --> OPER
    OPER --> AIA --> ANALY
    AIA --> RPTS

    OPER -. change streams .-> ES
    ANALY -. change streams .-> ES
    OPER -- archival job --> COLD
    KMS --- Data

    Data --> API
    ES --> DASH
    API --> DASH
    ANALY --> RPTS
    ANALY --> EXT

    REFC --- API

    classDef hp fill:#1f2937,stroke:#a855f7,color:#fff;
```

## Layer summary

| Layer | Role | Key collections |
|-------|------|-----------------|
| Sensors | Capture attacker telemetry | — (write to `attack_sessions`) |
| Ingestion & processing | Normalize, enrich, map, model, respond, deceive, explain | all writers |
| Data platform | System of record (MongoDB rs0), tiered hot/warm/ref/cache | 28 collections |
| Search mirror | Free-text + aggregation | Elasticsearch (doc 10) |
| Cold archive | Long-term raw retention | object store (doc 08) |
| Security plane | Keys, RBAC, audit | KMS, `users`/`roles`/`permissions`, `login_history` |
| Consumers | Dashboards, API, reports, sharing | reads from Mongo + ES |

This is the target enterprise topology; the single-replica-set + ES + connector
deployment in doc 11 is the concrete starting build that realizes it.
