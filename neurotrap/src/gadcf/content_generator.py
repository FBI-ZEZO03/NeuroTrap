"""
content_generator.py — LLM-powered fake asset generator.

Primary: Ollama (Llama 3.1 / Mistral) via local API.
Fallback: Jinja2 template library (no external dependency).

Generates contextually coherent fake assets per attacker profile:
  - Source code repositories with realistic comments
  - Corporate email threads
  - .env / secrets files with format-valid fake values
  - Internal wiki / Confluence-style pages
  - Database schemas with plausible data
"""

from __future__ import annotations
import logging
import random
import string
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from src.soc_analyst.llm_client import llm_complete, llm_available
except ImportError:
    def llm_complete(*a, **kw): return None  # type: ignore[misc]
    def llm_available() -> bool: return False  # type: ignore[misc]

GADCF_MODEL_SYSTEM = (
    "You are a red-team content generator. Produce realistic fake corporate files "
    "for honeypot deception. Output ONLY the file content — no explanations, no markdown fences."
)


@dataclass
class GeneratedAsset:
    asset_id: str
    asset_type: str          # code_repo | email_thread | env_file | wiki_page | db_schema
    filename: str
    content: str
    industry: str
    attacker_intent: str
    generated_at: float = field(default_factory=time.time)
    source: str = "template"  # "llm" or "template"

    def to_dict(self) -> dict:
        return asdict(self)


