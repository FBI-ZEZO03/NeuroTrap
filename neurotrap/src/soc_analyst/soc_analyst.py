"""
soc_analyst.py — AI SOC Analyst (Innovation 06).

An LLM-assisted analyst layer on top of the existing detection + behavior data.
It does three SOC jobs over the captured `alert_events` and `attacker_profiles`:

  1. Auto-triage queue  — ranks active threat actors by risk and attaches a
     verdict + recommended action (the project's log/slow/isolate/block matrix).
  2. Incident reports   — per-attacker narrative: summary, observed MITRE TTPs,
     threat assessment, recommended actions (LLM-written, heuristic fallback).
  3. Analyst chat        — free-form Q&A grounded in the current SOC data.

Every method works with no LLM key (deterministic heuristics) and with no DB
(built-in demo data), so it is safe to run live in a graduation demo.
"""

from __future__ import annotations
import time
import logging
from typing import Optional

from .llm_client import llm_complete, llm_available

logger = logging.getLogger(__name__)

# Threat-score → action matrix, aligned with the Response Engine thresholds
# (40 / 70 / 90) documented in the project plan.
def _risk_band(score: float) -> tuple[str, str, str]:
    """Return (risk_label, recommended_action, one-line verdict)."""
    if score >= 90:
        return ("critical", "block", "Active compromise attempt — block source and capture forensics")
    if score >= 70:
        return ("high", "isolate", "Hands-on intrusion — isolate session and alert on-call")
    if score >= 40:
        return ("elevated", "slow", "Automated exploitation — slow and redirect to a deeper honeypot")
    return ("low", "monitor", "Reconnaissance / low-signal noise — keep logging")


INTENT_HINT = {
    "credential_harvesting": "Attempting to capture or reuse credentials.",
    "malware_deployment": "Staging or executing malware payloads.",
    "lateral_movement": "Probing for pivots to other hosts.",
    "cryptomining": "Deploying cryptominers for resource theft.",
    "reconnaissance": "Enumerating services and surface area.",
    "bot_enrollment": "Enrolling the host into a botnet.",
    "unknown": "Intent not yet classified.",
}


