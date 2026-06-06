# 03 · Relationship Diagram

Entity relationships across the 28 collections. Relationships are by **business
key** (string) unless noted; cardinality reflects the embed/reference policy in
`01_architecture_overview.md`.

```mermaid
erDiagram
    users ||--o{ login_history : "logs"
    users ||--o| analyst_profiles : "has"
    users }o--o{ roles : "role_refs"
    roles }o--o{ permissions : "permission_refs"

    attack_sessions }o--|| threat_actors : "threat_actor_ref"
    attack_sessions }o--o| digital_twins : "digital_twin_ref"
    attack_sessions ||--o{ mitre_mappings : "related_session"
    attack_sessions ||--o{ response_actions : "related_session"
    attack_sessions ||--o{ alerts : "related_session"
    attack_sessions ||--o{ ai_analyst_outputs : "related_session"
    attack_sessions }o--o| active_environments : "engaged_in"

    threat_actors ||--o| digital_twins : "digital_twin_ref"
    threat_actors }o--o{ threat_intel : "enriched_by_ip"
    threat_actors }o--o{ attack_campaigns : "related_attackers"

    attack_sessions }o--o{ attack_campaigns : "related_sessions"
    digital_twins ||--o{ ai_insights : "scoped_to"

    deception_profiles }o--o{ environment_templates : "template_refs"
    environment_templates ||--o{ generated_environments : "template_ref"
    deception_profiles ||--o{ generated_environments : "profile_ref"
    generated_environments ||--o| active_environments : "promoted_to"
    generated_environments ||--o{ fake_servers : "server_refs"
    generated_environments ||--o{ fake_databases : "database_refs"
    generated_environments ||--o{ fake_filesystems : "filesystem_refs"
    generated_environments ||--o{ fake_credentials : "credential_refs"
    generated_environments ||--o{ fake_documents : "document_refs"
    generated_environments ||--o{ honey_tokens : "token_refs"
    generated_environments ||--o{ canary_tokens : "token_refs"
    fake_servers ||--o{ fake_databases : "hosts"
    fake_servers ||--o{ fake_filesystems : "hosts"
    fake_documents }o--o| canary_tokens : "embedded_token_ref"

    active_environments ||--o{ deception_effectiveness : "measured_by"
    attack_sessions ||--o{ deception_effectiveness : "session_ref"

    ai_analyst_outputs }o--o| reports : "incident_report_ref"
    alerts }o--o| users : "assigned_to"
    response_actions }o--o| users : "decided_by"
```

## Key relationship notes

| Relationship | Type | Why |
|--------------|------|-----|
| `attack_sessions → threat_actors` | reference | actors are shared across many sessions and queried independently |
| session child arrays (`commands/files/creds/timeline`) | embed | bounded, owned, read with the session |
| `threat_actors ↔ digital_twins` | 1:1 reference | a twin is the analytic model of one actor; unique `attacker_id` index |
| `generated_environments → fake_*` | reference arrays | components are large and independently lifecycle-managed |
| `roles ↔ permissions`, `users ↔ roles` | many-to-many reference | RBAC resolution at auth time |
| `mitre_mappings → attack_sessions` | reference (1 session : many mappings) | techniques queried by id across sessions |
