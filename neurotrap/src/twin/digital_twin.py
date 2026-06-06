"""
digital_twin.py — Attacker Digital Twin (ADT), NeuroTrap Innovation Module 05.

A digital twin is a living virtual replica of a real attacker, continuously
synthesised from every signal NeuroTrap observes about a source IP:

  * identity & origin        (first/last seen, country, ASN, honeypots touched)
  * capability               (attacker tier, sophistication, automation score)
  * intent                   (classified intent, dominant objective)
  * TTP fingerprint          (MITRE techniques/tactics, tooling)
  * kill-chain progression   (which of the 7 stages have been reached)
  * psychology               (CBEE cognitive-bias profile, when available)
  * predicted next move      (Markov tactic predictor)
  * forward simulation       (the twin "running ahead" of the real attacker)
  * engagement recommendation(suggested deception posture)
  * fidelity                 (how well past predictions matched reality)

Twins are built by aggregating `alert_events` per src_ip (so they reflect live
honeypot captures directly) and enriched with `attacker_profiles` and
`cbee_profiles` when those exist. They persist to the `attacker_twins`
collection through the central DB layer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from .kill_chain import build_kill_chain, tactic_for_attack_type
from .predictor import TacticPredictor

logger = logging.getLogger(__name__)

# Keywords → tool/agent names we surface in the twin's "tooling" fingerprint.
_TOOL_SIGNATURES = {
    "sqlmap": "sqlmap", "nikto": "Nikto", "nmap": "Nmap", "masscan": "masscan",
    "hydra": "Hydra", "medusa": "Medusa", "gobuster": "Gobuster", "dirbuster": "DirBuster",
    "wget": "wget", "curl": "curl", "busybox": "BusyBox", "mirai": "Mirai",
    "xmrig": "XMRig", "metasploit": "Metasploit", "python-requests": "python-requests",
    "zgrab": "zgrab", "libssh": "libssh",
}

_TIER_RANK = {"beginner": 1, "automated_bot": 2, "advanced_human": 3}


@dataclass
class DigitalTwin:
    src_ip: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    observation_count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    # capability / intent
    attacker_tier: str = "beginner"
    sophistication: float = 0.0          # 0–100
    automation_score: float = 0.0        # 0–100 (100 = fully automated/bot)
    classified_intent: str = "unknown"
    threat_score: float = 0.0

    # fingerprint
    honeypots_touched: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    tactics_observed: list[str] = field(default_factory=list)
    tactic_sequence: list[str] = field(default_factory=list)   # ordered
    technique_ids: list[str] = field(default_factory=list)

    # synthesized intelligence
    kill_chain: dict = field(default_factory=dict)
    psychology: dict = field(default_factory=dict)
    predicted_next: list[dict] = field(default_factory=list)
    recommendation: dict = field(default_factory=dict)

    # twin quality
    fidelity: float = 0.0                # 0–1, prediction accuracy over time
    predictions_made: int = 0
    predictions_hit: int = 0
    confidence: float = 0.0              # 0–1, how much signal backs this twin

    def to_dict(self) -> dict:
        return asdict(self)


class AttackerDigitalTwin:
    """
    Engine that builds, persists, predicts and simulates attacker digital twins.

    Usage:
        adt = AttackerDigitalTwin(db)
        twin = adt.build_twin("185.220.101.42")
        forecast = adt.simulate(twin, steps=5)
    """

    def __init__(self, db):
        self.db = db

    # ── building ────────────────────────────────────────────────────────────────

    def build_all(self) -> list[DigitalTwin]:
        """Build/refresh a twin for every src_ip seen in alert_events."""
        ips = self._distinct_source_ips()
        return [self.build_twin(ip) for ip in ips]

    def build_twin(self, src_ip: str) -> DigitalTwin:
        events = self._events_for(src_ip)
        twin = DigitalTwin(src_ip=src_ip)

        prior = self._load_existing(src_ip)
        if prior:
            twin.created_at = prior.get("created_at", twin.created_at)
            twin.predictions_made = prior.get("predictions_made", 0)
            twin.predictions_hit = prior.get("predictions_hit", 0)

        self._fold_events(twin, events)
        self._merge_profile(twin, src_ip)
        self._merge_psychology(twin, src_ip)

        # Kill chain + prediction from the synthesised tactic history.
        twin.kill_chain = build_kill_chain(twin.tactics_observed)
        predictor = TacticPredictor(twin.tactic_sequence)
        current = twin.tactic_sequence[-1] if twin.tactic_sequence else None
        twin.predicted_next = predictor.predict_next(current, top_n=3)
        twin.predictions_made = max(twin.predictions_made, 0) + (1 if twin.predicted_next else 0)

        twin.recommendation = self._recommend(twin)
        twin.confidence = self._confidence(twin)
        twin.fidelity = (twin.predictions_hit / twin.predictions_made) if twin.predictions_made else 0.0
        twin.updated_at = time.time()

        self._persist(twin)
        logger.info(
            "Twin built — IP=%s tier=%s stage=%s next=%s conf=%.2f",
            src_ip, twin.attacker_tier, twin.kill_chain.get("current_stage"),
            twin.predicted_next[0]["tactic"] if twin.predicted_next else "—", twin.confidence,
        )
        return twin

    # ── prediction / simulation ──────────────────────────────────────────────────

    def predict(self, twin: DigitalTwin, top_n: int = 3) -> list[dict]:
        predictor = TacticPredictor(twin.tactic_sequence)
        current = twin.tactic_sequence[-1] if twin.tactic_sequence else None
        return predictor.predict_next(current, top_n=top_n)

    def simulate(self, twin: DigitalTwin, steps: int = 5, seed: Optional[int] = None) -> list[dict]:
        predictor = TacticPredictor(twin.tactic_sequence)
        start = twin.tactic_sequence[-1] if twin.tactic_sequence else None
        if seed is None:
            # Stable per-twin seed so repeated views show the same forecast.
            seed = abs(hash(twin.src_ip)) % (2 ** 31)
        return predictor.simulate_forward(start, steps=steps, seed=seed)

    # ── reads ─────────────────────────────────────────────────────────────────────

    def get_twin(self, src_ip: str) -> Optional[dict]:
        try:
            return self.db["attacker_twins"].find_one({"src_ip": src_ip}, {"_id": 0})
        except Exception:
            return None

    def list_twins(self, limit: int = 50) -> list[dict]:
        try:
            return list(
                self.db["attacker_twins"].find({}, {"_id": 0})
                .sort("threat_score", -1).limit(limit)
            )
        except Exception:
            return []

    # ── internals ─────────────────────────────────────────────────────────────────

    def _distinct_source_ips(self) -> list[str]:
        try:
            ips = set()
            for e in self.db["alert_events"].find({}, {"_id": 0, "src_ip": 1}):
                if e.get("src_ip"):
                    ips.add(e["src_ip"])
            return sorted(ips)
        except Exception:
            return []

    def _events_for(self, src_ip: str) -> list[dict]:
        try:
            return list(
                self.db["alert_events"].find({"src_ip": src_ip}, {"_id": 0})
                .sort("timestamp", 1)
            )
        except Exception:
            return []

    def _load_existing(self, src_ip: str) -> Optional[dict]:
        return self.get_twin(src_ip)

    def _fold_events(self, twin: DigitalTwin, events: list[dict]):
        if not events:
            return
        timestamps = []
        tactics_seq: list[str] = []
        tactics_set: list[str] = []
        techniques: set[str] = set()
        tools: set[str] = set()
        honeypots: set[str] = set()
        countries: set[str] = set()
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        max_sev = 0

        for e in events:
            ts = e.get("timestamp")
            if ts:
                timestamps.append(ts)
            hp = e.get("honeypot_source")
            if hp:
                honeypots.add(hp)
            # Tactic from attack_type (honeypot) — keeps ordered sequence.
            tactic = tactic_for_attack_type(e.get("attack_type", "unknown"))
            tactics_seq.append(tactic)
            if tactic not in tactics_set:
                tactics_set.append(tactic)
            # Tooling from commands, payloads, user-agents, client versions.
            blob = " ".join(str(x) for x in [
                e.get("command", ""), e.get("raw_payload", ""),
                (e.get("extra") or {}).get("user_agent", ""),
                (e.get("extra") or {}).get("client_version", ""),
            ]).lower()
            for sig, name in _TOOL_SIGNATURES.items():
                if sig in blob:
                    tools.add(name)
            if e.get("country"):
                countries.add(e["country"])
            max_sev = max(max_sev, severity_rank.get(e.get("severity", "low"), 1))

        twin.observation_count = len(events)
        twin.first_seen = min(timestamps) if timestamps else time.time()
        twin.last_seen = max(timestamps) if timestamps else time.time()
        twin.honeypots_touched = sorted(honeypots)
        twin.countries = sorted(countries)
        twin.tools = sorted(tools)
        twin.tactic_sequence = tactics_seq
        twin.tactics_observed = tactics_set
        twin.technique_ids = sorted(techniques)

        twin.automation_score = self._automation_score(timestamps, twin.tools)
        # Baseline tier/threat from honeypot signal (profile merge may raise it).
        twin.threat_score = min(100.0, max_sev * 12 + len(tactics_set) * 6 + len(twin.tools) * 4)
        if twin.automation_score >= 70:
            twin.attacker_tier = "automated_bot"
        elif len(tactics_set) >= 4 or max_sev >= 4:
            twin.attacker_tier = "advanced_human"
        twin.sophistication = min(100.0, len(tactics_set) * 14 + len(twin.technique_ids) * 4
                                  + _TIER_RANK.get(twin.attacker_tier, 1) * 10)

    def _automation_score(self, timestamps: list[float], tools: list[str]) -> float:
        score = 0.0
        if any(t in tools for t in ("Mirai", "BusyBox", "sqlmap", "Nikto", "masscan", "Nmap", "zgrab", "python-requests")):
            score += 50
        if len(timestamps) >= 3:
            gaps = [b - a for a, b in zip(sorted(timestamps), sorted(timestamps)[1:])]
            gaps = [g for g in gaps if g >= 0]
            if gaps:
                avg = sum(gaps) / len(gaps)
                # Fast, regular bursts → automation.
                if avg < 1.0:
                    score += 40
                elif avg < 5.0:
                    score += 20
                var = sum((g - avg) ** 2 for g in gaps) / len(gaps)
                if var < 1.0:
                    score += 10
        return min(100.0, score)

    def _merge_profile(self, twin: DigitalTwin, src_ip: str):
        try:
            prof = self.db["attacker_profiles"].find_one({"src_ip": src_ip}, {"_id": 0})
        except Exception:
            prof = None
        if not prof:
            return
        # Profile signal can only strengthen the twin.
        if _TIER_RANK.get(prof.get("attacker_tier", "beginner"), 1) > _TIER_RANK.get(twin.attacker_tier, 1):
            twin.attacker_tier = prof["attacker_tier"]
        if prof.get("classified_intent") and prof["classified_intent"] != "unknown":
            twin.classified_intent = prof["classified_intent"]
        twin.threat_score = max(twin.threat_score, float(prof.get("threat_score", 0.0)))
        if prof.get("country"):
            twin.countries = sorted(set(twin.countries) | {prof["country"]})
        # Fold MITRE TTPs from the profile into the twin's fingerprint.
        for ttp in prof.get("ttps", []):
            tid = ttp.get("technique_id")
            if tid and tid not in twin.technique_ids:
                twin.technique_ids.append(tid)
            tactic = ttp.get("tactic")
            if tactic:
                if tactic not in twin.tactics_observed:
                    twin.tactics_observed.append(tactic)
                twin.tactic_sequence.append(tactic)

    def _merge_psychology(self, twin: DigitalTwin, src_ip: str):
        try:
            bias = self.db["cbee_profiles"].find_one({"src_ip": src_ip}, {"_id": 0})
        except Exception:
            bias = None
        if bias:
            twin.psychology = {
                "dominant": bias.get("dominant"),
                "overall": bias.get("overall"),
                "curiosity_gap": bias.get("curiosity_gap"),
                "confirmation_bias": bias.get("confirmation_bias"),
                "sunk_cost": bias.get("sunk_cost"),
                "authority_signal": bias.get("authority_signal"),
                "scarcity_framing": bias.get("scarcity_framing"),
            }

    def _recommend(self, twin: DigitalTwin) -> dict:
        """Suggest a deception posture from the twin's state + predicted move."""
        tier_to_env = {"beginner": "beginner", "automated_bot": "automated_bot",
                       "advanced_human": "advanced_human"}
        env_tier = tier_to_env.get(twin.attacker_tier, "beginner")
        next_tactic = twin.predicted_next[0]["tactic"] if twin.predicted_next else "Discovery"

        playbook = {
            "Credential Access": "Pre-stage a honeytoken /etc/shadow and fake vault creds to capture intent.",
            "Lateral Movement":  "Expose a decoy internal jump-host with planted SSH keys to map their pivot.",
            "Exfiltration":      "Plant beaconing canary documents to attribute and track stolen data.",
            "Impact":            "Throttle + snapshot the environment; deploy a believable but inert target.",
            "Command and Control": "Sinkhole the next ingress download and serve an instrumented payload.",
            "Persistence":       "Allow a fake cron/persistence foothold to study their implant.",
            "Privilege Escalation": "Offer a tempting setuid binary decoy to observe their escalation tooling.",
            "Execution":         "Increase shell interactivity to elicit more commands and TTPs.",
            "Discovery":         "Enrich the filesystem with plausible breadcrumbs to deepen engagement.",
        }
        bias = (twin.psychology or {}).get("dominant")
        return {
            "suggested_env_tier": env_tier,
            "anticipated_tactic": next_tactic,
            "action": playbook.get(next_tactic, "Maintain engagement and continue profiling."),
            "bias_lever": bias,
            "urgency": "high" if twin.threat_score >= 60 else ("medium" if twin.threat_score >= 30 else "low"),
        }

    def _confidence(self, twin: DigitalTwin) -> float:
        """How much observed signal backs this twin (0–1)."""
        score = 0.0
        score += min(0.4, twin.observation_count * 0.04)
        score += min(0.3, len(twin.tactics_observed) * 0.08)
        score += min(0.2, len(twin.tools) * 0.07)
        if twin.psychology:
            score += 0.1
        return round(min(1.0, score), 3)

    def _persist(self, twin: DigitalTwin):
        try:
            self.db["attacker_twins"].update_one(
                {"src_ip": twin.src_ip}, {"$set": twin.to_dict()}, upsert=True
            )
        except Exception as exc:
            logger.error("Failed to persist twin %s: %s", twin.src_ip, exc)