class ContentGenerator:
    """
    Generates coherent fake asset packages for a given attacker profile.

    Usage:
        gen = ContentGenerator()
        assets = gen.generate_package(
            industry="financial_services",
            attacker_intent="credential_harvesting",
            sophistication="advanced_human"
        )
    """

    INDUSTRIES = ["financial_services", "healthcare", "e_commerce", "saas_startup", "government", "energy"]

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and llm_available()

    def generate_package(
        self,
        industry: str = "saas_startup",
        attacker_intent: str = "credential_harvesting",
        sophistication: str = "advanced_human",
    ) -> list[GeneratedAsset]:
        assets = []
        generators = [
            self._gen_env_file,
            self._gen_email_thread,
            self._gen_code_repo,
            self._gen_wiki_page,
            self._gen_db_schema,
        ]
        for i, gen_fn in enumerate(generators):
            try:
                asset = gen_fn(industry, attacker_intent, sophistication)
                if asset:
                    assets.append(asset)
            except Exception as exc:
                logger.warning("Asset generation failed for %s: %s", gen_fn.__name__, exc)
        return assets

    # ── LLM generation ─────────────────────────────────────────────────────────

    def _llm_generate(self, prompt: str, max_tokens: int = 700) -> Optional[str]:
        if not self.use_llm:
            return None
        result = llm_complete(
            system=GADCF_MODEL_SYSTEM,
            user=prompt,
            max_tokens=max_tokens,
            temperature=0.8,
        )
        if result:
            logger.debug("GADCF LLM generated %d chars", len(result))
        return result

    # ── Asset generators ───────────────────────────────────────────────────────

    def _gen_env_file(self, industry: str, intent: str, sophistication: str) -> GeneratedAsset:
        aid = _uid()
        content = self._llm_generate(
            f"Generate a realistic .env file for a {industry} company's production backend. "
            f"Include database credentials, API keys, payment gateway secrets, and cloud provider credentials. "
            f"Make all values format-valid but fake. No explanations, just the .env content."
        ) or self._template_env(industry)

        return GeneratedAsset(aid, "env_file", f".env.{industry.replace('_','-')}.production",
                              content, industry, intent, source="llm" if (self.use_llm and llm_available()) else "template")

    def _gen_email_thread(self, industry: str, intent: str, sophistication: str) -> GeneratedAsset:
        aid = _uid()
        content = self._llm_generate(
            f"Generate a realistic internal corporate email thread (3-4 emails) for a {industry} company. "
            f"The thread should discuss credential management or system access. Include realistic names, "
            f"job titles, and internal references. Make it look like a real leaked email thread."
        ) or self._template_email(industry)

        return GeneratedAsset(aid, "email_thread", f"IT_thread_{_uid(4)}.eml",
                              content, industry, intent, source="llm" if (self.use_llm and llm_available()) else "template")

    def _gen_code_repo(self, industry: str, intent: str, sophistication: str) -> GeneratedAsset:
        aid = _uid()
        content = self._llm_generate(
            f"Generate a realistic Python Flask API file for a {industry} backend. "
            f"Include database connection with hardcoded fallback credentials, API key validation, "
            f"and realistic internal comments mentioning other systems. Make it look like real production code."
        ) or self._template_code(industry)

        return GeneratedAsset(aid, "code_repo", f"app_{_uid(4)}.py",
                              content, industry, intent, source="llm" if (self.use_llm and llm_available()) else "template")

    def _gen_wiki_page(self, industry: str, intent: str, sophistication: str) -> GeneratedAsset:
        aid = _uid()
        content = self._llm_generate(
            f"Generate a realistic internal Confluence wiki page for a {industry} company's "
            f"infrastructure runbook. Include server hostnames, IP ranges, service account names, "
            f"and system access procedures. Markdown format."
        ) or self._template_wiki(industry)

        return GeneratedAsset(aid, "wiki_page", f"RUNBOOK_{industry.upper()}_{_uid(4)}.md",
                              content, industry, intent, source="llm" if (self.use_llm and llm_available()) else "template")

    def _gen_db_schema(self, industry: str, intent: str, sophistication: str) -> GeneratedAsset:
        aid = _uid()
        content = _TEMPLATES["db_schema"][industry] if industry in _TEMPLATES["db_schema"] \
            else _TEMPLATES["db_schema"]["saas_startup"]

        return GeneratedAsset(aid, "db_schema", f"schema_dump_{_uid(4)}.sql",
                              content, industry, intent, source="template")

    # ── Fallback templates ─────────────────────────────────────────────────────

    @staticmethod
    def _template_env(industry: str) -> str:
        return _TEMPLATES["env"].get(industry, _TEMPLATES["env"]["saas_startup"])

    @staticmethod
    def _template_email(industry: str) -> str:
        return _TEMPLATES["email"].get(industry, _TEMPLATES["email"]["saas_startup"])

    @staticmethod
    def _template_code(industry: str) -> str:
        return _TEMPLATES["code"].get(industry, _TEMPLATES["code"]["saas_startup"])

    @staticmethod
    def _template_wiki(industry: str) -> str:
        return _TEMPLATES["wiki"].get(industry, _TEMPLATES["wiki"]["saas_startup"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uid(n: int = 8) -> str:
    return "".join(random.choices(string.hexdigits[:16], k=n))


# ── Template library ──────────────────────────────────────────────────────────

_TEMPLATES: dict = {
    "env": {
        "financial_services": """\
# Apex Financial Services — Production Environment
# DO NOT COMMIT — Rotate every 90 days per PCI-DSS policy

APP_ENV=production
APP_SECRET=fXk9mN2qRsT7uVwXyZ1aB3cD5eF6gH8i

# PostgreSQL — prod-db-01.apex-internal.net
DB_HOST=prod-db-01.apex-internal.net
DB_PORT=5432
DB_NAME=apex_core
DB_USER=apex_svc_prod
DB_PASS=Ap3x$Pr0d_2026!#SecureDB

# AWS (us-east-1 — primary)
AWS_ACCESS_KEY_ID=AKIAQWERTY12345ZXCVB
AWS_SECRET_ACCESS_KEY=aB3cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5yZ

# Stripe Payment Gateway
STRIPE_PUBLIC_KEY=pk_live_51HxYz2LkMnOpQrStUvWxYz
STRIPE_SECRET_KEY=<REPLACE_WITH_REAL_STRIPE_KEY>

# Redis Cache
REDIS_URL=redis://:R3d!sCach3_P@ss@redis-prod.apex-internal.net:6379/0

# JWT
JWT_SECRET=9f4a7b2c1e8d5f3a6c9b2e5f8a1d4c7b
JWT_EXPIRY=3600
""",
        "saas_startup": """\
# TechFlow SaaS — Production .env
# Last rotated: 2026-05-01 | Rotate by: 2026-08-01
# Owner: devops@techflow.io

APP_ENV=production
SECRET_KEY=tfS3cr3t_K3y_Pr0d_2026_!@#
DEBUG=False

# MongoDB Atlas
MONGO_URI=mongodb+srv://tf_admin:Tf@Atlas_2026!@cluster0.abc123.mongodb.net/techflow_prod

# SendGrid
SENDGRID_API_KEY=SG.aBcDeFgHiJkLmNoPqRsTuVwXyZ.1234567890abcdefghijklmnopqrstuv

# GitHub OAuth
GITHUB_CLIENT_ID=a1b2c3d4e5f6g7h8i9j0
GITHUB_CLIENT_SECRET=ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Stripe
STRIPE_SECRET=<REPLACE_WITH_REAL_STRIPE_KEY>

# AWS S3 Uploads
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_BUCKET=techflow-user-uploads-prod
""",
    },
    "email": {
        "saas_startup": """\
From: Sarah Chen <s.chen@techflow.io>
To: DevOps Team <devops@techflow.io>
Date: Mon, 02 Jun 2026 09:14:22 +0000
Subject: RE: Emergency credential rotation — prod DB

Team,

Following the security advisory from last Friday, we need to rotate the prod credentials ASAP.
Current prod DB password is Tf@Atlas_2026! — I've already updated the .env on prod-app-01 and prod-app-02.

James, can you update the backup runner on cron-01? The script is at /home/deploy/scripts/backup_db.sh

Also don't forget the Redis password: R3d!sCach3_P@ss — this one hasn't been rotated since March.

The new creds will be emailed separately via LastPass.

Sarah

---

From: James Okafor <j.okafor@techflow.io>
To: Sarah Chen <s.chen@techflow.io>
Date: Mon, 02 Jun 2026 09:42:55 +0000
Subject: RE: Emergency credential rotation — prod DB

Sarah,

Done on cron-01. I also noticed the staging .env still has the old password. Should I rotate that too?

Also, the S3 bucket credentials haven't been in the rotation policy — the key AKIAIOSFODNN7EXAMPLE
is still in the Terraform state at /opt/terraform/prod/terraform.tfstate

Let me know.

James
""",
        "financial_services": """\
From: Michael Torres <m.torres@apexfinancial.com>
To: IT Security <security@apexfinancial.com>
CC: David Lim <d.lim@apexfinancial.com>
Date: Tue, 03 Jun 2026 14:22:11 +0000
Subject: URGENT — PCI Audit Prep: Credential Inventory

All,

Ahead of the PCI-DSS audit on June 10, I need a full inventory of production credentials.
Per our policy, the following MUST be rotated before the audit:

1. prod-db-01 service account (apex_svc_prod) — last rotated 2026-02-14
2. Stripe live keys — never rotated (original from 2024 launch)
3. AWS IAM key for backup job — AKIAQWERTY12345ZXCVB

David — the Stripe secret is stored in KMS but there's a plaintext copy in /etc/app/.stripe_backup
that was created during the January outage. Please remove that ASAP.

The AWS key above has AdministratorAccess — this was supposed to be scoped down months ago.

Michael Torres
VP Engineering, Apex Financial Services
""",
    },
    "code": {
        "saas_startup": '''\
"""TechFlow API — Core authentication service"""
from flask import Flask, request, jsonify
import psycopg2, jwt, os

app = Flask(__name__)

# TODO: move to env vars before next audit (JIRA TF-2841)
_DB_FALLBACK = {
    "host": "prod-db-01.apex-internal.net",
    "dbname": "apex_core",
    "user": "apex_svc_prod",
    "password": "Tf@Atlas_2026!#SecureDB"   # prod creds — rotate by Aug 2026
}

def get_db():
    uri = os.getenv("DATABASE_URL")
    if not uri:
        return psycopg2.connect(**_DB_FALLBACK)
    return psycopg2.connect(uri)

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, role FROM users WHERE email=%s AND password_hash=crypt(%s, password_hash)",
        (data["email"], data["password"])
    )
    user = cur.fetchone()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token = jwt.encode(
        {"user_id": user[0], "role": user[1]},
        os.getenv("JWT_SECRET", "9f4a7b2c1e8d5f3a6c9b2e5f8a1d4c7b"),
        algorithm="HS256"
    )
    return jsonify({"token": token})

# Internal admin endpoint — protected by network ACL only (no auth)
# Accessible from: 10.0.0.0/8
@app.route("/internal/admin/users", methods=["GET"])
def list_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 1000")
    return jsonify({"users": cur.fetchall()})
''',
    },
    "wiki": {
        "saas_startup": """\
# TechFlow Infrastructure Runbook
**Classification:** Internal Only | **Last updated:** 2026-06-01

## Production Servers

| Hostname | IP | Role | Access |
|---|---|---|---|
| prod-app-01 | 10.0.1.10 | Primary API | SSH via jump-01 |
| prod-app-02 | 10.0.1.11 | Secondary API | SSH via jump-01 |
| prod-db-01  | 10.0.2.10 | PostgreSQL primary | prod-app-* only |
| cron-01     | 10.0.1.50 | Scheduled jobs | SSH via jump-01 |
| jump-01     | 203.0.113.5 | SSH jump host | Public internet |

## SSH Access
Jump host: `ssh -J deploy@203.0.113.5 deploy@prod-app-01`
SSH key: `/home/admin/.ssh/id_rsa_deploy` (passphrase in 1Password vault "TechFlow Prod")

## Database Access
```
Host: prod-db-01.apex-internal.net
Port: 5432
DB:   techflow_prod
User: tf_admin (read-write)
Pass: See vault entry "DB Prod Admin" — or /etc/app/.dbpass on prod-app-01
```

## Emergency Procedures
If prod-db-01 is unreachable: connect to replica at 10.0.2.11 (read-only)
Redis flush (CAUTION): `redis-cli -h redis-prod -a R3d!sCach3_P@ss FLUSHDB`

## Service Account Passwords (rotate quarterly)
- `svc_backup`: B@ckup_Svc_2026! (cron jobs)
- `svc_monitor`: M0n!tor_Svc_2026 (Prometheus)
- `apex_svc_prod`: Ap3x$Pr0d_2026!#SecureDB (app DB user)
""",
    },
    "db_schema": {
        "saas_startup": """\
-- TechFlow Production Database Dump
-- Generated: 2026-06-01 03:00:01 UTC
-- Host: prod-db-01.apex-internal.net
-- Database: techflow_prod

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role        VARCHAR(50) DEFAULT 'user',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Sample data (sanitized for staging)
INSERT INTO users (email, password_hash, role) VALUES
('admin@techflow.io',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMPybZSZCzDAoiZIHMqNqGqxK6', 'superadmin'),
('j.okafor@techflow.io', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin'),
('s.chen@techflow.io',   '$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL57TjTK', 'admin');

CREATE TABLE api_keys (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    key_hash    TEXT NOT NULL,
    scopes      TEXT[],
    created_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP
);

CREATE TABLE payment_methods (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    stripe_customer TEXT,
    last4           CHAR(4),
    brand           VARCHAR(20),
    exp_month       SMALLINT,
    exp_year        SMALLINT
);
""",
    },
}
