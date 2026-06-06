"""
Entry point for the Attacker Digital Twin engine.

    python -m src.twin.main

Periodically rebuilds every attacker twin from the latest honeypot captures and
profiles, keeping predictions and kill-chain progression current. Uses the
central DB layer (MongoDB or embedded fallback).
"""

from __future__ import annotations

import logging
import os
import time

from ..db import backend, get_db
from .digital_twin import AttackerDigitalTwin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("neurotrap.twin")


def main():
    db = get_db()
    logger.info("Storage backend: %s", backend())
    adt = AttackerDigitalTwin(db)
    interval = float(os.getenv("TWIN_REFRESH_SECS", "15"))

    logger.info("Attacker Digital Twin engine running — refresh every %.0fs", interval)
    try:
        while True:
            twins = adt.build_all()
            logger.info("Refreshed %d attacker twin(s)", len(twins))
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Digital Twin engine stopped")


if __name__ == "__main__":
    main()
