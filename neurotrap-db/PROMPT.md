# NeuroTrap — MongoDB Database Architecture Build Spec

> **How to use this file with Claude Code:**
> Save this file as `PROMPT.md` (or `CLAUDE.md`) in an empty project folder, then run Claude Code and say:
> *"Read PROMPT.md and execute it phase by phase. Stop after each phase, show me the files you created, and wait for my approval before continuing."*
> This file is written as an executable brief — Claude Code should treat the **Deliverables**, **File Layout**, and **Phases** as authoritative instructions, not just background reading.

---

## 0. Role & Operating Instructions (read first, Claude Code)

You are acting as a **senior database architect + detection engineer** designing the persistence layer for **NeuroTrap**, an AI-powered cyber **deception / honeypot / threat-analysis** platform for a defensive SOC. This is a defensive security project: honeypots, threat intel enrichment, MITRE ATT&CK mapping, attacker profiling, and reporting. There is no offensive tooling in scope — you are designing how *collected* attacker telemetry is stored, correlated, and surfaced.

Working rules:
1. **Work in phases.** Do NOT generate all files in one shot. Complete one phase, summarize what you produced, then pause for approval.
2. **One file per collection** for schemas and samples — do not cram everything into a single mega-file.
3. **Be consistent.** Reuse the same field-naming convention (`snake_case`), the same ID strategy, and the same timestamp convention (`ISODate`, UTC, field name `created_at` / `updated_at`) across every collection.
4. **Validate as you go.** Every JSON Schema you write must be valid against MongoDB's `$jsonSchema` validator. Every sample document must validate against its own schema.
5. **No placeholders.** Don't write `// TODO fill later`. If a field needs a value, give a realistic example.
6. **Cite assumptions.** When you make a design decision (e.g. embed vs. reference), add a one-line rationale comment.
7. After each phase, run a self-check against the **Acceptance Criteria** at the bottom.

Tech assumptions (override only if the user asks):
- **MongoDB 7.x**, replica set, with schema validation via `$jsonSchema`.
- Driver-agnostic schemas, but provide **Mongoose** model definitions as the canonical code form (Node.js).
- **Elasticsearch 8.x** for full-text/aggregation search alongside MongoDB.
- Expected scale: **thousands of attack sessions/day**, multi-year retention of profiles, hot/warm/cold tiering for raw session data.

---

## 1. Project Context

NeuroTrap collects attacker telemetry in real time from honeypots (**Cowrie**, **Dionaea**, **Honeyd**), enriches it with **threat intelligence APIs** (VirusTotal, AbuseIPDB, Shodan, OTX, GeoIP), maps activity to **MITRE ATT&CK**, builds persistent **attacker Digital Twins**, generates **adaptive deceptive environments**, scores **deception effectiveness**, and produces **AI SOC analyst** outputs and **reports**. The database is the backbone tying all of this together.

---

## 2. Authoritative Deliverables

Produce ALL of the following. Each is a real artifact in the repo, not prose in a chat reply.

1. **`docs/01_architecture_overview.md`** — system + data architecture overview.
2. **`docs/02_collection_list.md`** — the full collection inventory (table: name, purpose, est. write rate, retention tier).
3. **`schemas/<collection>.schema.json`** — one MongoDB `$jsonSchema` validator per collection.
4. **`models/<collection>.model.js`** — one Mongoose model per collection.
5. **`samples/<collection>.sample.json`** — at least one realistic sample document per collection (2–3 for the complex ones).
6. **`docs/03_relationship_diagram.md`** — entity-relationship diagram (Mermaid `erDiagram`).
7. **`docs/04_data_flow_diagram.md`** — ingest → enrich → correlate → respond → report flow (Mermaid `flowchart`).
8. **`docs/05_indexing_strategy.md`** — per-collection indexes + rationale + the `createIndex` commands.
9. **`docs/06_security_best_practices.md`** — auth, RBAC, encryption, field-level protection, audit.
10. **`docs/07_scalability.md`** — sharding keys, read/write scaling, capped/TTL strategy.
11. **`docs/08_retention_strategy.md`** — TTL indexes + tiering + archival rules per collection.
12. **`docs/09_backup_strategy.md`** — backup cadence, PITR, restore drills.
13. **`docs/10_elasticsearch_integration.md`** — what gets indexed in ES, sync mechanism, mappings.
14. **`docs/11_production_deployment.md`** — topology, sizing, monitoring, hardening checklist.
15. **`docs/12_final_architecture_diagram.md`** — enterprise-grade architecture diagram (Mermaid).
16. **`scripts/init_db.js`** — `mongosh` script that creates every collection with its validator and indexes.
17. **`README.md`** — how the repo is structured and how to run `init_db.js`.

