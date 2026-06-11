# Deception Engine

The deception engine is the core innovation of NeuroTrap. Instead of a single generic honeypot, it reads the attacker profile produced by the behavior engine and spawns a decoy environment tailored to that specific attacker — a simple Linux box for a script-kiddie, a credential-baited server for an automated bot, or a fake corporate environment with planted secrets for an APT actor.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `DeceptionEngine` | `src/deception/deception_engine.py` | Orchestrator: reads profiles, spawns/tears down environments |
| `CredentialGenerator` | `src/deception/credential_generator.py` | Generates fake users, credentials, keys, config files |
| `main.py` | `src/deception/main.py` | Entry point: polling loop + response engine integration |

---

## Environment Templates

Three environment archetypes are defined in `DeceptionEngine.ENV_TEMPLATES`. Each template specifies the OS flavour, number of services, and what fake data to seed:

| Attacker Tier | Template | What They See |
|--------------|----------|---------------|
| `beginner` | `simple-linux` | Ubuntu 20.04, 2 services (SSH + HTTP), standard user files |
| `automated_bot` | `baited-server` | CentOS 7, 4 services, seeded with credentials common credential-stuffing bots expect |
| `advanced_human` | `advanced-corporate` | Debian 11, 6 services + Docker, planted AWS keys, `.env` files, populated fake DB |

### Template Definition (example: advanced)

```python
{
    "name": "advanced-corporate",
    "base_image": "cowrie/cowrie:latest",
    "hostname_pool": ["fin-db-01", "vpn-gw-02", "jenkins-prod", "corp-ldap-03"],
    "services": ["ssh", "http", "ftp", "mysql"],
    "seed": {
        "fake_secrets": True,     # plant AWS keys, .env files
        "fake_db_rows": 500,
        "users": 8
    },
    "timeout_minutes": 30
}
```

Hostnames are randomized from the pool; an attacker who returns later may see a different hostname, reinforcing the illusion of a real network.

---

## DeceptionEngine

### Public Interface

```python
class DeceptionEngine:
    def generate_environment(self, profile: AttackerProfile) -> str:
        """Spawn a personalized decoy. Returns env_id."""

    def get_active_environments(self) -> dict:
        """Return all currently running environments."""

    def teardown(self, env_id: str) -> None:
        """Force-remove a decoy container and free the name."""
```

### Spawn Flow

1. `select_template(profile)` — maps attacker tier to template
2. `CredentialGenerator.generate(template)` — Faker-based fake users, keys, creds
3. `FakeFS.build(template, creds)` — constructs honeyfs directory tree
4. Docker API: `containers.run(template.base_image, ...)` with custom hostname and fake filesystem mounted at `/cowrie/honeyfs`
5. Falls back to a `MockEnvironment` dict if Docker socket is unavailable
6. Environment record saved to `deception_environments` with `is_active: True`

### TTP-Based Customization

If the attacker's TTP list includes specific tactics, the engine further personalizes the environment:

| TTP Tactic | Customization |
|-----------|---------------|
| Credential Access | Add `/etc/shadow`-style file with seeded hashes |
| Lateral Movement | Add SSH config with fake internal hostnames |
| Persistence | Add existing cron entries in `/var/spool/cron/` |
| Command and Control | Add fake outbound connection logs suggesting C2 |

---

## CredentialGenerator

`CredentialGenerator` (`src/deception/credential_generator.py`) uses the `Faker` library seeded deterministically per attacker IP, so the same attacker always gets the same fake identity (realistic across multiple visits).

### Generated Artifacts

| Artifact | Content |
|----------|---------|
| SSH users | `{"username": "jsmith", "password": "TempPass2024!", "email": "j.smith@corp.local"}` |
| AWS credentials | `~/.aws/credentials` with `AKIA...` key ID + secret access key |
| `.env` file | `DB_PASSWORD=...`, `SECRET_KEY=...`, `STRIPE_KEY=sk_live_...` |
| `/etc/shadow` entries | bcrypt-hashed fake passwords with realistic salt |
| Shell history | Plausible command history with timestamps |
| Database records | 500+ fake user rows with emails, bcrypt hashes, names |

Planted secrets (especially the AWS key pattern) double as tripwires — if an attacker attempts to use them externally, that's a high-confidence signal that they took the bait.

---

## Environment Lifecycle

```
Profile.threat_score >= 10
    └── DeceptionEngine.generate_environment(profile)
            ↓
        [SPAWNED] Container running, is_active=True
            ↓  attacker interacts
        [ENGAGED] Events flow back through detection pipeline
            ↓
        [TEARDOWN trigger: session_closed OR idle > timeout_minutes]
        DeceptionEngine.teardown(env_id)
            ↓
        Container removed, is_active=False, deactivated_at saved
```

The reaper runs on a timer (10-second poll) and tears down environments that:
- Have `is_active: True` but the backing container no longer exists
- Have exceeded `timeout_minutes` of idle time
- Whose attacker session has been marked closed

### Constraints

- Maximum 20 active environments (evicts oldest active to stay under limit)
- Environments auto-expire after 1 hour regardless of activity
- All environments are stored in MongoDB even after expiry (historical record)

---

## Deception Main Loop

`src/deception/main.py` runs the orchestration loop:

```python
while True:
    # Get top-threat unblocked attackers
    profiles = db.attacker_profiles.find(
        {"threat_score": {"$gte": 10}, "is_blocked": False}
    ).sort("threat_score", -1).limit(5)

    for profile in profiles:
        if profile not in active_environments:
            env_id = engine.generate_environment(profile)

        # Also run the response engine for this profile
        response_engine.evaluate(profile)

    sleep(10)
```

---

## Integration with Other Layers

```
BehaviorEngine
    → attacker_profiles (threat_score >= 10 trigger)
        → DeceptionEngine
            → spawns personalized Cowrie container
                → attacker interacts
                    → new events in alert_events
                        → feeds back into detection pipeline
                            → further enriches attacker profile
```

The deception engine creates a feedback loop: each decoy spawns a new Cowrie instance that continues generating `AlertEvent` data, which the behavior engine uses to update the profile, which can trigger a deeper tier environment.

---

## Verification

```bash
# Run simulation to trigger deception
python scripts/simulate_attack.py

# Check created environments
curl -s http://localhost:5000/api/environments | python3 -m json.tool

# Check database
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.deception_environments.find({},{src_ip:1,attacker_tier:1,is_active:1}).pretty()"

# Verify environment was personalized (check credentials were generated)
docker exec neurotrap-mongodb mongosh --quiet \
  -u admin -p "$MONGO_PASS" --authenticationDatabase admin neurotrap \
  --eval "db.deception_environments.findOne({attacker_tier:'advanced_human'},{credentials:1})"
```
