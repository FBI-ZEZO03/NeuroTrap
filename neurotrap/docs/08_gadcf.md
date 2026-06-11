# GADCF — Generative Adaptive Deception Content Factory

The Generative Adaptive Deception Content Factory (GADCF) produces realistic fake digital assets — environment files, email threads, code repositories, wiki runbooks, and database dumps — tailored to the attacker's classified intent and apparent target industry. These assets seed honeypot environments and serve as additional bait layers.

---

## Components

| Component | File | Role |
|-----------|------|------|
| `ContentGenerator` | `src/gadcf/content_generator.py` | Generates individual fake assets |
| `GADCFEngine` | `src/gadcf/gadcf_engine.py` | Orchestrator: maps intent → industry, coordinates generation |

---

## Asset Types

| Asset Type | Description | Example Content |
|-----------|-------------|----------------|
| `env_file` | `.env` config file with plausible credentials | `DB_PASSWORD=...`, `AWS_ACCESS_KEY_ID=AKIA...`, `STRIPE_SECRET_KEY=sk_live_...` |
| `email_thread` | Multi-email thread with credential rotation narrative | IT helpdesk thread announcing password reset for "production DB" |
| `code_repo` | Partial Flask/Django project with hardcoded fallback credentials | `db = connect("postgres://admin:TempPass@db-prod-01/appdb")` |
| `wiki_page` | Confluence/MediaWiki-style runbook | Server IPs, SSH keys, service account passwords, deployment procedures |
| `db_dump` | SQL dump with fake user records | `INSERT INTO users (email, password_hash) VALUES ('ceo@corp.com', '$2b$12...')` |

---

## Content Generation

### LLM Mode (Ollama Mistral)

When Ollama is running locally and reachable, `ContentGenerator` calls it to produce context-aware, industry-specific content:

```python
prompt = f"""Generate a realistic {asset_type} for a {industry} company.
Include plausible but obviously fake credentials. Make it look like a real
internal document that contains sensitive data."""
```

### Template Fallback

When Ollama is unavailable (default in the current deployment), `ContentGenerator` falls back to parameterized templates. Templates use `Faker` to randomize names, IPs, and values while maintaining structural realism.

**Example `.env` template:**

```
# Production environment — do not commit
DB_HOST=db-prod-01.internal
DB_PORT=5432
DB_NAME=production
DB_USER=app_svc
DB_PASSWORD={fake.password(length=20, special_chars=True)}
AWS_ACCESS_KEY_ID=AKIA{fake.bothify('????????????????')}
AWS_SECRET_ACCESS_KEY={fake.sha256()[:40]}
STRIPE_SECRET_KEY=sk_live_{fake.bothify('??????????????????????????????????????????????????')}
SECRET_KEY={fake.sha256()}
JWT_SECRET={fake.sha256()}
```

---

## Intent-to-Industry Mapping

`GADCFEngine` maps the attacker's classified intent to a target industry context, so the generated content aligns with what the attacker is likely seeking:

| Classified Intent | Target Industry | Asset Focus |
|------------------|----------------|-------------|
| `credential_harvesting` | Finance | High-value credentials, banking API keys |
| `malware_deployment` | E-commerce | Payment processor keys, customer database dumps |
| `lateral_movement` | Enterprise IT | Internal network diagrams, domain admin credentials |
| `cryptomining` | Cloud infrastructure | AWS/Azure credentials, Kubernetes configs |
| `bot_enrollment` | Any ISP/hosting | SSH keys, server lists, automation scripts |
| `reconnaissance` | Generic | Internal wiki pages, employee directories |

---

## GADCFEngine

```python
class GADCFEngine:
    def generate_for_profile(self, profile: AttackerProfile) -> list[dict]:
        industry = self.intent_to_industry(profile.classified_intent)
        assets = []
        for asset_type in self.select_asset_types(profile):
            content = self.generator.generate(
                asset_type=asset_type,
                industry=industry,
                sophistication=profile.attacker_tier
            )
            asset_doc = {
                "asset_type": asset_type,
                "content": content,
                "target_ip": profile.src_ip,
                "industry": industry,
                "intent": profile.classified_intent,
                "created_at": time.time(),
            }
            db.gadcf_assets.insert_one(asset_doc)
            assets.append(asset_doc)
        return assets
```

---

## Dashboard Integration

The **GADCF** section of the dashboard shows:

- **Asset library** — chronological list of generated assets with type, target IP, and content preview
- **Manual generation** — admin can trigger generation for a specific IP with optional asset type override (calls `POST /api/gadcf/generate`)

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/gadcf/assets` | GET | — | Recent generated assets |
| `/api/gadcf/generate` | POST | admin | Trigger generation for a specific IP |

### Generate Request

```json
{ "src_ip": "203.0.113.45", "asset_type": "env_file" }
```

`asset_type` is optional; if omitted, the engine selects based on intent.

---

## Enabling LLM Mode

By default, GADCF uses template fallback. To enable Ollama:

```bash
# Install Ollama on the host
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral

# Set in .env
OLLAMA_HOST=http://host.docker.internal:11434
```

LLM mode produces more varied and context-aware content but requires Ollama to be running and the model to be pulled.