---

## 3. File Layout (create exactly this tree)

```
neurotrap-db/
├── README.md
├── PROMPT.md                      # this file
├── docs/
│   ├── 01_architecture_overview.md
│   ├── 02_collection_list.md
│   ├── 03_relationship_diagram.md
│   ├── 04_data_flow_diagram.md
│   ├── 05_indexing_strategy.md
│   ├── 06_security_best_practices.md
│   ├── 07_scalability.md
│   ├── 08_retention_strategy.md
│   ├── 09_backup_strategy.md
│   ├── 10_elasticsearch_integration.md
│   ├── 11_production_deployment.md
│   └── 12_final_architecture_diagram.md
├── schemas/        # one *.schema.json per collection
├── models/         # one *.model.js (Mongoose) per collection
├── samples/        # one *.sample.json per collection
└── scripts/
    └── init_db.js
```

---

## 4. Collections to Design (the canonical list)

Design every collection below. For EACH one provide: **Collection Name, Purpose, Complete Schema, Field Names, Data Types, Required Fields, Optional Fields, Validation Rules, Relationships, References, Indexes, Retention Policy.**

### Domain A — User Management
- `users` — accounts (username, email, password_hash, status, mfa_enabled).
- `roles` — role definitions (admin, analyst, viewer, etc.).
- `permissions` — granular permission catalog.
- `login_history` — login events (ip, user_agent, success, geo).
- `analyst_profiles` — analyst-specific metadata (specialties, shift, workload).

### Domain B — Attack Sessions
- `attack_sessions` — core telemetry: `session_id`, `source_ip`, `destination_service`, `protocol`, `start_time`, `end_time`, `duration`, `commands_executed[]`, `files_accessed[]`, `credentials_attempted[]`, `session_timeline[]`, `session_status`, honeypot source (cowrie/dionaea/honeyd).

### Domain C — Threat Actors
- `threat_actors` — `attacker_profile`, `classification`, `risk_score`, `reputation_score`, `country`, `asn`, `isp`, `threat_history[]`, references to historical sessions.

### Domain D — Threat Intelligence
- `threat_intel` — enrichment results: `virustotal`, `abuseipdb`, `shodan`, `otx`, `geoip`, `reputation_data`, `threat_feeds[]`, `enrichment_history[]`. Keyed by IP/indicator.

### Domain E — MITRE ATT&CK Mapping
- `mitre_mappings` — `technique_id`, `technique_name`, `tactic`, `description`, `confidence_score`, `related_session`, `detection_evidence[]`.

### Domain F — Autonomous Response Engine
- `response_actions` — `threat_score`, `risk_level`, `automated_decision`, action type (`block`/`redirect`/`isolate`/`tarpit`), `response_history[]`, `decision_logs[]`.

### Domain G — Alerts
- `alerts` — `alert_type`, `severity`, `source`, `related_session`, `notification_status`, `delivery_tracking[]`.

### Domain H — Reports
- `reports` — `report_type` (daily/weekly/incident/executive), `generated_pdf_ref`, `report_metadata`, generation timestamps.

