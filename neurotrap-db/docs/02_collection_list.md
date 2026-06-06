# 02 · Collection Inventory

28 collections across 14 domains (A–N). Write rates assume the stated load of
**thousands of attack sessions/day**. Retention tier maps to the hot/warm/cold
model in `01_architecture_overview.md` and the rules in `08_retention_strategy.md`.

## Domain A — User Management

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `users` | SOC accounts: credentials, status, MFA | very low (admin changes) | warm (account lifetime) |
| `roles` | Role definitions (admin/analyst/viewer/…) | static | warm (config) |
| `permissions` | Granular permission catalog | static | warm (config) |
| `login_history` | Auth events: ip, user-agent, success, geo | low–medium (per login) | cold (365 d, compliance) |
| `analyst_profiles` | Analyst metadata: specialties, shift, workload | low | warm |

## Domain B — Attack Sessions

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `attack_sessions` | Core honeypot telemetry per session | **high** (1000s/day, many events each) | hot → archive (90 d TTL on raw, then cold) |

## Domain C — Threat Actors

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `threat_actors` | Persistent per-source attacker profile + history | medium (upsert per session) | warm (multi-year) |

## Domain D — Threat Intelligence

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `threat_intel` | Enrichment cache (VT, AbuseIPDB, Shodan, OTX, GeoIP) keyed by indicator | medium (per new/expired IP) | cold cache (refresh window 7–30 d) |

## Domain E — MITRE ATT&CK Mapping

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `mitre_mappings` | Technique mappings with evidence per session | high (several per session) | warm |

## Domain F — Autonomous Response Engine

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `response_actions` | Automated decisions + action history | medium | warm (audit value) |

## Domain G — Alerts

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `alerts` | Notifications with delivery tracking | medium–high | hot → 180 d then cold |

## Domain H — Reports

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `reports` | Generated daily/weekly/incident/executive reports + PDF refs | low | warm/cold (compliance) |

## Domain I — Attacker Digital Twin

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `digital_twins` | Cross-session behavioural replica + evolution | medium (upsert per session) | warm (multi-year) |

## Domain J — Deception Engine

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `deception_profiles` | Strategy profile mapping attacker type → deception plan | low | warm (config) |
| `environment_templates` | Reusable environment blueprints | low | warm (config) |
| `generated_environments` | Concrete environments instantiated from templates | medium | hot → retire |
| `active_environments` | Currently-live deception instances | medium (lifecycle churn) | hot (capped-ish, TTL on retired) |
| `fake_servers` | Decoy server definitions inside environments | medium | hot → retire |
| `fake_databases` | Decoy DB definitions + fabricated tables | medium | hot → retire |
| `fake_filesystems` | Decoy filesystem trees | medium | hot → retire |
| `fake_credentials` | Planted credentials (field-encrypted) | medium | hot → retire |
| `fake_documents` | Decoy documents/assets | medium | hot → retire |
| `honey_tokens` | Embedded honey tokens + trigger state | low–medium | warm (track triggers) |
| `canary_tokens` | Canarytokens + out-of-band trigger events | low–medium | warm (track triggers) |

## Domain K — Deception Effectiveness

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `deception_effectiveness` | Engagement metrics + success scoring per env/session | medium | warm |

## Domain L — AI SOC Analyst

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `ai_analyst_outputs` | LLM explanations/recommendations + review workflow | medium | warm |

## Domain M — AI Insights

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `ai_insights` | Predictions, campaign/anomaly/behaviour results | medium | warm |

## Domain N — Attack Campaign Detection

| Collection | Purpose | Est. write rate | Retention tier |
|------------|---------|-----------------|----------------|
| `attack_campaigns` | Correlated multi-actor/multi-session campaigns | low–medium | warm (multi-year) |

---

**Total: 28 collections.** Each has a `schemas/<name>.schema.json`,
`models/<name>.model.js`, and `samples/<name>.sample.json`. High-write
collections (`attack_sessions`, `mitre_mappings`, `alerts`) carry the heaviest
indexing and are first in line for sharding and ES mirroring.
