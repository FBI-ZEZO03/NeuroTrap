# Response Engine

The Response Engine is the autonomous enforcement layer. It evaluates each attacker's threat score and executes a proportional response — from silent logging to emergency network blocking with forensic capture.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `ResponseEngine` | `src/response/response_engine.py` | Decision matrix + action execution |

---

## Decision Matrix

Response actions are determined by threat score thresholds:

| Score Range | Action | Enforcement |
|-------------|--------|-------------|
| ≥ 90 | `block_emergency` | `iptables -I INPUT -s <IP> -j DROP` + forensic PCAP + multi-channel alert |
| 70–89 | `isolate_alert` | `iptables -I INPUT -s <IP> -j LOG` + rate-limit rule + alert |
| 40–69 | `slow_redirect` | `tc netem delay 500ms` on source IP + log |
| < 40 | `log_only` | Write to `response_log` only |

---

## Action Details

### `block_emergency` (score ≥ 90)

1. **iptables DROP rule:** `iptables -I INPUT -s <IP> -j DROP` — drops all further packets
2. **Forensic PCAP:** Starts `tcpdump -i <interface> host <IP> -w /tmp/forensic_<IP>.pcap -c 10000` (captures next 10,000 packets)
3. **Alerts:**
   - Email via SMTP (if `SMTP_HOST` configured)
   - Slack webhook (if `SLACK_WEBHOOK_URL` configured)
   - Telegram bot (if `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` configured)
4. **Database:** Writes to `response_log` with `action: "block_emergency"`

### `isolate_alert` (score 70–89)

1. **iptables LOG rule:** `iptables -I INPUT -s <IP> -j LOG --log-prefix "NEUROTRAP_ALERT: "`
2. **Rate limiting:** `tc netem delay 200ms` with packet-loss injection
3. **Alert:** Sends notification (lower priority than `block_emergency`)
4. **Database:** Writes to `response_log` with `action: "isolate_alert"`

### `slow_redirect` (score 40–69)

1. **Traffic shaping:** `tc qdisc add dev <iface> root netem delay 500ms 50ms distribution normal`  
   Adds 500ms ± 50ms of latency to the attacker's traffic, making automated tools appear unreliable
2. **Database:** Writes to `response_log`

### `log_only` (score < 40)

1. Only records to `response_log` — no network intervention

---

## Mock Mode

When `iptables` or `tc` are not available (local development, containers without `NET_ADMIN`), all network operations fail gracefully — the decision is logged but no enforcement occurs. This means:

- The full decision logic always runs
- `response_log` is always populated
- Dashboard and API show accurate records
- No errors bubble up to the API

---

## Response Log Schema

```python
{
    "action": "block_emergency",
    "src_ip": "203.0.113.45",
    "threat_score": 95.2,
    "timestamp": 1780969777.0,
    "details": {
        "intent": "malware_deployment",
        "tier": "advanced_human",
        "session_count": 8,
        "ttps": ["T1105", "T1053.003", "T1003.008"]
    }
}
```

---

## Manual Block

Admins can manually block an IP regardless of threat score:

```bash
curl -s -X POST http://localhost:5000/api/response/block \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"src_ip": "203.0.113.45"}'
```

This runs the same `block_emergency` path.

---

## Alert Channels

Configure alert channels via environment variables:

```bash
# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASS=<password>
ALERT_EMAIL_TO=soc-team@example.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Telegram
TELEGRAM_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
```

All channels are optional. If none are configured, `block_emergency` still fires the iptables rule and PCAP capture; it just doesn't send external notifications.

---

## Reverting a Block

iptables blocks survive container restarts (they're applied to the host kernel). To unblock:

```bash
# List all NEUROTRAP blocks
sudo iptables -L INPUT -n --line-numbers | grep NEUROTRAP

# Remove a specific block (replace N with the line number)
sudo iptables -D INPUT N

# Or remove by IP
sudo iptables -D INPUT -s 203.0.113.45 -j DROP
```

---

## Dashboard Integration

The **Response Log** section of the dashboard shows:
- All response actions with timestamp, action type, IP, threat score
- Color-coded by severity: `block_emergency` (red) · `isolate_alert` (orange) · `slow_redirect` (yellow) · `log_only` (blue)

The **KPI dashboard** shows **IPs Blocked** as the count of `block_emergency` + `isolate_alert` entries in `response_log`.

---

## Integration with Deception Engine

The response engine and deception engine are called together for each profile update:

```python
# src/deception/main.py
for profile in top_threat_profiles:
    if profile.threat_score >= 10 and not profile.is_blocked:
        deception_engine.generate_environment(profile)
    response_engine.evaluate(profile)
```

A blocked attacker (`score >= 90`) gets their traffic dropped at the network level, but their deception environment remains active to capture any traffic that gets through before the iptables rule propagates.
