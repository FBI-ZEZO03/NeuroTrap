/**
 * init_db.js — NeuroTrap database bootstrap (run with mongosh).
 *
 *   mongosh "mongodb://localhost:27017/neurotrap?replicaSet=rs0" scripts/init_db.js
 *
 * For every collection it:
 *   1. loads schemas/<name>.schema.json as the $jsonSchema validator,
 *   2. creates the collection with that validator (or updates it via collMod
 *      if it already exists — idempotent, never drops data),
 *   3. builds the indexes (incl. TTL) from the registry below.
 *
 * Requires running as a script file so Node's fs/path modules are available
 * (mongosh exposes them in script mode).
 */
const fs = require('fs');
const path = require('path');

// __dirname is provided when run as `mongosh init_db.js`; fall back to a path
// relative to the working directory if the runtime doesn't define it.
const HERE = (typeof __dirname !== 'undefined') ? __dirname : path.join(process.cwd(), 'scripts');
const SCHEMA_DIR = path.resolve(HERE, '..', 'schemas');

// validationAction per collection: 'error' (default, strict) or 'warn'.
const WARN_ONLY = new Set(['threat_intel']); // tolerate partial 3rd-party payloads

// Index registry: [keys, options].
const INDEXES = {
  users: [[{ user_id: 1 }, { unique: true }], [{ email: 1 }, { unique: true }], [{ status: 1 }, {}]],
  roles: [[{ role_id: 1 }, { unique: true }]],
  permissions: [[{ permission_id: 1 }, { unique: true }], [{ resource: 1, action: 1 }, {}]],
  login_history: [[{ user_ref: 1, created_at: -1 }, {}], [{ ip: 1, created_at: -1 }, {}], [{ created_at: 1 }, { expireAfterSeconds: 31536000 }]],
  analyst_profiles: [[{ user_ref: 1 }, { unique: true }], [{ shift: 1, 'workload.open_cases': 1 }, {}]],
  attack_sessions: [
    [{ session_id: 1 }, { unique: true }], [{ source_ip: 1, start_time: -1 }, {}],
    [{ session_status: 1, start_time: -1 }, {}], [{ risk_score: -1 }, {}],
    [{ threat_actor_ref: 1 }, {}], [{ protocol: 1, honeypot_source: 1 }, {}]
  ],
  threat_actors: [[{ actor_id: 1 }, { unique: true }], [{ primary_ip: 1 }, {}], [{ known_ips: 1 }, {}], [{ risk_score: -1 }, {}], [{ classification: 1, last_seen: -1 }, {}]],
  threat_intel: [[{ indicator: 1 }, { unique: true }], [{ reputation_score: -1 }, {}], [{ expires_at: 1 }, { expireAfterSeconds: 0 }]],
  mitre_mappings: [[{ mapping_id: 1 }, { unique: true }], [{ technique_id: 1 }, {}], [{ related_session: 1 }, {}], [{ tactic: 1, technique_id: 1 }, {}]],
  response_actions: [[{ action_id: 1 }, { unique: true }], [{ related_session: 1 }, {}], [{ target_ip: 1, status: 1 }, {}], [{ status: 1, created_at: -1 }, {}]],
  alerts: [[{ alert_id: 1 }, { unique: true }], [{ severity: 1, status: 1, created_at: -1 }, {}], [{ related_session: 1 }, {}], [{ status: 1, created_at: -1 }, {}]],
  reports: [[{ report_id: 1 }, { unique: true }], [{ report_type: 1, period_start: -1 }, {}], [{ status: 1, generated_at: -1 }, {}]],
  digital_twins: [[{ digital_twin_id: 1 }, { unique: true }], [{ attacker_id: 1 }, { unique: true }], [{ 'behavioral_fingerprint.hash': 1 }, {}], [{ mitre_techniques_used: 1 }, {}], [{ last_updated: -1 }, {}]],
  deception_profiles: [[{ profile_id: 1 }, { unique: true }], [{ target_tier: 1, target_intent: 1, is_active: 1 }, {}]],
  environment_templates: [[{ template_id: 1 }, { unique: true }], [{ industry: 1, is_active: 1 }, {}]],
  generated_environments: [[{ environment_id: 1 }, { unique: true }], [{ status: 1, generated_at: -1 }, {}], [{ target_actor_ref: 1 }, {}]],
  active_environments: [[{ environment_id: 1 }, { unique: true }], [{ status: 1, started_at: -1 }, {}], [{ session_ref: 1 }, {}], [{ expires_at: 1 }, { expireAfterSeconds: 0 }]],
  fake_servers: [[{ server_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}]],
  fake_databases: [[{ database_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}]],
  fake_filesystems: [[{ filesystem_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}]],
  fake_credentials: [[{ credential_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}], [{ use_detected: 1 }, {}]],
  fake_documents: [[{ document_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}]],
  honey_tokens: [[{ token_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}], [{ triggered: 1 }, {}]],
  canary_tokens: [[{ token_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}], [{ triggered: 1, active: 1 }, {}]],
  deception_effectiveness: [[{ effectiveness_id: 1 }, { unique: true }], [{ environment_ref: 1 }, {}], [{ session_ref: 1 }, {}], [{ deception_success_score: -1 }, {}]],
  ai_analyst_outputs: [[{ output_id: 1 }, { unique: true }], [{ related_session: 1, generated_at: -1 }, {}], [{ review_status: 1 }, {}]],
  ai_insights: [[{ insight_id: 1 }, { unique: true }], [{ 'scope.type': 1, 'scope.ref': 1, generated_at: -1 }, {}]],
  attack_campaigns: [[{ campaign_id: 1 }, { unique: true }], [{ status: 1, last_seen: -1 }, {}], [{ related_attackers: 1 }, {}], [{ shared_mitre_techniques: 1 }, {}]]
};

const collections = Object.keys(INDEXES);
print(`NeuroTrap init_db: ${collections.length} collections on db '${db.getName()}'`);

let created = 0, updated = 0, indexed = 0;

for (const name of collections) {
  const schemaPath = path.join(SCHEMA_DIR, `${name}.schema.json`);
  const validator = JSON.parse(fs.readFileSync(schemaPath, 'utf8')); // { $jsonSchema: {...} }
  const validationAction = WARN_ONLY.has(name) ? 'warn' : 'error';

  const exists = db.getCollectionNames().includes(name);
  if (!exists) {
    db.createCollection(name, { validator, validationLevel: 'strict', validationAction });
    created++;
    print(`  + created ${name} (validationAction=${validationAction})`);
  } else {
    db.runCommand({ collMod: name, validator, validationLevel: 'strict', validationAction });
    updated++;
    print(`  ~ updated validator on ${name}`);
  }

  for (const [keys, opts] of INDEXES[name]) {
    db.getCollection(name).createIndex(keys, opts);
    indexed++;
  }
}

print(`\nDone. created=${created} updated=${updated} indexes_ensured=${indexed}`);
print('Next: seed reference data (roles, permissions, environment_templates, deception_profiles).');
