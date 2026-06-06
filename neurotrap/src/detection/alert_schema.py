"""
Alert event schema and validation for the NeuroTrap detection pipeline.
All sources (Cowrie, Dionaea, Scapy, Zeek) normalize into AlertEvent before DB write.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


SEVERITY_LEVELS = ("low", "medium", "high", "critical")

ATTACK_TYPES = (
    "port_scan",
    "brute_force",
    "protocol_anomaly",
    "malware_upload",
    "command_injection",
    "lateral_movement",
    "data_exfiltration",
    "tool_fingerprint",
    "unknown",
)


@dataclass
class AlertEvent:
    src_ip: str
    dst_port: int
    attack_type: str
    honeypot_source: str                    # cowrie | dionaea | scapy | zeek
    severity: str = "low"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    protocol: Optional[str] = None
    raw_payload: Optional[str] = None
    session_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    command: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.attack_type not in ATTACK_TYPES:
            self.attack_type = "unknown"
        if self.severity not in SEVERITY_LEVELS:
            self.severity = "low"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_cowrie(cls, raw: dict) -> "AlertEvent":
        """Parse a Cowrie JSON log entry into an AlertEvent."""
        event_id_map = {
            "cowrie.login.failed": ("brute_force", "low"),
            "cowrie.login.success": ("brute_force", "high"),
            "cowrie.command.input": ("command_injection", "medium"),
            "cowrie.session.file_download": ("malware_upload", "high"),
            "cowrie.session.connect": ("tool_fingerprint", "low"),
        }
        cowrie_id = raw.get("eventid", "")
        attack_type, severity = event_id_map.get(cowrie_id, ("unknown", "low"))

        return cls(
            src_ip=raw.get("src_ip", "0.0.0.0"),
            dst_port=int(raw.get("dst_port") or 22),
            attack_type=attack_type,
            severity=severity,
            honeypot_source="cowrie",
            session_id=raw.get("session"),
            username=raw.get("username"),
            password=raw.get("password"),
            command=raw.get("input"),
            extra=raw,
        )

    @classmethod
    def from_zeek(cls, raw: dict, log_type: str = "conn") -> "AlertEvent":
        """Parse a Zeek conn.log / ssh.log JSON entry into an AlertEvent."""
        return cls(
            src_ip=raw.get("id.orig_h", "0.0.0.0"),
            src_port=raw.get("id.orig_p"),
            dst_ip=raw.get("id.resp_h"),
            dst_port=raw.get("id.resp_p", 0),
            protocol=raw.get("proto", "tcp"),
            attack_type="tool_fingerprint",
            severity="low",
            honeypot_source="zeek",
            extra={"zeek_log": log_type, **raw},
        )
