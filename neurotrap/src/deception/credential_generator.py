"""
credential_generator.py — Generates realistic but fake credentials, files,
and environment data for populating deception environments.
"""

from __future__ import annotations
import random as _random_module
import string
import hashlib
from typing import Optional

try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    Faker = None
    FAKER_AVAILABLE = False


class CredentialGenerator:
    """Generates fake credentials and data seeded for a specific attacker tier."""

    COMMON_USERNAMES = [
        "admin", "root", "ubuntu", "ec2-user", "deploy", "git",
        "postgres", "mysql", "www-data", "jenkins", "docker",
    ]

    def __init__(self, seed: Optional[int] = None):
        # Instance-level Random so each generator is independently reproducible
        self._rng = _random_module.Random(seed)
        if FAKER_AVAILABLE:
            self._faker = Faker()
            self._faker.seed_instance(seed if seed is not None else 0)
        else:
            self._faker = None

    def _fake(self, method: str, *args, fallback="placeholder") -> str:
        if not self._faker:
            return fallback
        return getattr(self._faker, method)(*args)

    def generate_ssh_users(self, count: int = 5) -> list[dict]:
        users = []
        for _ in range(count):
            username = (
                self._rng.choice(self.COMMON_USERNAMES) if self._rng.random() < 0.4
                else self._fake("user_name", fallback="user" + str(self._rng.randint(100, 999)))
            )
            password = self._plausible_password()
            users.append({
                "username": username,
                "password": password,
                "shadow_hash": self._shadow_hash(password),
            })
        return users

    def generate_aws_credentials(self) -> dict:
        key_id = "AKIA" + "".join(self._rng.choices(string.ascii_uppercase + string.digits, k=16))
        secret = "".join(self._rng.choices(string.ascii_letters + string.digits + "/+", k=40))
        return {
            "AWS_ACCESS_KEY_ID": key_id,
            "AWS_SECRET_ACCESS_KEY": secret,
            "AWS_DEFAULT_REGION": self._rng.choice(["us-east-1", "us-west-2", "eu-west-1"]),
        }

    def generate_database_credentials(self) -> dict:
        return {
            "DB_HOST": "db.internal",
            "DB_PORT": self._rng.choice([3306, 5432]),
            "DB_NAME": self._fake("word", fallback="appdb"),
            "DB_USER": self._fake("user_name", fallback="dbadmin"),
            "DB_PASS": self._plausible_password(length=16),
        }

    def generate_env_file(self, tier: str = "beginner") -> str:
        aws = self.generate_aws_credentials()
        db = self.generate_database_credentials()
        api_key = "".join(self._rng.choices(string.hexdigits, k=32))
        jwt_secret = "".join(self._rng.choices(string.ascii_letters + string.digits, k=48))

        lines = [
            "# Application Configuration",
            f"APP_ENV={'staging' if tier == 'beginner' else 'production'}",
            f"SECRET_KEY={jwt_secret}",
            f"API_KEY={api_key}",
            "",
            "# Database",
        ] + [f"{k}={v}" for k, v in db.items()]

        if tier in ("advanced_human", "automated_bot"):
            lines += ["", "# AWS Credentials"] + [f"{k}={v}" for k, v in aws.items()]

        return "\n".join(lines)

    def generate_fake_shadow(self, user_count: int = 8) -> str:
        entries = []
        system_users = ["root", "daemon", "bin", "sys", "nobody"]
        for u in system_users:
            entries.append(f"{u}:!:19000:0:99999:7:::")
        for user in self.generate_ssh_users(user_count - len(system_users)):
            entries.append(f"{user['username']}:{user['shadow_hash']}:19000:0:99999:7:::")
        return "\n".join(entries)

    def generate_history_file(self, tier: str = "beginner") -> str:
        common = [
            "ls -la", "cd /var/www", "git pull", "sudo systemctl restart nginx",
            "df -h", "free -m", "ps aux", "top",
        ]
        advanced = [
            "aws s3 ls", "kubectl get pods", "terraform plan",
            "ansible-playbook deploy.yml", "docker-compose up -d",
        ]
        commands = common + (advanced if tier != "beginner" else [])
        self._rng.shuffle(commands)
        return "\n".join(commands[:15])

    def _plausible_password(self, length: int = 12) -> str:
        chars = string.ascii_letters + string.digits + "!@#$"
        return "".join(self._rng.choices(chars, k=length))

    def _shadow_hash(self, password: str) -> str:
        salt = "".join(self._rng.choices(string.ascii_letters + string.digits, k=8))
        h = hashlib.sha512((salt + password).encode()).hexdigest()[:43]
        return f"$6${salt}${h}"
