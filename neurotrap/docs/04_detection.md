# Detection Pipeline

The detection layer is the central nervous system of NeuroTrap. It consumes all raw sensor output — JSON logs from honeypots, raw packets from the network interface, and Zeek flow logs — and normalizes everything into a single `AlertEvent` schema stored in MongoDB.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `AlertEvent` schema | `src/detection/alert_schema.py` | Canonical event data model |
| `PacketMonitor` | `src/detection/packet_monitor.py` | Live Scapy-based packet analysis |
| `LogIngestionPipeline` | `src/detection/log_pipeline.py` | Tails honeypot JSON log files |
| `CowrieSessionBuilder` | `src/detection/log_pipeline.py` | Aggregates Cowrie events into sessions |
| `main.py` | `src/detection/main.py` | Starts both monitor and pipeline as threads |

---

## AlertEvent Schema

`AlertEvent` (`src/detection/alert_schema.py`) is the normalized record every downstream module receives. All sources are mapped into this shape before being written to the database.

```python
@dataclass
class AlertEvent:
    # Required fields
    src_ip: str
    dst_port: int
    attack_type: str       # see ATTACK_TYPES
    honeypot_source: str   # cowrie, opencanary, galah, packet_monitor, other
    severity: str          # low, medium, high, critical

    # Optional fields
    src_port: Optional[int] = None
    session_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    command: Optional[str] = None
    raw_payload: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### Attack Types

```python
ATTACK_TYPES = (
    "brute_force",
    "command_injection",
    "tool_fingerprint",
    "protocol_anomaly",
    "lateral_movement",
    "malware_upload",
    "port_scan",
    "unknown",
)
```

### Factory Methods

```python
AlertEvent.from_cowrie(line: str) -> AlertEvent
```
Parses a Cowrie JSON line, maps `eventid` → `attack_type`, extracts credentials and commands.

```python
AlertEvent.from_zeek(line: str) -> AlertEvent
```
Parses a Zeek connection-log JSON line, extracts source IP, destination port, and protocol.

### Skipped Events

Cowrie metadata events that carry no attack signal are filtered via `_COWRIE_SKIP`:

```python
_COWRIE_SKIP = frozenset({
    "cowrie.client.kex",
    "cowrie.client.var",
    "cowrie.client.fingerprint",
    "cowrie.connection.failed",
    "cowrie.session.connect",
})
```

These events are valid Cowrie output but provide no behavioral data for the pipeline.

---

## PacketMonitor — Scapy Live Capture

`PacketMonitor` (`src/detection/packet_monitor.py`) sniffs raw packets on the configured network interface and detects threats via rolling-window threshold rules.

The container runs with `network_mode: host` and requires `CAP_NET_ADMIN` and `CAP_NET_RAW` capabilities. The environment variable `MONITOR_INTERFACE` (default: `eth0`) controls which NIC is sniffed.

### Detection Rules

| Rule | Trigger | `attack_type` | `severity` |
|------|---------|---------------|------------|
| Port scan | > 10 distinct destination ports from one IP in 5 s | `port_scan` | `medium` |
| Brute force | > 5 failed logins from one IP in 60 s | `brute_force` | `high` |
| Protocol anomaly | Malformed/unexpected TCP flags or payload for the destination port | `protocol_anomaly` | `medium` |
| Tool fingerprint | Known scanner signatures in TCP payload (nmap, masscan, zmap) | `tool_fingerprint` | `low` |
| UDP fallback | Any UDP to a monitored port that doesn't match a known protocol | `protocol_anomaly` | `low` |

### Implementation Sketch

```python
from collections import defaultdict, deque
from scapy.all import sniff, IP, TCP
import time

PORT_SCAN_PORTS = 10
PORT_SCAN_WINDOW = 5   # seconds
BRUTE_FORCE_THRESHOLD = 5
BRUTE_FORCE_WINDOW = 60

ports_seen = defaultdict(lambda: deque())

def inspect(pkt):
    if not pkt.haslayer(IP) or not pkt.haslayer(TCP):
        return
    src = pkt[IP].src
    dport = pkt[TCP].dport
    now = time.time()

    dq = ports_seen[src]
    dq.append((now, dport))
    while dq and now - dq[0][0] > PORT_SCAN_WINDOW:
        dq.popleft()

    distinct = len({p for _, p in dq})
    if distinct > PORT_SCAN_PORTS:
        emit_alert(src_ip=src, dst_port=dport,
                   attack_type="port_scan", severity="medium",
                   honeypot_source="packet_monitor")

