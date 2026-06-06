"""
deception_engine.py — Core deception engine: generates and manages personalized
honeypot environments tailored to classified attacker profiles.
"""

from __future__ import annotations
import uuid
import time
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional

from ..behavior.attacker_profile import AttackerProfile
from .credential_generator import CredentialGenerator

logger = logging.getLogger(__name__)

# Environment templates keyed by attacker tier
ENV_TEMPLATES = {
    "beginner": {
        "os_banner": "Ubuntu 20.04.6 LTS",
        "hostname": "web-server-01",
        "services": ["ssh", "http"],
        "fake_data_level": "minimal",
        "description": "Simple Ubuntu web server with minimal footprint",
    },
    "automated_bot": {
        "os_banner": "CentOS Linux 7 (Core)",
        "hostname": "db-primary-02",
        "services": ["ssh", "http", "mysql", "ftp"],
        "fake_data_level": "standard",
        "description": "Database server with common credentials and readable config files",
    },
    "advanced_human": {
        "os_banner": "Debian GNU/Linux 11 (bullseye)",
        "hostname": "prod-app-cluster-03",
        "services": ["ssh", "http", "https", "mysql", "redis", "docker"],
        "fake_data_level": "rich",
        "description": "Corporate app server with AWS creds, .env files, and sensitive data",
    },
}


@dataclass
class DeceptionEnvironment:
    env_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    src_ip: str = ""
    attacker_tier: str = "beginner"
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True
    container_id: Optional[str] = None
    assigned_port: Optional[int] = None
    os_banner: str = ""
    hostname: str = ""
    services: list[str] = field(default_factory=list)
    generated_credentials: list[dict] = field(default_factory=list)
    env_file_content: str = ""
    history_content: str = ""
    engagement_log: list[dict] = field(default_factory=list)

    def log_engagement(self, action: str, details: str = ""):
        self.engagement_log.append({
            "timestamp": time.time(),
            "action": action,
            "details": details,
        })
        self.last_activity = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class DeceptionEngine:
    """
    Manages the full lifecycle of deception environments:
      generate → deploy → monitor → teardown

    Usage:
        engine = DeceptionEngine(db)
        env = engine.generate_environment(attacker_profile)
        engine.teardown(env.env_id)
    """

    ENV_TIMEOUT_SECS = 3600      # auto-teardown after 1 hour of inactivity
    MAX_ACTIVE_ENVS = 20

    def __init__(self, db, docker_client=None):
        self.db = db
        self.docker = docker_client
        self._active: dict[str, DeceptionEnvironment] = {}
        self._lock = threading.Lock()
        self._gc_thread = threading.Thread(target=self._gc_loop, daemon=True, name="deception-gc")
        self._gc_thread.start()

    def generate_environment(self, profile: AttackerProfile) -> DeceptionEnvironment:
        """
        Create a personalized honeypot environment for the given attacker profile.
        Returns within ~30 seconds (target from project spec).
        """
        tier = profile.attacker_tier
        template = ENV_TEMPLATES.get(tier, ENV_TEMPLATES["beginner"])
        cred_gen = CredentialGenerator(seed=hash(profile.src_ip) % (2**31))

        env = DeceptionEnvironment(
            src_ip=profile.src_ip,
            attacker_tier=tier,
            os_banner=template["os_banner"],
            hostname=template["hostname"],
            services=template["services"],
            generated_credentials=cred_gen.generate_ssh_users(count=5),
            env_file_content=cred_gen.generate_env_file(tier=tier),
            history_content=cred_gen.generate_history_file(tier=tier),
        )

        # Apply personalization based on detected TTPs
        env = self._personalize_from_ttps(env, profile.ttps)

        # Try to spawn a Docker container if Docker is available
        if self.docker:
            try:
                env.container_id = self._spawn_container(env)
                logger.info("Spawned container %s for env %s", env.container_id[:12], env.env_id)
            except Exception as exc:
                logger.warning("Docker spawn failed (running in mock mode): %s", exc)

        with self._lock:
            if len(self._active) >= self.MAX_ACTIVE_ENVS:
                self._evict_oldest()
            self._active[env.env_id] = env

        self._persist(env)
        logger.info(
            "Environment %s created for %s (tier=%s services=%s)",
            env.env_id, profile.src_ip, tier, env.services,
        )
        return env

    def get_active_environments(self) -> list[DeceptionEnvironment]:
        with self._lock:
            return list(self._active.values())

    def get_environment(self, env_id: str) -> Optional[DeceptionEnvironment]:
        with self._lock:
            return self._active.get(env_id)

    def log_activity(self, env_id: str, action: str, details: str = ""):
        with self._lock:
            env = self._active.get(env_id)
        if env:
            env.log_engagement(action, details)
            self._persist(env)

    def teardown(self, env_id: str):
        with self._lock:
            env = self._active.pop(env_id, None)
        if not env:
            return
        env.is_active = False

        if self.docker and env.container_id:
            try:
                container = self.docker.containers.get(env.container_id)
                container.stop(timeout=5)
                container.remove()
                logger.info("Container %s removed", env.container_id[:12])
            except Exception as exc:
                logger.warning("Failed to remove container: %s", exc)

        self._persist(env)
        logger.info("Environment %s torn down (engaged for %.0fs)", env_id, time.time() - env.created_at)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _personalize_from_ttps(self, env: DeceptionEnvironment, ttps: list[dict]) -> DeceptionEnvironment:
        tactic_set = {t.get("tactic", "") for t in ttps}

        if "Lateral Movement" in tactic_set:
            env.hostname = "internal-jump-host"
            if "redis" not in env.services:
                env.services.append("redis")

        if "Credential Access" in tactic_set:
            env.hostname += "-auth"

        if "Impact" in tactic_set or "Command and Control" in tactic_set:
            env.fake_data_level = "rich"

        return env

    def _spawn_container(self, env: DeceptionEnvironment) -> str:
        container = self.docker.containers.run(
            "cowrie/cowrie:latest",
            detach=True,
            remove=False,
            name=f"neurotrap-env-{env.env_id}",
            labels={"neurotrap_env_id": env.env_id, "neurotrap_src_ip": env.src_ip},
            environment={
                "COWRIE_HOSTNAME": env.hostname,
            },
        )
        return container.id

    def _persist(self, env: DeceptionEnvironment):
        try:
            doc = env.to_dict()
            # Upsert by src_ip so each attacker has exactly one environment record.
            # Using env_id would create a new row on every generate_environment() call.
            self.db["deception_environments"].update_one(
                {"src_ip": env.src_ip},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.error("Failed to persist environment %s: %s", env.env_id, exc)

    def _evict_oldest(self):
        if not self._active:
            return
        oldest_id = min(self._active, key=lambda eid: self._active[eid].last_activity)
        logger.info("Evicting oldest environment %s to make room", oldest_id)
        self.teardown(oldest_id)

    def _gc_loop(self):
        while True:
            time.sleep(60)
            now = time.time()
            with self._lock:
                stale = [
                    eid for eid, env in self._active.items()
                    if (now - env.last_activity) > self.ENV_TIMEOUT_SECS
                ]
            for eid in stale:
                logger.info("GC: timing out environment %s", eid)
                self.teardown(eid)
