"""
http_honeypot.py — Low/medium-interaction HTTP honeypot.

Presents a believable but fake corporate admin login page, logs every request,
captures credentials submitted to login forms, and flags common attack
signatures (path traversal, SQLi, command injection, web-shell probes, scanner
fingerprints). All activity is recorded as AlertEvents via BaseHoneypot.
"""

from __future__ import annotations

import re
import socket
import time
from urllib.parse import parse_qs, unquote

from .base import BaseHoneypot, HoneypotSession

# Signature → (attack_type, severity)
_SIGNATURES = [
    (re.compile(r"(\.\./|\.\.%2f)", re.I),                     ("data_exfiltration", "high")),
    (re.compile(r"(union\s+select|or\s+1=1|';--|sleep\()", re.I), ("command_injection", "high")),
    (re.compile(r"(;|\||`|\$\(|&&)\s*(cat|wget|curl|bash|sh|nc|whoami|id)\b", re.I), ("command_injection", "critical")),
    (re.compile(r"(/etc/passwd|/bin/sh|cmd\.exe|powershell)", re.I), ("command_injection", "critical")),
    (re.compile(r"<\?php|eval\(|base64_decode\(", re.I),      ("malware_upload", "high")),
    (re.compile(r"(\.env|\.git/|wp-admin|phpmyadmin|/actuator|/\.aws)", re.I), ("tool_fingerprint", "medium")),
]

_SCANNER_UA = re.compile(r"(sqlmap|nikto|nmap|masscan|dirbuster|gobuster|hydra|curl|python-requests|zgrab)", re.I)

_LOGIN_PAGE = (
    "<!doctype html><html><head><title>NeuroCorp Admin Portal</title></head>"
    "<body style='font-family:sans-serif;max-width:380px;margin:80px auto'>"
    "<h2>NeuroCorp Internal — Sign in</h2>"
    "<form method='POST' action='/login'>"
    "<p>Username<br><input name='username' style='width:100%'></p>"
    "<p>Password<br><input name='password' type='password' style='width:100%'></p>"
    "<button type='submit'>Log in</button></form>"
    "<p style='color:#888;font-size:12px'>Apache/2.4.41 (Ubuntu) Server</p>"
    "</body></html>"
)


class HTTPHoneypot(BaseHoneypot):
    name = "http"
    default_port = 8081  # mapped to :80 in Docker; high port for local runs

    def handle_client(self, conn: socket.socket, addr, session: HoneypotSession):
        request = self._read_request(conn)
        if not request:
            return
        method, path, headers, body = request
        ua = headers.get("user-agent", "")

        # Classify the request.
        decoded = unquote(path + "?" + body)
        attack_type, severity = "tool_fingerprint", "low"
        for pattern, (atype, sev) in _SIGNATURES:
            if pattern.search(decoded):
                attack_type, severity = atype, sev
                break
        else:
            if _SCANNER_UA.search(ua):
                attack_type, severity = "tool_fingerprint", "medium"

        username = password = None
        if method == "POST" and ("login" in path.lower() or "username" in body.lower()):
            form = parse_qs(body)
            username = (form.get("username") or [None])[0]
            password = (form.get("password") or [None])[0]
            if username or password:
                attack_type, severity = "brute_force", "medium"

        self.record_event(
            session,
            attack_type=attack_type,
            severity=severity,
            username=username,
            password=password,
            command=f"{method} {path}",
            protocol="http",
            raw_payload=(body[:512] or None),
            extra={"user_agent": ua, "method": method, "path": path,
                   "headers": {k: v for k, v in list(headers.items())[:20]}},
        )

        self._send_response(conn, method, path, username, password)

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _read_request(self, conn: socket.socket):
        conn.settimeout(8.0)
        data = bytearray()
        # Read until end of headers.
        while b"\r\n\r\n" not in data and len(data) < 65536:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        if not data:
            return None

        head, _, rest = data.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        if not lines or not lines[0]:
            return None
        parts = lines[0].split()
        method = parts[0] if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        body = rest
        try:
            length = int(headers.get("content-length", "0"))
        except ValueError:
            length = 0
        while len(body) < length and len(body) < 65536:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            body += chunk

        return method, path, headers, body.decode("utf-8", errors="replace")

    def _send_response(self, conn, method, path, username, password):
        if method == "POST" and (username or password):
            # Always "fail" the login to keep the attacker engaged/guessing.
            body = "<html><body><h3>Invalid credentials</h3><a href='/'>Back</a></body></html>"
            status = "401 Unauthorized"
        elif path.rstrip("/") in ("", "/login", "/admin"):
            body, status = _LOGIN_PAGE, "200 OK"
        else:
            body = "<html><body><h1>404 Not Found</h1></body></html>"
            status = "404 Not Found"

        payload = body.encode("utf-8")
        response = (
            f"HTTP/1.1 {status}\r\n"
            f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\r\n"
            "Server: Apache/2.4.41 (Ubuntu)\r\n"
            "Content-Type: text/html; charset=UTF-8\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8") + payload
        try:
            conn.sendall(response)
        except OSError:
            pass
