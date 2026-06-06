"""
base.py — Shared machinery for NeuroTrap's native Python honeypots.

These are self-contained, low/medium-interaction honeypots that run anywhere
Python runs (no Docker required) and feed the exact same data path as the
external Cowrie/Dionaea honeypots: every interesting interaction is normalised
into an `AlertEvent` and written to the `alert_events` collection through the
central DB layer (Mongo or the embedded fallback). A lightweight session record
is also kept in `honeypot_sessions` so the behaviour engine can profile
attackers per source IP.

Subclasses implement `handle_client(conn, addr, session)` for their protocol.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

from ..detection.alert_schema import AlertEvent

logger = logging.getLogger(__name__)

# Optional hook so the API can stream live events to the dashboard via WebSocket.
EventSink = Callable[[dict], None]


@dataclass
class HoneypotSession:
    """One TCP connection / attacker engagement with a honeypot."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    src_ip: str = "0.0.0.0"
    src_port: int = 0
    honeypot: str = ""          # ssh | http | ftp | telnet
    dst_port: int = 0
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    credentials: list[dict] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    events: int = 0
    analyzed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BaseHoneypot:
    """
    Threaded TCP honeypot base class.

    Subclasses set `name`, `default_port`, `banner` (optional) and implement
    `handle_client`. Call `start()` to bind and serve in a background thread;
    `stop()` to shut down. Captured activity is recorded via `record_event`.
    """

    name: str = "base"
    default_port: int = 0
    banner: bytes = b""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: Optional[int] = None,
        db=None,
        event_sink: Optional[EventSink] = None,
    ):
        self.host = host
        self.port = port if port is not None else self.default_port
        self._db = db
        self._event_sink = event_sink
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── lifecycle ───────────────────────────────────────────────────────────────

    @property
    def db(self):
        if self._db is None:
            from ..db import get_db
            self._db = get_db()
        return self._db

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        # Reflect the actually-bound port (useful when port=0 in tests).
        self.port = self._sock.getsockname()[1]
        self._sock.listen(50)
        self._sock.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(
            target=self._serve, daemon=True, name=f"honeypot-{self.name}"
        )
        self._thread.start()
        logger.info("[%s] honeypot listening on %s:%d", self.name, self.host, self.port)
        return self

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("[%s] honeypot stopped", self.name)

    def _serve(self):
        while self._running:
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._client_wrapper, args=(conn, addr), daemon=True
            ).start()

    def _client_wrapper(self, conn: socket.socket, addr):
        src_ip, src_port = addr[0], addr[1]
        session = HoneypotSession(
            src_ip=src_ip, src_port=src_port, honeypot=self.name, dst_port=self.port
        )
        try:
            conn.settimeout(15.0)
            if self.banner:
                conn.sendall(self.banner)
            self.handle_client(conn, addr, session)
        except (socket.timeout, ConnectionError, OSError):
            pass
        except Exception as exc:  # never let one client kill the listener
            logger.debug("[%s] handler error from %s: %s", self.name, src_ip, exc)
        finally:
            session.ended_at = time.time()
            self._persist_session(session)
            try:
                conn.close()
            except OSError:
                pass

    # ── subclass entry point ────────────────────────────────────────────────────

    def handle_client(self, conn: socket.socket, addr, session: HoneypotSession):
        raise NotImplementedError

    # ── recording ───────────────────────────────────────────────────────────────

    def record_event(
        self,
        session: HoneypotSession,
        attack_type: str,
        severity: str = "low",
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        command: Optional[str] = None,
        protocol: Optional[str] = None,
        raw_payload: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> AlertEvent:
        """Normalise an interaction into an AlertEvent and persist it."""
        event = AlertEvent(
            src_ip=session.src_ip,
            src_port=session.src_port,
            dst_port=self.port,
            attack_type=attack_type,
            severity=severity,
            honeypot_source=self.name,
            protocol=protocol or self.name,
            session_id=session.session_id,
            username=username,
            password=password,
            command=command,
            raw_payload=raw_payload,
            extra=extra or {},
        )
        session.events += 1
        if username is not None or password is not None:
            session.credentials.append({"username": username, "password": password,
                                        "timestamp": time.time()})
        if command:
            session.commands.append(command)

        doc = event.to_dict()
        try:
            self.db["alert_events"].update_one(
                {"event_id": doc["event_id"]}, {"$set": doc}, upsert=True
            )
        except Exception as exc:
            logger.error("[%s] failed to persist event: %s", self.name, exc)

        if self._event_sink:
            try:
                self._event_sink(doc)
            except Exception:
                pass

        logger.info(
            "[%s] %s from %s (%s)", self.name, attack_type, session.src_ip, severity
        )
        return event

    def _persist_session(self, session: HoneypotSession):
        try:
            self.db["honeypot_sessions"].update_one(
                {"session_id": session.session_id},
                {"$set": session.to_dict()},
                upsert=True,
            )
        except Exception as exc:
            logger.error("[%s] failed to persist session: %s", self.name, exc)


# ── small socket helpers ─────────────────────────────────────────────────────────


def recv_line(conn: socket.socket, max_bytes: int = 4096) -> str:
    """Read a single CRLF/LF-terminated line, decoded leniently."""
    data = bytearray()
    while len(data) < max_bytes:
        chunk = conn.recv(1)
        if not chunk:
            break
        if chunk in (b"\n",):
            break
        if chunk == b"\r":
            continue
        data += chunk
    return data.decode("utf-8", errors="replace").strip()
