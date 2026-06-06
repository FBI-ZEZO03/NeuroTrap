"""
bias_scorer.py — Scores attacker sessions across 5 cognitive bias dimensions.

Dimensions (Cialdini + MITRE ENGAGE):
  1. Curiosity Gap     — incomplete secrets that beg to be found
  2. Confirmation Bias — fake evidence matching attacker's existing belief
  3. Sunk Cost Trap    — small wins that make the attacker invest more time
  4. Authority Signals — credible internal memos and admin artifacts
  5. Scarcity Framing  — urgency cues that trigger rushed, revealing behavior
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict


@dataclass
class BiasProfile:
    curiosity_gap:    float = 0.0   # 0–100
    confirmation_bias: float = 0.0
    sunk_cost:        float = 0.0
    authority_signal: float = 0.0
    scarcity_framing: float = 0.0

    @property
    def overall(self) -> float:
        return round((self.curiosity_gap + self.confirmation_bias + self.sunk_cost +
                      self.authority_signal + self.scarcity_framing) / 5, 1)

    @property
    def dominant(self) -> str:
        scores = {
            "curiosity_gap":    self.curiosity_gap,
            "confirmation_bias":self.confirmation_bias,
            "sunk_cost":        self.sunk_cost,
            "authority_signal": self.authority_signal,
            "scarcity_framing": self.scarcity_framing,
        }
        return max(scores, key=scores.get)

    def to_dict(self) -> dict:
        return {**asdict(self), "overall": self.overall, "dominant": self.dominant}


# ── Command signals ────────────────────────────────────────────────────────────

_CURIOSITY = re.compile(
    r'(find|locate|search|grep|cat|less|head|tail|ls -la|ls -R|tree)\s+'
    r'.*\.(key|pem|env|conf|cfg|secret|token|vault|private)',
    re.IGNORECASE,
)
_AUTHORITY = re.compile(
    r'(sudo|su |admin|root|passwd|shadow|sudoers|authorized_keys|id_rsa)',
    re.IGNORECASE,
)
_SUNK_COST = re.compile(
    r'(download|wget|curl|scp|rsync|git clone|pip install|apt install)',
    re.IGNORECASE,
)
_SCARCITY = re.compile(
    r'(crontab|at |systemctl enable|chmod \+x|nohup|screen|tmux|disown)',
    re.IGNORECASE,
)


class BiasScorer:
    """
    Continuously scores a session's command stream against 5 bias dimensions.
    Scores are cumulative and capped at 100.
    """

    def score(self, session: dict) -> BiasProfile:
        commands: list[str] = session.get("commands", [])
        duration: float     = session.get("duration_secs", 0)
        login_attempts: int = session.get("login_attempts", 1)
        intent: str         = session.get("classified_intent", "")

        cmd_blob = "\n".join(commands)

        profile = BiasProfile()

        # ── Curiosity Gap ──────────────────────────────────────────
        # Searching for secrets / hidden files → attacker is chasing bait
        curiosity_hits = len(_CURIOSITY.findall(cmd_blob))
        deep_search    = sum(1 for c in commands if "/etc" in c or "/root" in c or "/.ssh" in c)
        profile.curiosity_gap = min(curiosity_hits * 18 + deep_search * 12, 100)

        # ── Confirmation Bias ──────────────────────────────────────
        # Attacker checks if env matches expectations (ls, uname, ifconfig early)
        recon_early = sum(1 for c in commands[:5] if any(t in c for t in ["uname","id","whoami","hostname"]))
        tech_match  = sum(1 for c in commands if intent in ("credential_harvesting","reconnaissance") and "cat" in c)
        profile.confirmation_bias = min(recon_early * 20 + tech_match * 10, 100)

        # ── Sunk Cost Trap ─────────────────────────────────────────
        # Attacker invested time downloading/installing — won't want to leave empty
        install_cmds = len(_SUNK_COST.findall(cmd_blob))
        time_invested = min(duration / 60, 10)  # 0–10 for 0–10 min
        profile.sunk_cost = min(install_cmds * 20 + time_invested * 5, 100)

        # ── Authority Signals ──────────────────────────────────────
        # Attacker is escalating privilege / confirming they have admin access
        auth_hits  = len(_AUTHORITY.findall(cmd_blob))
        priv_esc   = sum(1 for c in commands if "sudo" in c or "chmod 4" in c)
        profile.authority_signal = min(auth_hits * 15 + priv_esc * 20, 100)

        # ── Scarcity Framing ──────────────────────────────────────
        # Attacker is establishing persistence (urgency to secure access)
        persist_cmds = len(_SCARCITY.findall(cmd_blob))
        # High login_attempts at start = rushed, scarcity mindset
        rushed = min(login_attempts / 20, 1.0) * 30
        profile.scarcity_framing = min(persist_cmds * 18 + rushed, 100)

        return profile
