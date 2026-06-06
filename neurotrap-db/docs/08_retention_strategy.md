# 08 · Retention Strategy

Per-collection TTL, tiering, and archival. Hot/warm/cold map to
`01_architecture_overview.md`.

## Retention matrix

| Collection | Hot window | Then | Mechanism |
|------------|-----------|------|-----------|
| `attack_sessions` | 90 d (full detail) | archive to cold object store (Parquet/BSON dump), keep slim summary in `threat_actors.threat_history` | scheduled archival job + post-archive purge |
| `mitre_mappings` | 90 d | archived with parent sessions | archival job |
| `alerts` | 180 d | cold archive | archival job |
| `login_history` | 365 d | **delete** | TTL index `{created_at:1}` exp 31536000 |
| `threat_intel` | until `expires_at` (7–30 d) | **delete** (re-fetched on demand) | TTL index `{expires_at:1}` exp 0 |
| `active_environments` | until `expires_at` | **delete** (instance torn down) | TTL index `{expires_at:1}` exp 0 |
| `generated_environments` | until retired + 30 d | cold archive | archival job (status=retired) |
| `fake_*` (servers/db/fs/creds/docs) | life of environment | purge with environment | cascade on env retire |
| `honey_tokens`, `canary_tokens` | retained while active; triggers kept 2 y | cold archive | archival job |
| `threat_actors` | **retained long-term** (multi-year) | — | no TTL |
| `digital_twins` | **retained long-term** | — | no TTL |
| `attack_campaigns` | **retained long-term** | — | no TTL |
| `deception_effectiveness` | 1 y | aggregate then archive | rollup job |
| `ai_analyst_outputs` | 1 y | archive (keep approved incident outputs longer) | archival job |
| `ai_insights` | 180 d | delete (regenerable) | TTL/job |
| `reports` | per compliance (≥ 3 y for executive/incident) | cold archive; PDFs in object store with lifecycle policy | object-store lifecycle |
| `users`, `roles`, `permissions`, `analyst_profiles` | account/config lifetime | — | manual |

## Tiering mechanics

1. **Hot (MongoDB shards):** indexed, fast, sharded. Only recent/active data.
2. **Cold (object store, e.g. S3):** archived sessions/mappings as compressed
   BSON/Parquet, partitioned `year/month/day`. Queryable via Athena/Spark or
   re-import for investigations.
3. **Summaries stay hot:** before purging a raw session, its rollup is written to
   `threat_actors.threat_history[]` and `digital_twins.risk_evolution[]` so
   long-term profiles survive without the bulky raw events.

## TTL indexes (authoritative list)

```js
db.login_history.createIndex({ created_at: 1 }, { expireAfterSeconds: 31536000 }); // 365d
db.threat_intel.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });          // on expiry
db.active_environments.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });   // on teardown
```

Archival/purge of `attack_sessions`, `mitre_mappings`, `alerts`, etc. is handled
by a scheduled job (not TTL) so data is **copied to cold storage before deletion**.