sniff(iface="eth0", prn=inspect, store=False)
```

---

## LogIngestionPipeline — Honeypot Log Tailing

`LogIngestionPipeline` (`src/detection/log_pipeline.py`) runs background threads that tail each honeypot's JSON log file and emit normalized `AlertEvent` objects.

### Sources

| Honeypot | Log file (container path) | Format |
|----------|--------------------------|--------|
| Cowrie | `/cowrie/cowrie-git/var/log/cowrie/cowrie.json` | JSONL (one event per line) |
| OpenCanary | `/var/tmp/opencanary/opencanary.log` | JSONL |
| Galah | `/galah/logs/galah.json` | JSONL |

Each source has a dedicated tail thread. Lines are parsed one at a time; malformed/partial JSON lines are caught and skipped (files can be mid-write when tailed).

### Read-Offset Persistence

The pipeline persists its read offset per source file to avoid re-processing events after a container restart. Offset is stored in the database and checked on startup.

---

## CowrieSessionBuilder

`CowrieSessionBuilder` (embedded in `log_pipeline.py`) aggregates per-session Cowrie events into complete session documents for the behavior engine.

**Why a separate builder?**  
The ML classifier in `src/behavior/` needs a complete session record (all commands, credentials, timing) to extract features. Raw `AlertEvent` records are per-event; this builder groups them by `session_id`.

### Session Document Schema

```python
{
    "session_id": "a1b2c3d4",
    "src_ip": "203.0.113.45",
    "start_time": 1780000000.0,
    "end_time": 1780000038.4,
    "duration": 38.4,
    "login_attempts": 3,
    "commands": ["uname -a", "id", "cat /etc/passwd"],
    "username": "root",
    "password": "p@ssw0rd",
    "processed": false,   # BehaviorEngine sets to true after classification
}
```

On `cowrie.session.closed`, the builder writes this document to `cowrie_sessions`. The behavior engine polls for `{"processed": false}` records.

---

## Severity Assignment

Severity is assigned at ingestion time as a first-pass triage value:

| Signal | Severity |
|--------|----------|
| Single connection, probe | `low` |
| Port scan, repeated failed logins | `medium` |
| Successful login + command execution | `high` |
| Malware upload / download | `high` |
| Critical service exploitation | `critical` |

The severity in `AlertEvent` drives the dashboard's color coding and the initial filter. The richer composite **threat score** (0–100) computed by the behavior engine from full session context drives response decisions.

---

## Data Flow Summary

```
Honeypot JSON files (bind-mounted volumes)
    ↓  tail threads (one per source)
LogIngestionPipeline
    ↓  AlertEvent.from_cowrie() / from_zeek() / etc.
    ↓  write to alert_events collection
    ↓  (Cowrie only) CowrieSessionBuilder
    ↓  write to cowrie_sessions on session.closed

Raw network packets (host NIC)
    ↓  Scapy sniff()
PacketMonitor
    ↓  rolling-window threshold rules
    ↓  AlertEvent (attack_type, severity set by rule)
    ↓  write to alert_events collection
```

---

## Database Indexes

Created by `scripts/setup_db_indexes.py`:

```python
db.alert_events.create_index("src_ip")
db.alert_events.create_index("timestamp")
db.alert_events.create_index("attack_type")
db.alert_events.create_index([("src_ip", 1), ("timestamp", -1)])

db.cowrie_sessions.create_index("session_id", unique=True)
db.cowrie_sessions.create_index("src_ip")
db.cowrie_sessions.create_index("processed")   # for BehaviorEngine polling
```

---

## Verification

```bash
# Trigger a brute-force and check detection
for i in {1..10}; do
  ssh -o ConnectTimeout=1 -o StrictHostKeyChecking=no root@localhost 2>/dev/null
done

# Query for brute_force events
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.alert_events.find({attack_type:'brute_force'}).limit(3).pretty()"

# Check port-scan detection latency (should appear within 5 seconds)
nmap -sS -p 1-1000 localhost &
sleep 5
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.alert_events.find({attack_type:'port_scan'}).count()"
```
