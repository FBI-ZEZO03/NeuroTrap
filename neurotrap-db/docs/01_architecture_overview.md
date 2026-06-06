# 01 · Architecture Overview

## 1. Purpose

This document is the design contract for the NeuroTrap persistence layer. It
fixes the conventions every schema, model, and sample obeys so that 28
collections across 14 domains stay internally consistent.

NeuroTrap ingests attacker telemetry from honeypots in real time, enriches it
with threat-intel APIs, maps it to MITRE ATT&CK, builds persistent attacker
**Digital Twins**, drives an **adaptive deception** layer, scores deception
**effectiveness**, and produces **AI SOC analyst** outputs and reports. MongoDB is
the system of record tying these together; Elasticsearch mirrors the hot,
search-heavy collections.

## 2. Data architecture at a glance

```
 Honeypots (Cowrie · Dionaea · OpenCanary · Galah)
        │  raw events
        ▼
 Ingest queue ──► attack_sessions ──► threat_intel (enrich) ──► mitre_mappings
        │                │                    │                      │
        │                ▼                    ▼                      ▼
        │           threat_actors ◄────── digital_twins ◄──── attack_campaigns
        │                │
        ▼                ▼
 response_actions ◄── (threat_score)        deception_* (profiles→generated→active)
        │                                        │
        ▼                                        ▼
     alerts ──► ai_analyst_outputs ──► reports          deception_effectiveness
        │            │
        ▼            ▼
   users / roles / permissions (RBAC)        ai_insights
```

Three logical data tiers:

| Tier | Collections | Behaviour |
|------|-------------|-----------|
| **Hot** (operational) | `attack_sessions`, `alerts`, `response_actions`, `active_environments`, live feed | High write rate, TTL/tiering, mirrored to ES |
| **Warm** (analytical) | `threat_actors`, `digital_twins`, `attack_campaigns`, `mitre_mappings`, `deception_effectiveness`, `ai_*` | Updated continuously, retained long-term |
| **Cold** (reference / archive) | `threat_intel` cache, `reports`, `login_history`, archived sessions | Refresh windows / compliance retention / object-store archival |

## 3. Naming & ID conventions

- **Primary key:** every document keeps Mongo's `_id` as an `ObjectId`.
- **Business key:** where the spec names a human-readable identifier
  (`session_id`, `digital_twin_id`, `campaign_id`, `report_id`, `alert_id`,
  `action_id`, `user_id`, `actor_id`, `template_id`, `environment_id`,
  `output_id`, `insight_id`, `mapping_id`), it is stored as a **string** field
  with a **unique index**, formatted as a stable, sortable, prefixed ULID-style
  token, e.g. `sess_01J9...`, `dt_01J9...`, `camp_01J9...`.
- **Field names:** `snake_case` only.
- **Timestamps:** `created_at`, `updated_at` are required UTC `date` on every
  collection. Domain times use explicit names (`start_time`, `end_time`,
  `last_seen`, `generated_at`, `expires_at`).

## 4. Type & enum conventions

`$jsonSchema` uses `bsonType`. Canonical mappings:

| Concept | bsonType | Notes |
|---------|----------|-------|
| Identifier | `objectId` / `string` | `_id` vs. business key |
| Timestamp | `date` | always UTC |
| IP address | `string` | validated by `pattern` (IPv4/IPv6) |
| Score 0–100 | `int` or `double` | `minimum:0, maximum:100` |
| Score 0–1 | `double` | `minimum:0, maximum:1` |
| Money/large counts | `long` | — |

**Shared enums** (declared in every validator that uses them):

- `protocol ∈ [ssh, telnet, http, https, ftp, smb, rdp, mysql, mssql, snmp, vnc, sip, other]`
- `session_status ∈ [active, closed, timed_out, terminated]`
- `severity ∈ [info, low, medium, high, critical]`
- `risk_level ∈ [low, medium, high, critical]`
- `honeypot_source ∈ [cowrie, dionaea, opencanary, galah, other]`
- `action_type ∈ [block, redirect, isolate, tarpit, monitor]`
- `report_type ∈ [daily, weekly, incident, executive]`
- `review_status ∈ [generated, reviewed, approved, rejected]`
- `environment_status ∈ [template, generated, active, retired]`

## 5. Score-range registry (single source of truth)

| Field | Range | Meaning |
|-------|-------|---------|
| `risk_score` | 0–100 | composite hostility of a session/actor (higher = worse) |
| `reputation_score` | 0–100 | external maliciousness (0 = benign, 100 = known-malicious) |
| `threat_score` | 0–100 | response-engine input; matrix at 40 / 70 / 90 |
| `deception_success_score` | 0–100 | how well an environment engaged the attacker |
| `confidence_score` | 0–1 | model/mapping confidence |
| `ai_confidence_score` | 0–1 | LLM/insight confidence |
| `similarity_score` | 0–1 | twin-to-twin / session-to-session similarity |
| `campaign_confidence_score` | 0–1 | clustering confidence a campaign is real |

## 6. Embed vs. reference policy

- **Embed** bounded, owned, read-with-parent data: a session's
  `commands_executed[]`, `session_timeline[]`, a report's `report_metadata`.
- **Reference** (by business key + `ObjectId`) shared, large, or independently
  queried data: `attack_sessions.threat_actor_ref → threat_actors`,
  `digital_twins.historical_sessions[] → attack_sessions`,
  `mitre_mappings.related_session → attack_sessions`. Each schema states its
  choice in the field `description`.

## 7. Cross-cutting guarantees

- Validation: `validationLevel: "strict"`, `validationAction: "error"` on hot
  collections; `"warn"` on enrichment caches where partial third-party data is
  expected. (See `init_db.js`.)
- Security: RBAC via `users`/`roles`/`permissions`; field-level encryption for
  `password_hash`, `credentials_attempted[]`, `fake_credentials`, and PII; audit
  via `login_history` + a change-stream audit sink. (See `06_security…`.)
- Scale: shard keys per high-volume collection, TTL on raw/ephemeral data, ES
  mirror for search. (See `07_scalability…`, `08_retention…`, `10_elasticsearch…`.)
