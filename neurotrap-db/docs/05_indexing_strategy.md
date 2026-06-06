# 05 · Indexing Strategy

Indexes are created by `scripts/init_db.js` and declared on each Mongoose model.
This doc lists them per collection, the rationale, and proves each named
dashboard query is index-supported.

## Per-collection indexes

| Collection | Index | Type | Rationale |
|------------|-------|------|-----------|
| users | `{user_id:1}`, `{email:1}` | unique | login + lookup |
| | `{status:1}` | — | filter disabled/locked |
| roles | `{role_id:1}` | unique | RBAC resolution |
| permissions | `{permission_id:1}` unique, `{resource:1,action:1}` | — | RBAC resolution |
| login_history | `{user_ref:1,created_at:-1}`, `{ip:1,created_at:-1}` | — | audit timelines |
| | `{created_at:1}` | **TTL 365d** | compliance expiry |
| analyst_profiles | `{user_ref:1}` unique, `{shift:1,'workload.open_cases':1}` | — | assignment by least load |
| **attack_sessions** | `{session_id:1}` | unique | business key |
| | `{source_ip:1,start_time:-1}` | compound | actor timeline / feed |
| | `{session_status:1,start_time:-1}` | compound | live-session dashboard |
| | `{risk_score:-1}` | — | top-threat sort |
| | `{threat_actor_ref:1}` | — | actor → sessions |
| | `{protocol:1,honeypot_source:1}` | compound | sensor breakdown |
| threat_actors | `{actor_id:1}` unique, `{primary_ip:1}`, `{known_ips:1}` | — | profile lookup by IP |
| | `{risk_score:-1}`, `{classification:1,last_seen:-1}` | — | threat-actor board |
| threat_intel | `{indicator:1}` unique | — | cache key |
| | `{expires_at:1}` | **TTL 0** | cache refresh |
| mitre_mappings | `{technique_id:1}`, `{related_session:1}`, `{tactic:1,technique_id:1}` | — | ATT&CK dashboard |
| response_actions | `{related_session:1}`, `{target_ip:1,status:1}`, `{status:1,created_at:-1}` | — | active blocks |
| alerts | `{severity:1,status:1,created_at:-1}`, `{related_session:1}`, `{status:1,created_at:-1}` | — | alert queue |
| reports | `{report_type:1,period_start:-1}`, `{status:1,generated_at:-1}` | — | reports list |
| digital_twins | `{digital_twin_id:1}` unique, `{attacker_id:1}` unique | — | twin lookup |
| | `{'behavioral_fingerprint.hash':1}`, `{mitre_techniques_used:1}`, `{last_updated:-1}` | — | similarity bucketing |
| deception_profiles | `{profile_id:1}` unique, `{target_tier:1,target_intent:1,is_active:1}` | — | profile selection |
| environment_templates | `{template_id:1}` unique, `{industry:1,is_active:1}` | — | template selection |
| generated_environments | `{environment_id:1}` unique, `{status:1,generated_at:-1}`, `{target_actor_ref:1}` | — | lifecycle |
| active_environments | `{environment_id:1}` unique, `{status:1,started_at:-1}`, `{session_ref:1}` | — | live deception |
| | `{expires_at:1}` | **TTL 0** | teardown |
| fake_servers/databases/filesystems/credentials/documents | `{<id>:1}` unique, `{environment_ref:1}` | — | env component fetch |
| fake_credentials | `{use_detected:1}` | — | burned-credential alerting |
| honey_tokens / canary_tokens | `{token_id:1}` unique, `{environment_ref:1}`, `{triggered:1}` | — | trigger monitoring |
| deception_effectiveness | `{effectiveness_id:1}` unique, `{environment_ref:1}`, `{session_ref:1}`, `{deception_success_score:-1}` | — | effectiveness board |
| ai_analyst_outputs | `{output_id:1}` unique, `{related_session:1,generated_at:-1}`, `{review_status:1}` | — | review queue |
| ai_insights | `{insight_id:1}` unique, `{'scope.type':1,'scope.ref':1,generated_at:-1}` | — | scoped insight fetch |
| attack_campaigns | `{campaign_id:1}` unique, `{status:1,last_seen:-1}`, `{related_attackers:1}`, `{shared_mitre_techniques:1}` | — | campaign board |

## Dashboard query → index proof

| Dashboard | Query / aggregation | Supporting index |
|-----------|---------------------|------------------|
| **Live Dashboard** | active sessions, last 5m | `attack_sessions {session_status:1,start_time:-1}` |
| **Real-Time Attack Feed** | newest sessions desc | `attack_sessions {source_ip:1,start_time:-1}` / `{session_status:1,start_time:-1}` |
| **Threat Actor Profiles** | top actors by risk | `threat_actors {risk_score:-1}`; lookup `{primary_ip:1}` |
| **Digital Twin Dashboard** | twin by actor, similar twins | `digital_twins {attacker_id:1}`, `{'behavioral_fingerprint.hash':1}` |
| **MITRE ATT&CK Dashboard** | counts by technique/tactic | `mitre_mappings {tactic:1,technique_id:1}` |
| **Deception Center** | active envs + effectiveness | `active_environments {status:1,started_at:-1}`, `deception_effectiveness {deception_success_score:-1}` |
| **AI SOC Analyst Dashboard** | pending review queue | `ai_analyst_outputs {review_status:1}`, `{related_session:1,generated_at:-1}` |
| **Reports Dashboard** | reports by type/period | `reports {report_type:1,period_start:-1}` |
| **Threat Intelligence Dashboard** | indicator lookup, worst reputation | `threat_intel {indicator:1}`, `{reputation_score:-1}` |
| **Alerts** | open critical alerts | `alerts {severity:1,status:1,created_at:-1}` |

## Sample `createIndex` commands

```js
db.attack_sessions.createIndex({ session_id: 1 }, { unique: true });
db.attack_sessions.createIndex({ source_ip: 1, start_time: -1 });
db.attack_sessions.createIndex({ session_status: 1, start_time: -1 });
db.attack_sessions.createIndex({ risk_score: -1 });
db.threat_intel.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.login_history.createIndex({ created_at: 1 }, { expireAfterSeconds: 31536000 });
db.active_environments.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.mitre_mappings.createIndex({ tactic: 1, technique_id: 1 });
```

(The complete set is applied programmatically in `scripts/init_db.js`.)