class SOCAnalyst:
    def __init__(self, db=None, use_llm: bool = True):
        self.db = db
        self.use_llm = use_llm

    # ── helpers ─────────────────────────────────────────────────────────────
    def llm_enabled(self) -> bool:
        return bool(self.use_llm) and llm_available()

    def _profiles(self, limit: int = 50) -> list[dict]:
        if self.db is None:
            return []
        try:
            return list(
                self.db["attacker_profiles"].find({}, {"_id": 0})
                .sort("threat_score", -1).limit(limit)
            )
        except Exception:
            return []

    def _events_for(self, src_ip: str, limit: int = 40) -> list[dict]:
        if self.db is None:
            return []
        try:
            return list(
                self.db["alert_events"].find({"src_ip": src_ip}, {"_id": 0})
                .sort("timestamp", -1).limit(limit)
            )
        except Exception:
            return []

    # ── 1. Triage queue ──────────────────────────────────────────────────────
    def triage_queue(self, limit: int = 15) -> list[dict]:
        profiles = self._profiles(limit)
        if not profiles:
            return _DEMO_TRIAGE[:limit]
        out = []
        for p in profiles:
            score = float(p.get("threat_score", 0) or 0)
            risk, action, verdict = _risk_band(score)
            ttps = p.get("ttps", []) or []
            out.append({
                "src_ip": p.get("src_ip", "—"),
                "threat_score": round(score, 1),
                "risk": risk,
                "recommended_action": action,
                "verdict": verdict,
                "intent": p.get("classified_intent", "unknown"),
                "tier": p.get("attacker_tier", "beginner"),
                "session_count": p.get("session_count", len(p.get("sessions", []) or [])),
                "ttp_count": len(ttps),
                "top_ttps": [t.get("technique_id") for t in ttps[:4] if t.get("technique_id")],
                "last_seen": p.get("last_seen"),
            })
        return out

    # ── 2. Incident report ────────────────────────────────────────────────────
    def generate_report(self, src_ip: str) -> dict:
        profile = None
        if self.db is not None:
            try:
                profile = self.db["attacker_profiles"].find_one({"src_ip": src_ip}, {"_id": 0})
            except Exception:
                profile = None
        events = self._events_for(src_ip)

        if profile is None and not events:
            # No data for this IP — synthesize from demo triage if present.
            demo = next((d for d in _DEMO_TRIAGE if d["src_ip"] == src_ip), None)
            profile = demo or {"src_ip": src_ip, "threat_score": 0,
                               "classified_intent": "unknown", "attacker_tier": "beginner",
                               "ttps": [], "sessions": []}

        score = float((profile or {}).get("threat_score", 0) or 0)
        risk, action, verdict = _risk_band(score)
        intent = (profile or {}).get("classified_intent", "unknown")
        tier = (profile or {}).get("attacker_tier", "beginner")
        ttps = (profile or {}).get("ttps", []) or []

        report_md = None
        source = "heuristic"
        if self.llm_enabled():
            report_md = llm_complete(
                system=(
                    "You are a senior SOC analyst writing a concise incident report from "
                    "honeypot telemetry. Be specific, factual, and actionable. Use short "
                    "Markdown sections: Summary, Attacker Profile, Observed TTPs, Threat "
                    "Assessment, Recommended Actions. Do not invent data not present."
                ),
                user=self._report_context(src_ip, profile, events),
                max_tokens=900,
            )
            if report_md:
                source = "anthropic"
        if not report_md:
            report_md = self._heuristic_report(src_ip, profile, events, risk, action, verdict)

        report = {
            "src_ip": src_ip,
            "generated_at": time.time(),
            "source": source,
            "risk": risk,
            "recommended_action": action,
            "verdict": verdict,
            "threat_score": round(score, 1),
            "intent": intent,
            "tier": tier,
            "ttps": [t.get("technique_id") for t in ttps if t.get("technique_id")],
            "event_count": len(events),
            "report_md": report_md,
        }
        self._persist(report)
        return report

    def _report_context(self, src_ip, profile, events) -> str:
        p = profile or {}
        lines = [f"Source IP: {src_ip}",
                 f"Threat score: {p.get('threat_score', 0)}",
                 f"Classified intent: {p.get('classified_intent', 'unknown')}",
                 f"Attacker tier: {p.get('attacker_tier', 'beginner')}",
                 f"Sessions: {p.get('session_count', len(p.get('sessions', []) or []))}",
                 f"First seen: {_fmt_ts(p.get('first_seen'))}",
                 f"Last seen: {_fmt_ts(p.get('last_seen'))}"]
        ttps = p.get("ttps", []) or []
        if ttps:
            lines.append("MITRE TTPs: " + ", ".join(
                f"{t.get('technique_id')} {t.get('name', '')}".strip() for t in ttps[:12]))
        if events:
            lines.append("\nRecent events (newest first):")
            for e in events[:20]:
                cmd = e.get("command") or e.get("raw_payload") or ""
                lines.append(f"- [{e.get('severity', '?')}] {e.get('attack_type', '?')} "
                             f"via {e.get('honeypot_source', '?')}:{e.get('dst_port', '?')} {cmd}".rstrip())
        return "\n".join(lines)

    def _heuristic_report(self, src_ip, profile, events, risk, action, verdict) -> str:
        p = profile or {}
        intent = p.get("classified_intent", "unknown")
        tier = p.get("attacker_tier", "beginner")
        score = p.get("threat_score", 0)
        ttps = p.get("ttps", []) or []
        n = len(events)
        atypes = {}
        for e in events:
            atypes[e.get("attack_type", "unknown")] = atypes.get(e.get("attack_type", "unknown"), 0) + 1
        atypes_str = ", ".join(f"{k} ×{v}" for k, v in sorted(atypes.items(), key=lambda x: -x[1])) or "—"
        ttp_str = "\n".join(
            f"- `{t.get('technique_id', '?')}` {t.get('name', '')}".rstrip() for t in ttps[:10]) or "- None mapped yet"
        sample = ""
        for e in events[:6]:
            cmd = (e.get("command") or e.get("raw_payload") or "").strip()
            if cmd:
                sample += f"\n- `{cmd[:90]}`"

        return (
            f"## Summary\n"
            f"Source **{src_ip}** is classified as a **{tier.replace('_', ' ')}** actor with intent "
            f"**{intent.replace('_', ' ')}** ({INTENT_HINT.get(intent, '')}). "
            f"Composite threat score **{round(float(score or 0), 1)}/100** → **{risk.upper()}** risk. "
            f"{n} correlated event(s) observed; activity breakdown: {atypes_str}.\n\n"
            f"## Attacker Profile\n"
            f"- Tier: **{tier.replace('_', ' ')}**\n"
            f"- Intent: **{intent.replace('_', ' ')}**\n"
            f"- Sessions: {p.get('session_count', len(p.get('sessions', []) or []))}\n"
            f"- First seen: {_fmt_ts(p.get('first_seen'))} · Last seen: {_fmt_ts(p.get('last_seen'))}\n\n"
            f"## Observed TTPs (MITRE ATT&CK)\n{ttp_str}\n\n"
            f"## Threat Assessment\n"
            f"{verdict}. The score reflects classifier confidence, breadth of mapped techniques, "
            f"and session persistence. Command samples:{sample or ' —'}\n\n"
            f"## Recommended Actions\n"
            f"- **Primary:** `{action}` the source per the response matrix.\n"
            f"- Preserve session PCAP/logs for forensic review.\n"
            f"- Plant matching canary credentials and watch for reuse.\n\n"
            f"_Generated offline (heuristic). Configure ANTHROPIC_API_KEY for LLM-written narratives._"
        )

    def get_recent_reports(self, limit: int = 20) -> list[dict]:
        if self.db is None:
            return []
        try:
            return list(
                self.db["soc_reports"].find({}, {"_id": 0, "report_md": 0})
                .sort("generated_at", -1).limit(limit)
            )
        except Exception:
            return []

    def _persist(self, report: dict) -> None:
        if self.db is None:
            return
        try:
            self.db["soc_reports"].insert_one(dict(report))
        except Exception as exc:
            logger.debug("soc_reports persist failed: %s", exc)

    # ── 3. Analyst chat ────────────────────────────────────────────────────────
    def answer_question(self, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            return {"answer": "Ask me about the current threats, an IP, or recommended actions.",
                    "source": "heuristic"}
        triage = self.triage_queue(limit=8)
        if self.llm_enabled():
            ctx = "Current SOC triage queue (highest risk first):\n" + "\n".join(
                f"- {t['src_ip']} score={t['threat_score']} risk={t['risk']} "
                f"intent={t['intent']} action={t['recommended_action']}" for t in triage)
            ans = llm_complete(
                system=("You are an AI SOC analyst assistant for the NeuroTrap honeypot "
                        "platform. Answer the analyst's question using ONLY the provided "
                        "triage context. Be concise and concrete; if the data is "
                        "insufficient, say so."),
                user=f"{ctx}\n\nAnalyst question: {question}",
                max_tokens=500,
            )
            if ans:
                return {"answer": ans, "source": "anthropic"}
        return {"answer": self._heuristic_answer(question, triage), "source": "heuristic"}

    def _heuristic_answer(self, question: str, triage: list[dict]) -> str:
        q = question.lower()
        # IP lookup
        for t in triage:
            if t["src_ip"] != "—" and t["src_ip"] in question:
                return (f"{t['src_ip']} is a {t['tier'].replace('_', ' ')} actor "
                        f"({t['intent'].replace('_', ' ')}), score {t['threat_score']}/100 "
                        f"→ {t['risk'].upper()}. Recommended action: {t['recommended_action']}. "
                        f"{t['verdict']}.")
        if not triage:
            return "No active threat actors in the queue right now."
        top = triage[0]
        if any(w in q for w in ("top", "worst", "highest", "priority", "urgent", "critical")):
            return (f"Highest-priority actor is {top['src_ip']} "
                    f"(score {top['threat_score']}/100, {top['risk'].upper()}). "
                    f"{top['verdict']}. Suggested action: {top['recommended_action']}.")
        if any(w in q for w in ("how many", "count", "number", "total")):
            crit = sum(1 for t in triage if t["risk"] in ("critical", "high"))
            return f"{len(triage)} actors in the queue; {crit} at high/critical risk."
        if any(w in q for w in ("block", "action", "respond", "recommend", "do")):
            acts = ", ".join(f"{t['src_ip']}→{t['recommended_action']}" for t in triage[:5])
            return f"Recommended actions (top 5): {acts}."
        return (f"There are {len(triage)} actors under watch. Top threat: {top['src_ip']} "
                f"({top['risk'].upper()}, score {top['threat_score']}). Ask about a specific IP "
                f"for detail, or request an incident report.")

    # ── 4. Shift summary ───────────────────────────────────────────────────────
    def summary(self, hours: int = 24) -> dict:
        triage = self.triage_queue(limit=100)
        total = len(triage)
        by_risk = {"critical": 0, "high": 0, "elevated": 0, "low": 0}
        for t in triage:
            by_risk[t["risk"]] = by_risk.get(t["risk"], 0) + 1
        top = triage[0] if triage else None
        events_24h = 0
        if self.db is not None:
            try:
                events_24h = self.db["alert_events"].count_documents(
                    {"timestamp": {"$gte": time.time() - hours * 3600}})
            except Exception:
                events_24h = 0
        headline = ("No active threats." if not top else
                    f"Top threat {top['src_ip']} ({top['risk'].upper()}, {top['threat_score']}/100) — "
                    f"{top['recommended_action']}.")
        return {
            "window_hours": hours,
            "actors_tracked": total,
            "by_risk": by_risk,
            "events_in_window": events_24h,
            "needs_action": by_risk["critical"] + by_risk["high"],
            "top_threat": top,
            "headline": headline,
            "llm_enabled": self.llm_enabled(),
        }


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    try:
        return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(float(ts)))
    except Exception:
        return str(ts)


