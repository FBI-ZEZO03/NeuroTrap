# 06 · Security Best Practices

## 1. Authentication & RBAC

- App users authenticate against `users` (Argon2id `password_hash`, optional TOTP
  `mfa_secret`). Authorization resolves `users.role_refs → roles.permission_refs →
  permissions` at request time and caches the effective permission set per session.
- Permission model is `resource:action` (e.g. `sessions:read`, `response:execute`).
  Map application routes to required permissions; deny by default.

| Role | Effective permissions (summary) |
|------|----------------------------------|
| `role_admin` | all `*:*` incl. `users:write`, `roles:write` |
| `role_analyst` | `sessions:read`, `actors:read`, `intel:read`, `mitre:read`, `response:execute`, `ai:review`, `reports:read` |
| `role_viewer` | `*:read` only |

## 2. Database-level users (least privilege)

| DB user | Role | Scope |
|---------|------|-------|
| `neurotrap_ingest` | custom: `insert/update` on `attack_sessions`, `mitre_mappings`, `threat_intel` | honeypot/enrichment writers |
| `neurotrap_app` | `readWrite` on app collections, **no** `dropDatabase`/`createUser` | API server |
| `neurotrap_ro` | `read` only | dashboards / BI / ES connector |
| `neurotrap_admin` | `dbOwner` | migrations only, MFA-gated, break-glass |

Never use the cluster root account from the application.

## 3. Encryption

- **In transit:** TLS 1.2+ required for all client and intra-replica-set traffic
  (`net.tls.mode: requireTLS`, `--clusterAuthMode x509`).
- **At rest:** WiredTiger encryption-at-rest (KMIP/cloud KMS key) on every node.
- **Field-level (CSFLE / Queryable Encryption):** encrypt sensitive fields with a
  customer master key in a KMS, so they are ciphertext even to DB admins:
  - `users.password_hash`, `users.mfa_secret`
  - `attack_sessions.credentials_attempted[].password`
  - `fake_credentials.secret_enc`
  - `login_history` PII (geo) where regulated

## 4. Validation as a control

- `$jsonSchema` validators with `validationAction: "error"` on hot/critical
  collections block malformed or injected documents at write time.
- `additionalProperties: false` prevents attacker-controlled fields (e.g. via a
  poisoned enrichment payload) from silently entering documents.

## 5. Audit logging

- Enable MongoDB auditing (`auditLog`) for auth, role changes, and DDL.
- Application audit trail: `login_history` (authn) + a change-stream consumer that
  writes an append-only audit topic for writes to `users`, `roles`, `permissions`,
  and `response_actions` (who blocked what, when).

## 6. Operational hardening

- Bind to private subnets only; no public `mongod`. Access via the app tier / VPN.
- Rotate KMS keys and DB credentials on a schedule; store secrets in a vault, not `.env`.
- Disable server-side JS (`security.javascriptEnabled: false`) unless a job needs it.
- Separate the deception data plane from the management plane (mirrors the
  honeypot-net / management-net split in the platform).