### Domain I — Attacker Digital Twin
- `digital_twins` — `digital_twin_id`, `attacker_id`, `behavioral_fingerprint`, `similarity_scores[]`, `historical_sessions[]`, `preferred_tools[]`, `preferred_protocols[]`, `preferred_targets[]`, `activity_patterns`, `operating_hours`, `geographic_patterns`, `mitre_techniques_used[]`, `risk_evolution[]`, `behavioral_trends[]`, `session_correlations[]`. Must support cross-session tracking, similarity analysis, and long-term behavioral evolution.

### Domain J — Deception Engine
- `deception_profiles`
- `environment_templates`
- `generated_environments`
- `active_environments`
- `fake_servers`
- `fake_databases`
- `fake_filesystems`
- `fake_credentials`
- `fake_documents`
- `honey_tokens`
- `canary_tokens`
> Must link environments to attacker profiles, support lifecycle (template → generated → active → retired), dynamic generation, and multiple deception layers.

### Domain K — Deception Effectiveness
- `deception_effectiveness` — `session_duration`, `commands_executed_count`, `files_accessed_count`, `credentials_attempted_count`, `services_explored_count`, `time_spent_in_environment`, `canary_trigger_events[]`, `lateral_movement_attempts`, `engagement_metrics`, `deception_success_score`, `historical_effectiveness_trends[]`.

### Domain L — AI SOC Analyst
- `ai_analyst_outputs` — `attack_explanation`, `session_summary`, `mitre_explanation`, `risk_explanation`, `explain_why`, `recommended_responses[]`, `generated_insights`, `analyst_notes[]`, `incident_report_ref`, `executive_summary`, `ai_confidence_score`, `analyst_feedback[]`. Support multiple outputs per session, confidence tracking, timestamps, and an analyst review workflow (`status`: generated → reviewed → approved/rejected).

### Domain M — AI Insights
- `ai_insights` — `predicted_next_attack_step`, `threat_predictions[]`, `campaign_detection_results[]`, `anomaly_detection_results[]`, `behavioral_predictions[]`, `ai_confidence_score`.

### Domain N — Attack Campaign Detection
- `attack_campaigns` — `campaign_id`, `campaign_name`, `related_attackers[]`, `related_sessions[]`, `shared_behaviors[]`, `shared_mitre_techniques[]`, `shared_infrastructure[]`, `campaign_confidence_score`.

---

## 5. Schema Authoring Rules (apply to every collection)

- Primary key: keep Mongo `_id` as `ObjectId`; add a human-readable business key where the spec names one (`session_id`, `digital_twin_id`, `campaign_id`) as a separate unique-indexed field.
- Timestamps: `created_at`, `updated_at` (UTC `date`), plus domain-specific ones (`start_time`, etc.).
- Enums: declare allowed values in the validator (e.g. `protocol ∈ [ssh, telnet, http, https, ftp, smb, rdp, other]`, `session_status ∈ [active, closed, timed_out, terminated]`, `severity ∈ [info, low, medium, high, critical]`).
- Numeric ranges: scores (`risk_score`, `reputation_score`, `confidence_score`, `deception_success_score`) constrained to documented ranges (state whether 0–100 or 0–1 and be consistent).
- Relationships: reference by stored business key AND/OR `ObjectId`; state which you chose and why (embed for bounded/owned data, reference for shared/large data).
- Required vs optional: explicitly mark `required` arrays in each `$jsonSchema`.
- Include `additionalProperties: false` on top-level objects unless a field is intentionally open (note it).

---

## 6. Cross-Cutting Documentation Requirements

