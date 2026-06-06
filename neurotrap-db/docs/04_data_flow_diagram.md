# 04 · Data Flow

End-to-end flow: **ingest → enrich → correlate → respond → report**, with the
collection written at each step.

```mermaid
flowchart TD
    HP["Honeypots<br/>Cowrie · Dionaea · OpenCanary · Galah"] -->|raw events| Q[Ingest queue]
    Q -->|normalize| AS[(attack_sessions)]

    AS -->|new source_ip| ENR{Enrichment worker}
    ENR -->|cache hit/refresh| TI[(threat_intel)]
    ENR -->|upsert profile| TA[(threat_actors)]

    AS -->|command/file/auth evidence| MM[(mitre_mappings)]
    TA -->|model update| DT[(digital_twins)]
    MM --> DT

    DT --> CAMP{Campaign correlation}
    TA --> CAMP
    CAMP --> AC[(attack_campaigns)]
    DT --> AII[(ai_insights)]

    AS -->|threat_score| RE{Response engine<br/>40 / 70 / 90}
    RE --> RA[(response_actions)]
    RE -->|score >= 30| DEC{Deception engine}
    DEC --> GE[(generated_environments)]
    GE --> AE[(active_environments)]
    AE --> DE[(deception_effectiveness)]

    RA --> AL[(alerts)]
    AE -->|canary fired| AL
    AS --> AIO[(ai_analyst_outputs)]
    AIO --> RPT[(reports)]
    AL --> RPT

    AS -. mirror .-> ES[("Elasticsearch")]
    TA -. mirror .-> ES
    AL -. mirror .-> ES

    RPT --> DASH["Dashboards / API"]
    ES --> DASH
    AL --> DASH

    subgraph RBAC
      U[(users)] --- RO[(roles)] --- PE[(permissions)]
      U --- LH[(login_history)]
      U --- AP[(analyst_profiles)]
    end
    DASH --- RBAC
```

## Step-by-step

1. **Ingest** — honeypot events are normalized into `attack_sessions` (status `active`).
2. **Enrich** — first sighting of a `source_ip` triggers the enrichment worker:
   `threat_intel` cache is read/refreshed and the `threat_actors` profile is upserted.
3. **Map** — command/file/auth evidence is matched to ATT&CK → `mitre_mappings`.
4. **Model** — `digital_twins` updates the actor's behavioural fingerprint;
   correlation produces `attack_campaigns` and predictive `ai_insights`.
5. **Respond** — the response engine reads the session `threat_score` and writes a
   `response_actions` decision (matrix 40/70/90); ≥30 also spins up a
   `generated_environments` → `active_environments` deception instance, scored in
   `deception_effectiveness`.
6. **Alert & report** — `alerts` fire (with delivery tracking); `ai_analyst_outputs`
   produce narratives feeding `reports`.
7. **Serve** — dashboards read MongoDB + the Elasticsearch mirror of hot collections.