# Demo data used when no DB / no captured profiles exist, so the UI is never empty.
_DEMO_TRIAGE = [
    {"src_ip": "91.234.56.78", "threat_score": 94.0, "risk": "critical",
     "recommended_action": "block", "verdict": _risk_band(94)[2],
     "intent": "malware_deployment", "tier": "advanced_human", "session_count": 5,
     "ttp_count": 4, "top_ttps": ["T1105", "T1059", "T1071", "T1486"], "last_seen": time.time() - 120},
    {"src_ip": "185.220.101.4", "threat_score": 76.0, "risk": "high",
     "recommended_action": "isolate", "verdict": _risk_band(76)[2],
     "intent": "credential_harvesting", "tier": "advanced_human", "session_count": 3,
     "ttp_count": 3, "top_ttps": ["T1110", "T1003", "T1078"], "last_seen": time.time() - 600},
    {"src_ip": "45.155.205.99", "threat_score": 52.0, "risk": "elevated",
     "recommended_action": "slow", "verdict": _risk_band(52)[2],
     "intent": "lateral_movement", "tier": "automated_bot", "session_count": 8,
     "ttp_count": 2, "top_ttps": ["T1021", "T1046"], "last_seen": time.time() - 1800},
    {"src_ip": "212.83.146.20", "threat_score": 21.0, "risk": "low",
     "recommended_action": "monitor", "verdict": _risk_band(21)[2],
     "intent": "reconnaissance", "tier": "automated_bot", "session_count": 2,
     "ttp_count": 1, "top_ttps": ["T1046"], "last_seen": time.time() - 3600},
]
