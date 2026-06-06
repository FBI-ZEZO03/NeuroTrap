# 10 · Elasticsearch Integration

MongoDB is the system of record; Elasticsearch 8.x is the **search/aggregation
mirror** for the hot, analyst-facing collections. ES is never the source of truth
and can be rebuilt from Mongo at any time.

## 1. What gets indexed

| Mongo collection | ES index | Why |
|------------------|----------|-----|
| `attack_sessions` | `neurotrap-sessions-*` (time-based) | full-text on commands, fast facets for the feed/timeline |
| `threat_actors` | `neurotrap-actors` | search by IP/ASN/ISP, aggregate by classification |
| `mitre_mappings` | `neurotrap-mitre` | technique/tactic aggregations |
| `alerts` | `neurotrap-alerts-*` | alert search + dashboards |
| `attack_campaigns` | `neurotrap-campaigns` | campaign search |
| `ai_analyst_outputs` | `neurotrap-ai-outputs` | full-text over narratives |

Reference/PII-heavy collections (`users`, `login_history`, `fake_credentials`,
`threat_intel` raw) are **not** mirrored. Credential/PII fields are excluded from
any indexed document.

## 2. Sync mechanism

- **Change Streams → connector.** A resumable change-stream consumer (Monstache or a
  custom Node service using `resumeToken`) tails the mirrored collections and
  upserts/deletes into ES. The resume token is persisted so restarts don't miss or
  replay events.
- Time-based indices (`-YYYY.MM`) with ILM: hot → warm → delete, aligned to the
  retention windows in doc 08.
- Backfill/rebuild via a one-off scan job when mappings change.

```
attack_sessions (Mongo)  --change stream-->  connector  --bulk upsert-->  neurotrap-sessions-2026.06
                                   |                                            |
                              resume token (persisted)                      ILM policy
```

## 3. Example mappings

`neurotrap-sessions` (commands are text for search, ids are keyword for exact match):

```json
{
  "mappings": {
    "properties": {
      "session_id":        { "type": "keyword" },
      "source_ip":         { "type": "ip" },
      "protocol":          { "type": "keyword" },
      "honeypot_source":   { "type": "keyword" },
      "session_status":    { "type": "keyword" },
      "risk_score":        { "type": "float" },
      "start_time":        { "type": "date" },
      "end_time":          { "type": "date" },
      "duration_seconds":  { "type": "float" },
      "threat_actor_ref":  { "type": "keyword" },
      "commands_executed": {
        "type": "nested",
        "properties": {
          "ts": { "type": "date" },
          "command": { "type": "text", "fields": { "raw": { "type": "keyword" } } }
        }
      },
      "tags": { "type": "keyword" }
    }
  }
}
```

`neurotrap-actors`:

```json
{
  "mappings": {
    "properties": {
      "actor_id":          { "type": "keyword" },
      "primary_ip":        { "type": "ip" },
      "known_ips":         { "type": "ip" },
      "classification":    { "type": "keyword" },
      "risk_score":        { "type": "float" },
      "reputation_score":  { "type": "float" },
      "country":           { "type": "keyword" },
      "asn":               { "type": "integer" },
      "isp":               { "type": "text", "fields": { "raw": { "type": "keyword" } } },
      "first_seen":        { "type": "date" },
      "last_seen":         { "type": "date" },
      "mitre_techniques":  { "type": "keyword" }
    }
  }
}
```

## 4. Query division of labour

- **MongoDB:** point lookups by business key, transactional reads/writes, the
  index-backed dashboard queries in doc 05.
- **Elasticsearch:** free-text command search, large date-range aggregations,
  geo/heatmap facets, and the global attack-feed search box.
