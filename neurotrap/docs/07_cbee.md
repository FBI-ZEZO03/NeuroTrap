# CBEE — Cognitive Bias Exploitation Engine

The Cognitive Bias Exploitation Engine (CBEE) analyzes attacker behavior through the lens of social engineering and cognitive psychology. It scores each attacker on five bias dimensions and uses those scores to inject precisely timed bait designed to extend engagement and extract higher-value intelligence.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `BiasScorer` | `src/cbee/bias_scorer.py` | Scores sessions on 5 bias dimensions |
| `CBEEEngine` | `src/cbee/cbee_engine.py` | Background loop; triggers injections when threshold met |
| `BaitInjector` | `src/cbee/bait_injector.py` | Generates bias-targeted fake assets |

---

## The Five Bias Dimensions

Each dimension is scored 0–100 based on observable session behavior:

### 1. Curiosity Gap
**What it measures:** Whether the attacker is actively hunting for hidden/sensitive information.

**Triggers:** `grep`/`find`/`cat` commands on files with `.key`, `.env`, `.secret`, `.pem`, `.cert`, `.conf` extensions; access to `/var/log/`, `~/.ssh/`.

**Exploitation:** Plant a file with an enticing name (e.g., `backup_credentials_2024.txt`, `prod_aws_keys.env`) in a predictable location.

### 2. Confirmation Bias
**What it measures:** Whether the attacker is running early recon commands that confirm their assumed target type (e.g., looking for a web server, a database, a corporate machine).

**Triggers:** Sequences of discovery commands that match a consistent target hypothesis (`ls /var/www`, `ps aux | grep apache`, `netstat -nltp`).

**Exploitation:** Create artifacts that strongly confirm the assumed target identity (a fake Apache config, fake database dumps with the expected schema).

### 3. Sunk Cost
**What it measures:** How much the attacker has invested in this session (time, bandwidth, commands).

**Triggers:** `wget`/`curl` downloads, `apt install`, multi-step command sequences. Scored by download count and session length.

**Exploitation:** Plant a "reward" at the end of an obviously multi-step process (a fake admin panel, a credentials archive).

### 4. Authority Signal
**What it measures:** Whether the attacker is pursuing privilege escalation and high-value system files.

**Triggers:** `sudo`, `chmod 4xxx`/`chmod u+s` (SUID bits), `/etc/shadow` access, `/etc/sudoers` access, kernel exploit attempts.

**Exploitation:** Leave a hint that a higher-privileged account exists and has not been properly secured (`cat /etc/sudoers` returning a permissive entry; a fake root `.bash_history` with revealing commands).

### 5. Scarcity Framing
**What it measures:** Whether the attacker is establishing persistence with urgency — suggesting they expect limited access time.

**Triggers:** `crontab -e`, `nohup`, systemd unit file creation, high login attempt rate, `disown`.

**Exploitation:** Plant "time-limited" artifacts (credentials with expiry dates, backup windows, scheduled job comments like `# expires 2025-01-01`).

---

## BiasProfile

```python
@dataclass
class BiasProfile:
    src_ip: str
    curiosity_gap: float     # 0–100
    confirmation_bias: float # 0–100
    sunk_cost: float         # 0–100
    authority_signal: float  # 0–100
    scarcity_framing: float  # 0–100
    overall: float           # mean of all 5 dimensions
    dominant: str            # argmax dimension name
    updated_at: float
```

`overall` is the mean of the five dimensions. `dominant` is the highest-scoring dimension and determines which bait type is deployed.

---

## CBEEEngine

`CBEEEngine` runs as a background thread started alongside the Flask API.

### Scoring Loop

```python
while True:
    # Get active profiles with enough session data
    profiles = db.attacker_profiles.find({"threat_score": {"$gte": 30}})
    for profile in profiles:
        commands = get_all_commands(profile["src_ip"])
        session_data = {"commands": commands, ...}
        bias = BiasScorer().score(session_data)
        db.cbee_profiles.update_one(
            {"src_ip": profile["src_ip"]},
            {"$set": bias.__dict__},
            upsert=True
        )
        # Fire injection if threshold met
        if bias.overall >= 25:
            injections = db.cbee_injections.count_documents(
                {"src_ip": profile["src_ip"]}
            )
            if injections < 3:
                BaitInjector().inject(profile["src_ip"], bias)
    sleep(30)
```

### Injection Threshold

Injections fire when:
- `bias.overall >= 25` (attacker shows measurable bias engagement)
- Fewer than 3 injections have been sent for this IP (prevents flooding)

---

## BaitInjector

`BaitInjector` generates fake assets targeted to the dominant bias dimension and stores them in `cbee_injections`.

| Dominant Bias | Asset Generated |
|--------------|----------------|
| `curiosity_gap` | Fake credential file at a predictable path (e.g., `/tmp/.db_backup_credentials`) |
| `confirmation_bias` | Fake configuration confirming target hypothesis |
| `sunk_cost` | Fake admin credentials behind a "requires authentication" path |
| `authority_signal` | Fake `/etc/sudoers` entry granting `ALL=(ALL) NOPASSWD:ALL` to a fake account |
| `scarcity_framing` | Fake time-limited credential with expiry comment |

---

## Dashboard Integration

The **CBEE** section of the dashboard (`/cbee`) shows:

- **Bias profiles table** — top 50 attackers scored by `overall`, with per-dimension bars
- **Bait injection log** — which IPs received injections, which bias type triggered them, and what assets were planted
- **Ad-hoc scorer** — submit a command list and get a live bias profile (admin only; calls `POST /api/cbee/score`)

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/cbee/profiles` | GET | — | Top 50 bias profiles |
| `/api/cbee/injections` | GET | — | Last 20 bait injection records |
| `/api/cbee/score` | POST | admin | Score a command list ad-hoc |

---

## Tuning

The scoring thresholds are defined as constants in `bias_scorer.py`:

```python
CURIOSITY_KEYWORDS = [".key", ".env", ".secret", ".pem", "/var/log", "/.ssh"]
AUTHORITY_KEYWORDS = ["sudo", "/etc/shadow", "/etc/sudoers", "chmod 4"]
SUNK_COST_MIN_DOWNLOADS = 2     # need ≥ 2 downloads to start scoring
INJECTION_OVERALL_THRESHOLD = 25
MAX_INJECTIONS_PER_IP = 3
```

Raising `INJECTION_OVERALL_THRESHOLD` makes injections more selective (fewer false positives). Raising `MAX_INJECTIONS_PER_IP` allows more follow-up baiting.
