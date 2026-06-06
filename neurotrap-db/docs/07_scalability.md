# 07 · Scalability

Target load: **thousands of attack sessions/day** (peak bursts during mass
scanning), multi-year retention of profiles/twins/campaigns. Each session can
carry dozens of embedded events, so `attack_sessions` and `mitre_mappings`
dominate write volume.

## 1. Sharding plan (high-volume collections)

| Collection | Shard key | Type | Why |
|------------|-----------|------|-----|
| `attack_sessions` | `{ source_ip: "hashed" }` | hashed | even write distribution; avoids monotonic `_id` hot-shard. Actor-timeline queries still served by the `{source_ip,start_time}` index within shards. |
| `mitre_mappings` | `{ related_session: "hashed" }` | hashed | co-locates a session's mappings, spreads load |
| `alerts` | `{ _id: "hashed" }` | hashed | high insert rate, no natural locality |
| `login_history` | `{ user_ref: "hashed" }` | hashed | spread auth audit writes |
| `deception_effectiveness` | `{ environment_ref: "hashed" }` | hashed | per-env locality |

Warm analytical collections (`threat_actors`, `digital_twins`,
`attack_campaigns`, `threat_intel`) are **unsharded** initially — modest size,
benefit from single-shard secondary-index queries. Revisit if an actor/twin count
exceeds tens of millions.

> Compound alternative considered: `{source_ip:1, start_time:1}` (range) for
> `attack_sessions` gives locality for time-range scans but risks jumbo chunks for
> noisy scanners. Hashed `source_ip` chosen for write balance; time-range queries
> are bounded per shard by the secondary index.

## 2. Read/write scaling

- **Writes:** ingest workers use bulk `insertMany`/`bulkWrite` with
  `w:"majority"` only on critical paths (response_actions); honeypot telemetry can
  use `w:1` + retryable writes for throughput.
- **Reads:** dashboards use `readPreference: secondaryPreferred` against the
  replica set; heavy aggregation/search offloaded to **Elasticsearch** (doc 10).
- Connection pooling at the app tier; cap pool per instance to protect primary.

## 3. Capped / TTL / live-feed strategy

- **Live attack feed:** serve from a capped collection or a TTL-bounded
  projection (`attack_sessions` last N minutes) rather than scanning the full set;
  alternatively from the ES hot index.
- **TTL collections:** `login_history` (365d), `threat_intel` (`expires_at`),
  `active_environments` (`expires_at`) auto-trim without batch jobs.
- Raw session detail tiers to cold storage after 90d (doc 08), keeping the hot
  shard set small and fast.

## 4. Growth headroom

- Pre-split hashed shard ranges before a known scanning event to avoid initial
  balancing churn.
- Monitor chunk distribution and the balancer; alert on jumbo chunks.
- Embedded arrays are bounded (cap stored commands/timeline length in the writer)
  to keep `attack_sessions` documents well under the 16 MB limit.
