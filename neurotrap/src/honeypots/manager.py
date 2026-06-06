"""
manager.py — Starts and supervises the full set of native honeypots.

The manager wires every honeypot to the shared DB layer and an optional event
sink (used by the Flask API to stream captures to the dashboard in real time),
then starts them on their configured ports. It is the single object the rest of
the system talks to when it wants honeypots running in-process.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import EventSink
from .ftp_honeypot import FTPHoneypot
from .http_honeypot import HTTPHoneypot
from .ssh_honeypot import SSHHoneypot
from .telnet_honeypot import TelnetHoneypot

logger = logging.getLogger(__name__)

HONEYPOT_TYPES = {
    "ssh": SSHHoneypot,
    "http": HTTPHoneypot,
    "ftp": FTPHoneypot,
    "telnet": TelnetHoneypot,
}


class HoneypotManager:
    def __init__(
        self,
        db=None,
        host: str = "0.0.0.0",
        event_sink: Optional[EventSink] = None,
        ports: Optional[dict[str, int]] = None,
    ):
        self.db = db
        self.host = host
        self.event_sink = event_sink
        self.ports = ports or {}
        self.honeypots: dict[str, object] = {}

    def build(self, enabled: Optional[list[str]] = None) -> "HoneypotManager":
        names = enabled or list(HONEYPOT_TYPES)
        for name in names:
            cls = HONEYPOT_TYPES.get(name)
            if cls is None:
                logger.warning("Unknown honeypot type %r, skipping", name)
                continue
            self.honeypots[name] = cls(
                host=self.host,
                port=self.ports.get(name),
                db=self.db,
                event_sink=self.event_sink,
            )
        return self

    def start(self):
        for name, hp in self.honeypots.items():
            try:
                hp.start()
            except OSError as exc:
                logger.error("Could not start %s honeypot on port %s: %s",
                             name, getattr(hp, "port", "?"), exc)

    def stop(self):
        for hp in self.honeypots.values():
            hp.stop()

    def status(self) -> list[dict]:
        return [
            {"name": name, "port": hp.port, "running": hp._running}
            for name, hp in self.honeypots.items()
        ]
