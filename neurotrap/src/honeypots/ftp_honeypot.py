"""
ftp_honeypot.py — Low-interaction FTP honeypot.

Emulates a vsFTPd server banner and the USER/PASS exchange, capturing every
credential pair an attacker tries. All authentication attempts are rejected
(530) so brute-forcers keep trying, which yields a rich credential corpus for
the behaviour engine.
"""

from __future__ import annotations

import socket

from .base import BaseHoneypot, HoneypotSession, recv_line


class FTPHoneypot(BaseHoneypot):
    name = "ftp"
    default_port = 2121  # mapped to :21 in Docker
    banner = b"220 (vsFTPd 3.0.3)\r\n"

    def handle_client(self, conn: socket.socket, addr, session: HoneypotSession):
        pending_user = None
        attempts = 0
        while attempts < 12:
            line = recv_line(conn)
            if not line:
                break
            cmd, _, arg = line.partition(" ")
            cmd = cmd.upper()

            if cmd == "USER":
                pending_user = arg.strip()
                conn.sendall(b"331 Please specify the password.\r\n")
            elif cmd == "PASS":
                attempts += 1
                self.record_event(
                    session,
                    attack_type="brute_force",
                    severity="medium",
                    username=pending_user,
                    password=arg.strip(),
                    command=f"USER {pending_user} / PASS",
                    protocol="ftp",
                )
                conn.sendall(b"530 Login incorrect.\r\n")
            elif cmd in ("QUIT", "BYE"):
                conn.sendall(b"221 Goodbye.\r\n")
                break
            elif cmd == "SYST":
                conn.sendall(b"215 UNIX Type: L8\r\n")
            elif cmd in ("FEAT", "OPTS"):
                conn.sendall(b"211 No features\r\n")
            else:
                # Log anything unusual (e.g. exploit attempts against the daemon).
                if cmd not in ("USER", "PASS"):
                    self.record_event(
                        session,
                        attack_type="protocol_anomaly",
                        severity="low",
                        command=line[:200],
                        protocol="ftp",
                    )
                conn.sendall(b"530 Please login with USER and PASS.\r\n")
