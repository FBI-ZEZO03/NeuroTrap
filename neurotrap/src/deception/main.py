"""Entry point for the deception-engine container."""

import logging
import time

from ..db import get_db, backend
from .deception_engine import DeceptionEngine
from ..behavior.attacker_profile import ProfileStore
from ..response.response_engine import ResponseEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("neurotrap.deception")


def main():
    db = get_db()
    logger.info("Storage backend: %s", backend())

    try:
        import docker
        docker_client = docker.from_env()
    except Exception:
        logger.warning("Docker SDK not available — running in mock mode")
        docker_client = None

    deception_engine = DeceptionEngine(db, docker_client=docker_client)
    response_engine = ResponseEngine(db)
    profile_store = ProfileStore(db["attacker_profiles"])

    logger.info("DeceptionEngine running — watching for new profiles…")

    from ..behavior.attacker_profile import AttackerProfile

    try:
        while True:
            # Build the set of IPs that already have a live environment this cycle.
            active_ips = {env.src_ip for env in deception_engine.get_active_environments()}

            profiles = profile_store.get_top_threats(limit=5)
            for p_dict in profiles:
                ip = p_dict.get("src_ip")
                if ip in active_ips:
                    continue

                profile = AttackerProfile(**{k: v for k, v in p_dict.items()
                                             if k in AttackerProfile.__dataclass_fields__})

                if profile.threat_score >= 10 and not profile.is_blocked:
                    deception_engine.generate_environment(profile)
                    decision = response_engine.evaluate(profile)
                    logger.info("Response for %s: %s", ip, decision.action)

            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("DeceptionEngine stopped")


if __name__ == "__main__":
    main()
