"""
ssh_honeypot.py — SSH honeypot with two interaction levels.

  * If `paramiko` is installed it runs a real SSH transport, completing the
    handshake and capturing every username/password an attacker submits
    (medium-interaction). All auth attempts are rejected so brute-forcers keep
    feeding credentials.
  * If paramiko is unavailable it degrades to a low-interaction banner honeypot:
    it presents an OpenSSH banner and logs the client's version string and
    connection attempt (useful for tool fingerprinting / scan detection).

Either way the data lands in `alert_events` exactly like the other honeypots.
"""

from __future__ import annotations

import logging
import socket
import threading

from .base import BaseHoneypot, HoneypotSession

logger = logging.getLogger(__name__)

SSH_BANNER = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SSHHoneypot(BaseHoneypot):
    name = "ssh"
    default_port = 2222  # mapped to :22 in Docker

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._host_key = None
        if PARAMIKO_AVAILABLE:
            # Ephemeral host key; persistence isn't needed for a honeypot.
            self._host_key = paramiko.RSAKey.generate(2048)

    def handle_client(self, conn: socket.socket, addr, session: HoneypotSession):
        if PARAMIKO_AVAILABLE:
            self._handle_paramiko(conn, session)
        else:
            self._handle_banner(conn, session)

    # ── medium interaction (paramiko) ───────────────────────────────────────────

    def _handle_paramiko(self, conn: socket.socket, session: HoneypotSession):
        transport = paramiko.Transport(conn)
        transport.local_version = SSH_BANNER
        transport.add_server_key(self._host_key)
        server = _CaptureServer(self, session)
        try:
            transport.start_server(server=server)
            # Give the client time to attempt auth; the server object records it.
            chan = transport.accept(20)
            if chan is not None:
                chan.close()
            server.done.wait(timeout=20)
        except (paramiko.SSHException, EOFError, OSError):
            pass
        finally:
            try:
                transport.close()
            except Exception:
                pass

    # ── low interaction (banner only) ───────────────────────────────────────────

    def _handle_banner(self, conn: socket.socket, session: HoneypotSession):
        try:
            conn.sendall((SSH_BANNER + "\r\n").encode())
            conn.settimeout(8.0)
            client_banner = conn.recv(256).decode("utf-8", errors="replace").strip()
        except OSError:
            client_banner = ""
        self.record_event(
            session,
            attack_type="tool_fingerprint",
            severity="low",
            command="ssh_connect",
            protocol="ssh",
            raw_payload=client_banner or None,
            extra={"client_version": client_banner, "mode": "banner-only"},
        )


if PARAMIKO_AVAILABLE:

    class _CaptureServer(paramiko.ServerInterface):
        """Paramiko server that logs credentials and always rejects auth."""

        def __init__(self, honeypot: SSHHoneypot, session: HoneypotSession):
            self.honeypot = honeypot
            self.session = session
            self.done = threading.Event()

        def get_allowed_auths(self, username):
            return "password,publickey"

        def check_auth_password(self, username, password):
            self.honeypot.record_event(
                self.session,
                attack_type="brute_force",
                severity="medium",
                username=username,
                password=password,
                command="ssh_auth_password",
                protocol="ssh",
            )
            return paramiko.AUTH_FAILED

        def check_auth_publickey(self, username, key):
            self.honeypot.record_event(
                self.session,
                attack_type="tool_fingerprint",
                severity="low",
                username=username,
                command="ssh_auth_publickey",
                protocol="ssh",
                extra={"key_type": key.get_name()},
            )
            return paramiko.AUTH_FAILED

        def check_channel_request(self, kind, chanid):
            self.done.set()
            return paramiko.OPEN_SUCCEEDED if kind == "session" else \
                paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
