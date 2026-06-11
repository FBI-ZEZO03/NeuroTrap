# Honeypot Layer

NeuroTrap deploys four honeypot technologies covering 15+ protocols. Each sensor writes structured JSON logs that are normalized by the detection pipeline into `AlertEvent` records.

---

## Honeypot Overview

| Honeypot | Type | Protocols | Ports |
|----------|------|-----------|-------|
| Cowrie | High-interaction | SSH, Telnet | 22, 23 |
| OpenCanary | Low-interaction | FTP, HTTP, SMB, MySQL, MSSQL, SNMP, VNC, RDP | 21, 80, 445, 3306, 1433, 161/udp, 5900, 3389 |
| Galah | LLM-powered web | HTTP | 8088 |
| Native Python | Custom sensors | SSH, HTTP, FTP, Telnet | 2222, 8081, 2121, 2323 (optional) |

---

## Cowrie — SSH/Telnet Honeypot

Cowrie presents a fully interactive fake Linux shell. Attackers can log in, run commands, download files, and pivot — all while every keystroke is recorded.

### Configuration (`config/cowrie.cfg`)

```ini
[honeypot]
hostname = web-prod-01           ; believable production hostname

[ssh]
enabled = true
listen_endpoints = tcp:2222:interface=0.0.0.0
version = SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5

[telnet]
enabled = true
listen_endpoints = tcp:2223:interface=0.0.0.0

[output_jsonlog]
enabled = true
logfile = ${honeypot:log_path}/cowrie.json
```

Port 22 on the host maps to container port 2222. The SSH version string impersonates a real Ubuntu installation.

### Credential Policy (`config/userdb.txt`)

```
root:x:!root        # decline literal "root"
root:x:!123456      # decline the most trivial password
root:x:*            # accept any other password for root
admin:x:*           # accept any password for admin
```

`*` means accept, `!` means decline. This lets attackers in while making the honeypot look like a hardened-but-misconfigured server rather than an obvious trap.

### Log Format

Cowrie emits JSONL events, one per line:

```json
{ "eventid": "cowrie.login.success", "timestamp": "2025-06-09T10:15:32.000Z",
  "src_ip": "203.0.113.45", "username": "root", "password": "p@ssw0rd",
  "session": "a1b2c3d4" }

{ "eventid": "cowrie.command.input", "timestamp": "2025-06-09T10:15:35.000Z",
  "src_ip": "203.0.113.45", "input": "cat /etc/passwd", "session": "a1b2c3d4" }

{ "eventid": "cowrie.session.closed", "timestamp": "2025-06-09T10:16:10.000Z",
  "src_ip": "203.0.113.45", "duration": 38.4, "session": "a1b2c3d4" }
```

### Key Event IDs and Their Mappings

| Cowrie event ID | `attack_type` stored |
|----------------|---------------------|
| `cowrie.login.failed` | `brute_force` |
| `cowrie.login.success` | `brute_force` |
| `cowrie.command.input` | `command_injection` |
| `cowrie.session.file_upload` | `malware_upload` |
| `cowrie.session.file_download` | `malware_upload` |
| `cowrie.direct-tcpip.*` | `lateral_movement` |
| `cowrie.client.version` | `tool_fingerprint` |
| `cowrie.client.kex`, `.var`, `.fingerprint` | skipped (`_COWRIE_SKIP`) |

---

## OpenCanary — Multi-Service Sensor

OpenCanary fills the breadth gaps that Cowrie doesn't cover. It answers on 13 additional protocols with low-interaction emulation — enough to detect probes and log connection attempts.

OpenCanary also covers all former Dionaea ports (21, 80, 445, 3306) after Dionaea was disabled due to a kernel 6.8 crash (SIGTRAP in `libemu`).

### Configuration (`config/opencanary.conf`)

