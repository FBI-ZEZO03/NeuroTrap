"""
attacker_profile.py — Builds and maintains persistent attacker profiles.

Each unique src_ip gets a profile tracking sessions, classified intent,
TTPs, threat score, and campaign ID (via DBSCAN clustering).
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AttackerProfile:
    src_ip: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    session_count: int = 0
    total_commands: int = 0
    classified_intent: str = "unknown"
    attacker_tier: str = "beginner"
    threat_score: float = 0.0
    ttps: list[dict] = field(default_factory=list)
    campaign_id: Optional[str] = None
    country: Optional[str] = None
    asn: Optional[str] = None
    sessions: list[dict] = field(default_factory=list)
    is_blocked: bool = False
    response_action: str = "none"

    def update_from_session(
        self,
        session: dict,
        intent: str,
        tier: str,
        confidence: float,
        ttps: list[dict],
        ttp_score: float,
    ):
        self.last_seen = time.time()
        self.session_count += 1
        self.total_commands += len(session.get("commands", []))
        self.classified_intent = intent
        self.attacker_tier = tier

        # Merge new TTPs (deduplicate by technique_id)
        existing_ids = {t["technique_id"] for t in self.ttps}
        for ttp in ttps:
            if ttp["technique_id"] not in existing_ids:
                self.ttps.append(ttp)
                existing_ids.add(ttp["technique_id"])

        # Recalculate composite threat score
        self.threat_score = self._compute_threat_score(confidence, ttp_score, tier)

        self.sessions.append({
            "timestamp": time.time(),
            "intent": intent,
            "confidence": confidence,
            "commands": session.get("commands", [])[:20],  # cap stored commands
        })

    def _compute_threat_score(self, confidence: float, ttp_score: float, tier: str) -> float:
        tier_bonus = {"beginner": 0, "automated_bot": 15, "advanced_human": 30}
        base = (confidence * 40) + ttp_score + tier_bonus.get(tier, 0)

        # Persistence bonus — reaching a honeypot at all is suspicious.
        # Single visit starts at MEDIUM range; repeat visits scale to CRITICAL.
        n = self.session_count
        if n >= 100:
            persistence_bonus = 65
        elif n >= 50:
            persistence_bonus = 62
        elif n >= 20:
            persistence_bonus = 55
        elif n >= 10:
            persistence_bonus = 48
        elif n >= 5:
            persistence_bonus = 42
        elif n >= 3:
            persistence_bonus = 37
        elif n >= 2:
            persistence_bonus = 32
        else:
            persistence_bonus = 27   # single honeypot hit = elevated suspicion

        # Volume: deeper engagement signal, +1 per 5 cmds, capped at +15
        volume_bonus = min(self.total_commands // 5, 15)

        base += persistence_bonus + volume_bonus
        return min(round(base, 1), 100.0)

    # Intent → rough confidence estimate used when recalculating from stored data
    _INTENT_CONFIDENCE = {
        "malware_deployment": 0.82, "lateral_movement": 0.75,
        "credential_harvesting": 0.80, "cryptomining": 0.88,
        "bot_enrollment": 0.72, "reconnaissance": 0.55, "unknown": 0.45,
    }

    # Tactic → score weight (mirrors TTPExtractor.threat_score_contribution)
    _TACTIC_WEIGHTS = {
        "Impact": 40, "Privilege Escalation": 35, "Credential Access": 30,
        "Lateral Movement": 25, "Persistence": 20, "Command and Control": 15,
        "Defense Evasion": 10, "Discovery": 5,
    }

    def reclassify_intent(self) -> tuple[str, str]:
        """Infer intent and tier from all stored session commands and behavior patterns."""
        all_cmds: list[str] = []
        for s in self.sessions:
            all_cmds.extend(s.get("commands", []))

        cmd_str = " ".join(all_cmds).lower()

        # Extract base command names (strip full paths like /bin/./uname → uname)
        base_cmds: set[str] = set()
        for c in all_cmds:
            token = c.split()[0] if c.strip() else ""
            base = token.split("/")[-1].replace(".", "")
            if base:
                base_cmds.add(base)

        if any(t in cmd_str for t in ["xmrig", "minerd", "cryptonight", "stratum+tcp"]):
            return "cryptomining", "automated_bot"

        # Checking for running miners = cryptomining-related behavior
        if "grep" in cmd_str and any(t in cmd_str for t in ["miner", "xmrig", "monero"]):
            return "cryptomining", "automated_bot"

        has_download = any(t in cmd_str for t in ["wget ", "curl ", "tftp "])
        has_execute = any(t in cmd_str for t in ["chmod +x", "bash ", "sh ", ".sh"])
        if has_download and has_execute:
            return "malware_deployment", "advanced_human"

        if "/etc/shadow" in cmd_str or "cat /etc/passwd" in cmd_str:
            return "credential_harvesting", "advanced_human"

        if any(t in cmd_str for t in ["crontab", ".bashrc", ".bash_profile", "systemctl enable"]):
            return "bot_enrollment", "automated_bot"

        # SCP upload + execute = malware deployment (must check before generic scp/lateral rule)
        # 'scp -t' is the honeypot-side receive of an attacker SCP push
        has_scp_upload = "scp -t " in cmd_str or "scp -f " in cmd_str
        has_execute = any(t in cmd_str for t in ["chmod +x", "bash -c", "bash ./", ".sh", "sh ./", "./"])
        if has_scp_upload and has_execute:
            return "malware_deployment", "advanced_human"

        if any(t in cmd_str for t in ["ssh ", "scp ", "rsync "]) and len(all_cmds) > 3:
            return "lateral_movement", "advanced_human"

        # System resource survey = bot_enrollment (botnet candidate screening)
        if any(t in cmd_str for t in ["nproc", "cpu mhz", "lsb_release", "free -h", "/proc/cpuinfo"]):
            return "bot_enrollment", "automated_bot"

        # RouterOS / embedded device targeting
        if "/ip cloud" in cmd_str or "/ip address" in cmd_str:
            return "bot_enrollment", "automated_bot"

        # Fingerprinting bots: only run system-info commands (uname, id, etc.)
        fingerprint = {"uname", "id", "whoami", "hostname", "ifconfig", "ip"}
        if base_cmds and base_cmds.issubset(fingerprint | {"ls", "pwd", "env", "cat", "ps"}):
            tier = "automated_bot" if self.session_count >= 3 else "beginner"
            return "bot_enrollment", tier

        # Repeat attacker with no commands = persistent credential stuffing
        if self.total_commands == 0:
            if self.session_count >= 5:
                return "credential_harvesting", "automated_bot"
            if self.session_count >= 2:
                return "credential_harvesting", "beginner"

        tier = "automated_bot" if self.session_count >= 5 else "beginner"
        return "reconnaissance", tier

    def recalculate_score(self) -> float:
        """Recompute threat_score from stored profile data (no live session needed)."""
        # Use average confidence from stored session history when available
        conf_vals = [s["confidence"] for s in self.sessions if isinstance(s.get("confidence"), (int, float))]
        confidence = sum(conf_vals) / len(conf_vals) if conf_vals else self._INTENT_CONFIDENCE.get(self.classified_intent, 0.5)

        # Reconstruct ttp_score from stored TTPs (one weight contribution per tactic)
        counted: set[str] = set()
        ttp_score = 0.0
        for ttp in self.ttps:
            tactic = ttp.get("tactic", "")
            if tactic not in counted:
                ttp_score += self._TACTIC_WEIGHTS.get(tactic, 5) * float(ttp.get("confidence", 0.8))
                counted.add(tactic)
        ttp_score = min(ttp_score, 40.0)

        self.threat_score = self._compute_threat_score(confidence, ttp_score, self.attacker_tier)
        return self.threat_score

    def to_dict(self) -> dict:
        return asdict(self)


class ProfileStore:
    """
    Manages AttackerProfile persistence in MongoDB.

    Usage:
        store = ProfileStore(db["attacker_profiles"])
        profile = store.get_or_create("1.2.3.4")
        store.save(profile)
    """

    def __init__(self, collection):
        self.collection = collection
        collection.create_index("src_ip", unique=True)
        collection.create_index("threat_score")
        collection.create_index("last_seen")

    def get_or_create(self, src_ip: str) -> AttackerProfile:
        doc = self.collection.find_one({"src_ip": src_ip})
        if doc:
            doc.pop("_id", None)
            # Sanitize timestamp fields — DB may store None/"" for older docs
            for ts_field in ("first_seen", "last_seen"):
                if not isinstance(doc.get(ts_field), (int, float)):
                    doc[ts_field] = time.time()
            return AttackerProfile(**doc)
        return AttackerProfile(src_ip=src_ip)

    def save(self, profile: AttackerProfile):
        doc = profile.to_dict()
        self.collection.update_one(
            {"src_ip": profile.src_ip},
            {"$set": doc},
            upsert=True,
        )

    def get_top_threats(self, limit: int = 20) -> list[dict]:
        cursor = self.collection.find(
            {},
            {"_id": 0},
        ).sort("threat_score", -1).limit(limit)
        return list(cursor)

    def recalculate_all(self) -> int:
        """Recompute intent, tier, and threat scores for every profile. Returns update count."""
        count = 0
        for doc in self.collection.find({}, {"_id": 0}):
            for ts_field in ("first_seen", "last_seen"):
                if not isinstance(doc.get(ts_field), (int, float)):
                    doc[ts_field] = time.time()
            try:
                profile = AttackerProfile(**{k: v for k, v in doc.items() if k in AttackerProfile.__dataclass_fields__})
                profile.classified_intent, profile.attacker_tier = profile.reclassify_intent()
                profile.recalculate_score()
                self.save(profile)
                count += 1
            except Exception as exc:
                logger.error("Recalc failed for %s: %s", doc.get("src_ip"), exc)
        return count

    def get_active_sessions(self, since_secs: float = 300) -> list[dict]:
        cutoff = time.time() - since_secs
        cursor = self.collection.find(
            {"last_seen": {"$gte": cutoff}},
            {"_id": 0},
        ).sort("last_seen", -1)
        return list(cursor)
