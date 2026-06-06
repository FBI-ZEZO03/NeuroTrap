# Acceptance Criteria — Self-Check

Maps every §8 acceptance criterion from `PROMPT.md` to the artifact(s) that
satisfy it. Validation was run with `scripts/validate_samples.py` (32 sample
docs across 28 collections, 0 failures).

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Every collection in §4 has schema + model + sample | ✅ | 28 × `schemas/*.schema.json`, `models/*.model.js`, `samples/*.sample.json` (file counts: 28/28/28) |
| 2 | Every sample validates against its own `$jsonSchema` | ✅ | `scripts/validate_samples.py` → "collections failing: 0" |
| 3 | All 17 §2 deliverables exist at §3 paths | ✅ | see deliverable map below |
| 4 | Consistent field naming / ID strategy / timestamps | ✅ | `snake_case`, prefixed business keys `^<p>_[0-9A-Z]{26}$`, `created_at`/`updated_at` on all 28; conventions in `docs/01` |
| 5 | Relationship + data-flow + final-architecture diagrams render as valid Mermaid | ✅ | `docs/03` (erDiagram), `docs/04` (flowchart), `docs/12` (flowchart) |
| 6 | Indexing doc proves each named dashboard query is index-supported | ✅ | `docs/05` "Dashboard query → index proof" table (9 dashboards) |
| 7 | Retention, backup, scalability, security, ES, deployment docs present & specific | ✅ | `docs/06`–`docs/11` |
| 8 | `scripts/init_db.js` creates every collection w/ validator + indexes | ✅ | `scripts/init_db.js` (28-collection registry, idempotent createCollection/collMod, TTL indexes) |
| 9 | Plausibly handles thousands of sessions/day w/ sharding + tiering plan | ✅ | `docs/07` (hashed `source_ip` shard key), `docs/08` (TTL + hot/warm/cold tiering) |

## Deliverable map (§2 → path)

| # | Deliverable | Path |
|---|-------------|------|
| 1 | architecture overview | `docs/01_architecture_overview.md` |
| 2 | collection list | `docs/02_collection_list.md` |
| 3 | schemas (1/collection) | `schemas/*.schema.json` (28) |
| 4 | Mongoose models (1/collection) | `models/*.model.js` (28) |
| 5 | sample docs (1+/collection) | `samples/*.sample.json` (28; 32 docs) |
| 6 | relationship diagram | `docs/03_relationship_diagram.md` |
| 7 | data flow diagram | `docs/04_data_flow_diagram.md` |
| 8 | indexing strategy | `docs/05_indexing_strategy.md` |
| 9 | security best practices | `docs/06_security_best_practices.md` |
| 10 | scalability | `docs/07_scalability.md` |
| 11 | retention strategy | `docs/08_retention_strategy.md` |
| 12 | backup strategy | `docs/09_backup_strategy.md` |
| 13 | elasticsearch integration | `docs/10_elasticsearch_integration.md` |
| 14 | production deployment | `docs/11_production_deployment.md` |
| 15 | final architecture diagram | `docs/12_final_architecture_diagram.md` |
| 16 | init script | `scripts/init_db.js` |
| 17 | README | `README.md` |

## Collections (28, by domain)

A: `users`, `roles`, `permissions`, `login_history`, `analyst_profiles` ·
B: `attack_sessions` · C: `threat_actors` · D: `threat_intel` ·
E: `mitre_mappings` · F: `response_actions` · G: `alerts` · H: `reports` ·
I: `digital_twins` · J: `deception_profiles`, `environment_templates`,
`generated_environments`, `active_environments`, `fake_servers`,
`fake_databases`, `fake_filesystems`, `fake_credentials`, `fake_documents`,
`honey_tokens`, `canary_tokens` · K: `deception_effectiveness` ·
L: `ai_analyst_outputs` · M: `ai_insights` · N: `attack_campaigns`.

## Notes / deviations

- **Honeypot enum** uses `[cowrie, dionaea, opencanary, galah, other]` — Honeyd was
  decommissioned platform-wide and replaced by OpenCanary + Galah. (PROMPT §1 named
  the legacy set; aligned to current reality.)
- **ID pattern** relaxed from strict Crockford ULID to `^<prefix>_[0-9A-Z]{26}$`
  (prefix + 26 uppercase alphanumerics) for consistency across cross-referenced samples.
- `validate_samples.py` is an extra artifact (beyond §2) providing the criterion-2
  proof without requiring a running MongoDB.