```json
{
  "device.node_id": "neurotrap-canary-01",
  "logtype": "json",
  "ftp.enabled": true,   "ftp.port": 21,
  "http.enabled": true,  "http.port": 80,
  "smb.enabled": true,
  "mysql.enabled": true, "mysql.port": 3306,
  "mssql.enabled": true, "mssql.port": 1433,
  "snmp.enabled": true,  "snmp.port": 161,
  "vnc.enabled": true,   "vnc.port": 5900,
  "rdp.enabled": true,   "rdp.port": 3389,
  "logger": {
    "class": "PyLogger",
    "kwargs": {
      "handlers": {
        "file": {
          "class": "logging.FileHandler",
          "filename": "/var/tmp/opencanary/opencanary.log"
        }
      }
    }
  }
}
```

---

## Galah — LLM-Powered Web Honeypot

Galah dynamically generates realistic HTTP responses using a large language model (Anthropic Claude or OpenAI). Each scanning tool or attacker sees a plausible, unique web application instead of a static template.

### Configuration (`config/galah/config.yaml`)

```yaml
provider: anthropic
model: claude-opus-4-8
server:
  address: "0.0.0.0:8080"
logging:
  file: /galah/logs/galah.json
```

### Enabling Galah

Galah is disabled by default (crashes without an API key). To enable:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
docker compose up -d galah
```

### Log Format

JSONL web events: method, path, headers, body, and the LLM-generated response.

---

## Native Python Honeypots (Optional)

Four lightweight sensors in `src/honeypots/` provide an alternative to or supplement the Docker-based honeypots. They are not started by default; opt in via Docker profile or run directly.

```bash
# Docker profile
docker compose --profile native-honeypots up

# Or run directly
pip install -r requirements/honeypots.txt
python -m src.honeypots.main
```

| Sensor | File | Port | Notes |
|--------|------|------|-------|
| SSH | `ssh_honeypot.py` | 2222 | Full credential capture (paramiko); banner-only fallback |
| HTTP | `http_honeypot.py` | 8081 | Logs request method, path, headers, body |
| FTP | `ftp_honeypot.py` | 2121 | Logs credential attempts and commands |
| Telnet | `telnet_honeypot.py` | 2323 | Logs all characters typed |

All sensors extend `BaseHoneypot` (`src/honeypots/base.py`), which:
- Runs a threaded TCP server
- Tracks credentials and commands per connection in `HoneypotSession`
- Calls `record_event()` to normalize to `AlertEvent` and persist to `alert_events`
- Also writes full sessions to `honeypot_sessions`

---

## Honeypot Port Map

```
Internet
    22/tcp  → Cowrie SSH       (docker port mapping: host:22 → cowrie:2222)
    23/tcp  → Cowrie Telnet    (host:23 → cowrie:2223)
    21/tcp  → OpenCanary FTP
    80/tcp  → OpenCanary HTTP
    443/tcp → Nginx → Dashboard
    445/tcp → OpenCanary SMB
    1433/tcp→ OpenCanary MSSQL
    3306/tcp→ OpenCanary MySQL
    3389/tcp→ OpenCanary RDP
    5900/tcp→ OpenCanary VNC
    8080/tcp→ Nginx → Dashboard (HTTP redirect to HTTPS)
    8088/tcp→ Galah web honeypot
    161/udp → OpenCanary SNMP
```

---

## Network Isolation

Honeypots run exclusively on `honeypot-net` (172.20.0.0/24). The analytics network (`elk-net`) and management network (`management-net`) are marked `internal: true` in Docker Compose — they have no default gateway, so containers on them cannot initiate outbound connections, and `honeypot-net` containers cannot address them.

This means: even if an attacker fully escapes a honeypot container, they cannot reach MongoDB, the behavior engine, or the Flask API.

---

## Verifying Honeypots Work

```bash
# SSH honeypot
ssh root@<host>               # should land in Cowrie fake shell

# Brute-force detection
for i in {1..10}; do ssh -o ConnectTimeout=1 root@<host> 2>/dev/null; done
# should produce brute_force events in alert_events

# Check events in the database
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.alert_events.countDocuments()"

# Check Cowrie logs directly
docker exec neurotrap-cowrie tail -f /cowrie/cowrie-git/var/log/cowrie/cowrie.json
```
