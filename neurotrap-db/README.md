# NeuroTrap — Database Architecture (`neurotrap-db`)

Persistence layer for **NeuroTrap CADN**, an AI-powered cyber **deception / honeypot /
threat-analysis** platform for a defensive SOC. This repo defines how *collected*
attacker telemetry is stored, validated, correlated, and surfaced — schemas,
Mongoose models, sample documents, the full operational doc set, and a one-shot
database initialization script.

> Defensive-security scope only: honeypot capture, threat-intel enrichment, MITRE
> ATT&CK mapping, attacker profiling/Digital Twins, deception orchestration, and
> SOC reporting. No offensive tooling.

## Stack

| Layer | Choice |
|-------|--------|
| Primary store | MongoDB 7.x (replica set, `$jsonSchema` validation) |
| Canonical model code | Mongoose (Node.js) |
| Search / aggregation | Elasticsearch 8.x (mirror of hot collections) |
| Scale target | thousands of attack sessions/day, multi-year profile retention, hot/warm/cold tiering |

## Repository layout

```
neurotrap-db/
├── README.md                     # this file
├── PROMPT.md                     # the executable build spec
├── docs/                         # 12 architecture & operations docs (01–12)
├── schemas/    <collection>.schema.json   # one MongoDB $jsonSchema validator per collection
├── models/     <collection>.model.js      # one Mongoose model per collection
├── samples/    <collection>.sample.json   # ≥1 realistic sample per collection
└── scripts/
    ├── init_db.js                # mongosh: create every collection + validator + indexes
    └── validate_samples.py       # checks each sample against its $jsonSchema
```

## Collection inventory

28 collections across 14 domains (A–N). See [`docs/02_collection_list.md`](docs/02_collection_list.md)
for the full table (purpose, write rate, retention tier) and
[`docs/01_architecture_overview.md`](docs/01_architecture_overview.md) for the
design conventions that every file follows.

## Running `init_db.js`

```bash
# 1. Point mongosh at your replica set
export MONGO_URI="mongodb://localhost:27017/neurotrap?replicaSet=rs0"

# 2. Create every collection with its validator and indexes
mongosh "$MONGO_URI" scripts/init_db.js

# 3. (optional) verify the sample documents validate against their schemas
python scripts/validate_samples.py
```

`init_db.js` is idempotent: it uses `createCollection` with `collMod` fallback,
so re-running it updates validators/indexes without dropping data.

## Conventions (enforced everywhere)

- IDs: Mongo `_id` is `ObjectId`; human-readable business keys (`session_id`,
  `digital_twin_id`, `campaign_id`, …) are separate unique-indexed string fields.
- Field names: `snake_case`. Timestamps: `created_at` / `updated_at` (UTC `date`),
  plus domain-specific times (`start_time`, …).
- Score ranges (consistent across the repo): `risk_score`, `reputation_score`,
  `threat_score`, `deception_success_score` ∈ **0–100**; `confidence_score`,
  `ai_confidence_score`, `similarity_score`, `campaign_confidence_score` ∈ **0–1**.
- Validators set `additionalProperties: false` on top-level objects unless a field
  is intentionally open (always noted in the schema `description`).

## Honeypot sources

`honeypot_source ∈ [cowrie, dionaea, opencanary, galah, other]`.
Honeyd was **decommissioned** from the platform (unmaintained, Python-2 only) and
replaced by **OpenCanary** (maintained multi-service sensor) and **Galah**
(LLM-powered web honeypot); the enum reflects the current sensor fleet.
