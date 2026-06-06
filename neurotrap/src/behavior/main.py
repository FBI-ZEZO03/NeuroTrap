"""Entry point for the behavior-engine container."""

import logging
import time

from ..db import get_db, backend
from .behavior_engine import BehaviorEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("neurotrap.behavior")


def main():
    db = get_db()
    logger.info("Storage backend: %s", backend())

    engine = BehaviorEngine(db)
    engine.start()

    logger.info("BehaviorEngine running — polling for sessions…")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        engine.stop()
        logger.info("BehaviorEngine stopped")


if __name__ == "__main__":
    main()
