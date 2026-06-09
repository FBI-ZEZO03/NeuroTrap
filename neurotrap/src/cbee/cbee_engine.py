"""
cbee_engine.py — Cognitive Bias Exploitation Engine orchestrator.

Sits between Layer 3 (Behavior Analysis) and Layer 4 (Deception Engine).
Subscribes to the live attacker profile stream, scores bias dimensions,
and emits BaitInjection commands to the Deception Engine.
"""

from __future__ import annotations
import time
import logging
import threading
from typing import Callable, Optional

from .bias_scorer import BiasScorer, BiasProfile
from .bait_injector import BaitInjector, BaitInjection

logger = logging.getLogger(__name__)


class CBEEEngine:
    """
    Cognitive Bias Exploitation Engine.

    Usage:
        engine = CBEEEngine(db, on_inject=deception_engine.receive_bait)
        engine.start()
    """

    RESCORE_INTERVAL    = 30   # re-score active sessions every N seconds
    MIN_SCORE_TO_INJECT = 15   # minimum bias score to trigger injection
    MAX_INJECTIONS_PER_IP = 3  # cap injections per attacker to avoid overload

    def __init__(self, db, on_inject: Optional[Callable[[BaitInjection], None]] = None):
        self.db = db
        self.on_inject = on_inject
        self.scorer  = BiasScorer()
        self.injector = BaitInjector()
        self._injected: dict[str, int]   = {}   # ip → injection count
        self._profiles: dict[str, BiasProfile] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run_loop, daemon=True, name="cbee-engine")
        self._thread.start()
        logger.info("CBEEEngine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def score_session(self, session: dict) -> BiasProfile:
        """Public: score a single session and return its bias profile."""
        profile = self.scorer.score(session)
        self._profiles[session.get("src_ip", "?")] = profile
        self._persist_profile(session.get("src_ip", "?"), profile)
        return profile

    def get_all_profiles(self) -> list[dict]:
        try:
            return list(self.db["cbee_profiles"].find({}, {"_id": 0}).sort("updated_at", -1).limit(50))
        except Exception:
            return [{"src_ip": ip, **p.to_dict()} for ip, p in self._profiles.items()]

    # ── Background loop ────────────────────────────────────────────────────────

    def _run_loop(self):
        while self._running:
            try:
                self._process_active_sessions()
            except Exception as exc:
                logger.error("CBEEEngine loop error: %s", exc)
            time.sleep(self.RESCORE_INTERVAL)

    def _process_active_sessions(self):
        # Build injected-count map from DB so restarts don't re-inject
        try:
            injected_counts: dict = {}
            for doc in self.db["cbee_injections"].aggregate([
                {"$group": {"_id": "$src_ip", "count": {"$sum": 1}}}
            ]):
                injected_counts[doc["_id"]] = doc["count"]
        except Exception:
            injected_counts = {}

        # Process from attacker_profiles — richer than individual cowrie sessions
        try:
            attacker_profiles = list(self.db["attacker_profiles"].find(
                {"threat_score": {"$gte": 30}},
                {"src_ip": 1, "sessions": 1, "session_count": 1,
                 "classified_intent": 1, "attacker_tier": 1, "threat_score": 1},
            ).sort("threat_score", -1).limit(50))
        except Exception:
            return

        for ap in attacker_profiles:
            ip = ap.get("src_ip", "?")

            if injected_counts.get(ip, 0) >= self.MAX_INJECTIONS_PER_IP:
                continue

            # Aggregate all stored commands across sessions into one synthetic session
            all_cmds: list[str] = []
            for s in ap.get("sessions", []):
                all_cmds.extend(s.get("commands", []))

            synthetic = {
                "src_ip": ip,
                "commands": all_cmds,
                "duration_secs": ap.get("session_count", 1) * 30,
                "login_attempts": ap.get("session_count", 1),
                "classified_intent": ap.get("classified_intent", "reconnaissance"),
            }

            bias = self.scorer.score(synthetic)
            self._profiles[ip] = bias
            self._persist_profile(ip, bias)

            if bias.overall >= self.MIN_SCORE_TO_INJECT:
                try:
                    env = self.db["deception_environments"].find_one(
                        {"src_ip": ip, "is_active": True}, {"env_id": 1}
                    )
                except Exception:
                    env = None

                env_id = env["env_id"] if env else "unknown"
                injection = self.injector.generate(bias, env_id=env_id, src_ip=ip)

                self._persist_injection(injection)
                injected_counts[ip] = injected_counts.get(ip, 0) + 1

                if self.on_inject:
                    try:
                        self.on_inject(injection)
                    except Exception as exc:
                        logger.error("Bait injection callback failed: %s", exc)

                logger.info(
                    "CBEE bait injected → %s | bias=%s | score=%.1f | assets=%d",
                    ip, bias.dominant, bias.overall, len(injection.assets)
                )

    def _persist_profile(self, ip: str, profile: BiasProfile):
        try:
            self.db["cbee_profiles"].update_one(
                {"src_ip": ip},
                {"$set": {"src_ip": ip, "updated_at": time.time(), **profile.to_dict()}},
                upsert=True,
            )
        except Exception:
            pass

    def _persist_injection(self, injection: BaitInjection):
        try:
            self.db["cbee_injections"].insert_one(injection.to_dict())
        except Exception:
            pass
