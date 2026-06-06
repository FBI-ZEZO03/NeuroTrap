"""
Entry point: run NeuroTrap's native honeypots standalone.

    python -m src.honeypots.main

Honeypots, ports and bind host are read from environment variables so the same
image works locally (high ports) and in Docker (privileged low ports). Captured
activity flows into the central DB layer — MongoDB if reachable, otherwise the
embedded SQLite fallback — so it works with zero infrastructure.

Env vars:
    HONEYPOT_HOST        bind address (default 0.0.0.0)
    HONEYPOTS_ENABLED    comma list: ssh,http,ftp,telnet (default all)
    HP_SSH_PORT / HP_HTTP_PORT / HP_FTP_PORT / HP_TELNET_PORT   per-protocol ports
"""

from __future__ import annotations

import logging
import os
import signal
import threading

from ..db import backend, get_db
from .manager import HONEYPOT_TYPES, HoneypotManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("neurotrap.honeypots")


def _ports_from_env() -> dict[str, int]:
    ports = {}
    for name in HONEYPOT_TYPES:
        env_key = f"HP_{name.upper()}_PORT"
        if os.getenv(env_key):
            try:
                ports[name] = int(os.environ[env_key])
            except ValueError:
                logger.warning("Invalid %s=%r, ignoring", env_key, os.environ[env_key])
    return ports


def main():
    db = get_db()
    logger.info("Storage backend: %s", backend())

    enabled = [s.strip() for s in os.getenv("HONEYPOTS_ENABLED", "ssh,http,ftp,telnet").split(",") if s.strip()]
    manager = HoneypotManager(
        db=db,
        host=os.getenv("HONEYPOT_HOST", "0.0.0.0"),
        ports=_ports_from_env(),
    ).build(enabled)

    manager.start()
    for s in manager.status():
        logger.info("  ✓ %-7s on port %s", s["name"], s["port"])

    stop = threading.Event()

    def _shutdown(*_):
        logger.info("Shutting down honeypots…")
        manager.stop()
        stop.set()

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (ValueError, AttributeError):
        pass

    logger.info("NeuroTrap honeypots running. Press Ctrl+C to stop.")
    stop.wait()


if __name__ == "__main__":
    main()
