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
        tier_bonus = {"beginner": 0, "automated_bot": 10, "advanced_human": 25}
        base = (confidence * 40) + ttp_score + tier_bonus.get(tier, 0)
        # Penalize if only recon detected (likely scanner)
        if self.classified_intent == "reconnaissance" and self.session_count < 3:
            base *= 0.6
        return min(round(base, 1), 100.0)

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

    def get_active_sessions(self, since_secs: float = 300) -> list[dict]:
        cutoff = time.time() - since_secs
        cursor = self.collection.find(
            {"last_seen": {"$gte": cutoff}},
            {"_id": 0},
        ).sort("last_seen", -1)
        return list(cursor)