For the doc deliverables, make sure to cover:
- **Relationship diagram** (Mermaid `erDiagram`): sessions ↔ threat_actors ↔ digital_twins ↔ mitre_mappings ↔ campaigns ↔ threat_intel ↔ deception envs ↔ effectiveness ↔ ai outputs ↔ alerts ↔ reports ↔ users.
- **Data flow diagram**: honeypots → ingest queue → `attack_sessions` → enrichment (`threat_intel`) → MITRE mapping → digital twin update → response engine → alerts → AI analyst → reports → dashboards.
- **Indexing strategy**: at minimum index `source_ip`, `session_id`, time ranges, `risk_score`, `technique_id`, `campaign_id`, and compound indexes for the dashboard queries; include TTL indexes for raw/ephemeral data.
- **Dashboards the DB must serve**: Live Dashboard, Real-Time Attack Feed, Threat Actor Profiles, Digital Twin Dashboard, MITRE ATT&CK Dashboard, Deception Center, AI SOC Analyst Dashboard, Reports Dashboard, Threat Intelligence Dashboard — list the key query/aggregation each one needs and confirm the indexes support it.
- **Security**: RBAC mapping to the `roles`/`permissions` collections, encryption at rest + TLS in transit, field-level encryption for credentials/PII, audit logging, least-privilege DB users.
- **Scalability**: candidate shard keys per high-volume collection (e.g. hashed `source_ip` or `{source_ip, start_time}` for `attack_sessions`), and why; capped collections for the live feed if appropriate.
- **Retention**: per-collection TTL/tiering — raw sessions hot 30–90d then archived, profiles/twins/campaigns retained long-term, enrichment cached with refresh windows, audit/login history per compliance.
- **Backup**: snapshot cadence, oplog/PITR, off-site copies, periodic restore tests.
- **Elasticsearch**: which fields/collections get mirrored to ES, the sync method (change streams / Monstache-style connector), and example ES mappings for `attack_sessions` and `threat_actors`.
- **Production deployment**: replica-set topology, node sizing for the stated load, monitoring (metrics + alerts), and a hardening checklist.

---

## 7. Execution Phases (Claude Code follows this order)

**Phase 1 — Scaffold & Inventory**
Create the folder tree, `README.md`, `docs/01_architecture_overview.md`, and `docs/02_collection_list.md` (full table). Pause.

**Phase 2 — Core domains (A–H)**
Schemas + Mongoose models + sample docs for User Management, Attack Sessions, Threat Actors, Threat Intelligence, MITRE, Response Engine, Alerts, Reports. Pause.

**Phase 3 — Advanced domains (I–N)**
Digital Twin, Deception Engine (all 11 collections), Deception Effectiveness, AI SOC Analyst, AI Insights, Campaign Detection. Pause.

**Phase 4 — Cross-cutting docs**
Diagrams (03, 04, 12), indexing (05), security (06), scalability (07), retention (08), backup (09), Elasticsearch (10), deployment (11). Pause.

**Phase 5 — Init script & validation**
Write `scripts/init_db.js`; verify every sample validates against its schema; produce a final checklist mapping each Acceptance Criterion to the file that satisfies it.

---

## 8. Acceptance Criteria (self-check before declaring done)

- [ ] Every collection in §4 has a `schemas/*.schema.json`, a `models/*.model.js`, and a `samples/*.sample.json`.
- [ ] Every sample document validates against its own `$jsonSchema`.
- [ ] All 17 deliverables in §2 exist at the paths in §3.
- [ ] Field naming, ID strategy, and timestamps are consistent across all files.
- [ ] Relationship + data-flow + final architecture diagrams render as valid Mermaid.
- [ ] Indexing doc proves each named dashboard query is index-supported.
- [ ] Retention, backup, scalability, security, ES, and deployment docs are each present and specific (no generic filler).
- [ ] `scripts/init_db.js` runs in `mongosh` and creates every collection with validator + indexes.
- [ ] The design plausibly handles thousands of sessions/day with a documented sharding + tiering plan.

---

## 9. Quick-start one-liner (paste into Claude Code)

> "Read `PROMPT.md`. Execute Phase 1 only: create the folder tree, README, architecture overview, and the full collection-list table. Then stop and show me the files."
