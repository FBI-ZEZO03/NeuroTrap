"""
telnet_honeypot.py — Low-interaction Telnet honeypot.

Mimics a BusyBox/embedded-device login prompt — the exact target IoT botnets
(Mirai and relatives) hammer. Captures username/password pairs and a few
post-login commands before disconnecting.
"""

from __future__ import annotations

import socket

from .base import BaseHoneypot, HoneypotSession, recv_line

_HOSTNAME = b"dvr-cam-07"


class TelnetHoneypot(BaseHoneypot):
    name = "telnet"
    default_port = 2323  # mapped to :23 in Docker

    def handle_client(self, conn: socket.socket, addr, session: HoneypotSession):
        conn.sendall(b"\r\n" + _HOSTNAME + b" login: ")
        username = recv_line(conn)
        conn.sendall(b"Password: ")
        password = recv_line(conn)

        self.record_event(
            session,
            attack_type="brute_force",
            severity="medium",
            username=username or None,
            password=password or None,
            command="telnet login",
            protocol="telnet",
        )

        # Common IoT default creds → pretend the login "worked" to capture the
        # follow-on payload commands botnets push.
        if (username, password) in (("root", "root"), ("root", "xc3511"),
                                    ("admin", "admin"), ("root", "vizxv")):
            conn.sendall(b"\r\nBusyBox v1.16.1 built-in shell (ash)\r\n")
            self._shell(conn, session)
        else:
            conn.sendall(b"\r\nLogin incorrect\r\n")

    def _shell(self, conn: socket.socket, session: HoneypotSession):
        for _ in range(15):
            conn.sendall(b"# ")
            line = recv_line(conn)
            if not line:
                break
            if line in ("exit", "quit"):
                break
            severity = "high" if any(t in line for t in
                                     ("wget", "tftp", "busybox", "/bin/busybox", "chmod", "cat /proc")) else "medium"
            self.record_event(
                session,
                attack_type="command_injection",
                severity=severity,
                command=line[:300],
                protocol="telnet",
            )
            conn.sendall(b"\r\n")
