"""
behavior_engine.py — Orchestrates classification, TTP extraction, and profiling.

Consumes Cowrie session documents from MongoDB, runs the full analysis pipeline,
and writes enriched AttackerProfile records back to the database.
"""

from __future__ import annotations
import logging
import time
import threading
from pathlib import Path

from .classifier import AttackerClassifier
from .ttp_extractor import TTPExtractor
from .attacker_profile import AttackerProfile, ProfileStore

logger = logging.getLogger(__name__)


class BehaviorEngine:
    """
    Main entry point for the behavior analysis layer.

    Usage:
        engine = BehaviorEngine(db)
        engine.start()          # background polling loop
        engine.stop()
    """

    def __init__(self, db, poll_interval: float = 5.0):
        self.db = db
        self.poll_interval = poll_interval
        self.classifier = AttackerClassifier.load() if (Path("/app/data/models/classifier.joblib").exists()) else None
        self.ttp_extractor = TTPExtractor()
        self.profile_store = ProfileStore(db["attacker_profiles"])
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="behavior-engine")
        self._thread.start()
        logger.info("BehaviorEngine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def analyze_session(self, session: dict) -> AttackerProfile:
        """Analyze a single session dict and return the updated AttackerProfile."""
        src_ip = session.get("src_ip", "0.0.0.0")
        commands = session.get("commands", [])

        # TTP extraction (always available)
        ttps = self.ttp_extractor.extract_as_dicts(commands)
        ttp_score = self.ttp_extractor.threat_score_contribution(commands)

        # ML classification (if model is trained)
        if self.classifier:
            intent, tier, confidence = self.classifier.predict(session)
        else:
            intent, tier, confidence = self._rule_based_classify(session)

        profile = self.profile_store.get_or_create(src_ip)
        profile.update_from_session(session, intent, tier, confidence, ttps, ttp_score)
        self.profile_store.save(profile)

        logger.info(
            "Session analyzed — IP=%s intent=%s tier=%s score=%.1f TTPs=%d",
            src_ip, intent, tier, profile.threat_score, len(ttps),
        )
        return profile

    # ── Background polling ────────────────────────────────────────────────────

    def _run_loop(self):
        """Poll for unprocessed Cowrie sessions and analyze them."""
        processed_ids: set = set()
        while self._running:
            try:
                cursor = self.db["cowrie_sessions"].find(
                    {"analyzed": {"$ne": True}},
                    {"_id": 1, "src_ip": 1, "commands": 1, "duration_secs": 1,
                     "login_attempts": 1, "failed_logins": 1},
                    limit=50,
                )
                for doc in cursor:
                    doc_id = doc["_id"]
                    if doc_id in processed_ids:
                        continue
                    try:
                        self.analyze_session(doc)
                        self.db["cowrie_sessions"].update_one(
                            {"_id": doc_id}, {"$set": {"analyzed": True}}
                        )
                        processed_ids.add(doc_id)
                    except Exception as exc:
                        logger.error("Failed to analyze session %s: %s", doc_id, exc)
            except Exception as exc:
                logger.error("BehaviorEngine poll error: %s", exc)
            time.sleep(self.poll_interval)

    # ── Fallback rule-based classifier ───────────────────────────────────────

    @staticmethod
    def _rule_based_classify(session: dict) -> tuple[str, str, float]:
        commands = session.get("commands", [])
        cmd_str = " ".join(commands).lower()

        if any(t in cmd_str for t in ["xmrig", "minerd", "cryptonight"]):
            return "cryptomining", "automated_bot", 0.9
        if any(t in cmd_str for t in ["wget", "curl", "tftp"]) and any(
            t in cmd_str for t in ["chmod", "bash", ".sh"]
        ):
            return "malware_deployment", "advanced_human", 0.8
        if "cat /etc/shadow" in cmd_str or "cat /etc/passwd" in cmd_str:
            return "credential_harvesting", "advanced_human", 0.85
        if any(t in cmd_str for t in ["ssh ", "scp ", "lateral"]):
            return "lateral_movement", "advanced_human", 0.75
        if len(commands) < 5:
            return "reconnaissance", "beginner", 0.6
        return "reconnaissance", "automated_bot", 0.5
