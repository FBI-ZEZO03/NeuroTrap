"""
predictor.py — Predicts an attacker's next move and simulates them forward.

At the heart of the Attacker Digital Twin is a Markov model over MITRE ATT&CK
tactics. A hand-crafted transition matrix encodes how real intrusions typically
progress (e.g. Credential Access most often leads to Lateral Movement), so the
twin produces sensible forecasts with zero training data. When a twin has
actually observed transitions of its own, those are blended in to personalise
the model to that specific adversary.

Two capabilities:
  * predict_next()      — rank the most likely next tactic(s) with probabilities.
  * simulate_forward()  — sample the chain forward N steps to forecast the
                          attacker's likely path (the "twin running ahead").
"""

from __future__ import annotations

import random
from typing import Optional

# Tactic vocabulary used by the transition model.
TACTICS = [
    "Discovery",
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Defense Evasion",
    "Credential Access",
    "Lateral Movement",
    "Command and Control",
    "Exfiltration",
    "Impact",
]

# Representative technique shown to the analyst for each predicted tactic.
REPRESENTATIVE_TECHNIQUE = {
    "Discovery":            ("T1082", "System Information Discovery", "uname -a"),
    "Initial Access":       ("T1190", "Exploit Public-Facing Application", "POST /cgi-bin"),
    "Execution":            ("T1059", "Command & Scripting Interpreter", "bash -c '…'"),
    "Persistence":          ("T1053.003", "Scheduled Task/Job: Cron", "crontab -e"),
    "Privilege Escalation": ("T1548.003", "Abuse Elevation Control: Sudo", "sudo -l"),
    "Defense Evasion":      ("T1222", "File/Directory Permissions Mod.", "chmod 777"),
    "Credential Access":    ("T1003.008", "OS Credential Dumping: /etc/shadow", "cat /etc/shadow"),
    "Lateral Movement":     ("T1021.004", "Remote Services: SSH", "ssh user@10.0.0.5"),
    "Command and Control":  ("T1105", "Ingress Tool Transfer", "wget http://…/x.sh"),
    "Exfiltration":         ("T1041", "Exfiltration Over C2 Channel", "curl -T data"),
    "Impact":               ("T1486", "Data Encrypted for Impact", "ransom.enc"),
}

# Hand-crafted transition matrix: from_tactic → {to_tactic: weight}.
# Weights are normalised at lookup time, so they need not sum to 1.
_TRANSITIONS: dict[str, dict[str, float]] = {
    "Discovery":            {"Credential Access": 25, "Execution": 20, "Privilege Escalation": 15,
                             "Command and Control": 15, "Lateral Movement": 10, "Persistence": 10, "Discovery": 5},
    "Initial Access":       {"Execution": 30, "Discovery": 25, "Persistence": 20,
                             "Command and Control": 15, "Credential Access": 10},
    "Execution":            {"Command and Control": 30, "Persistence": 20, "Privilege Escalation": 20,
                             "Discovery": 15, "Credential Access": 15},
    "Persistence":          {"Privilege Escalation": 25, "Command and Control": 25, "Defense Evasion": 20,
                             "Credential Access": 15, "Lateral Movement": 15},
    "Privilege Escalation": {"Credential Access": 30, "Defense Evasion": 20, "Lateral Movement": 20,
                             "Persistence": 15, "Impact": 15},
    "Defense Evasion":      {"Credential Access": 25, "Lateral Movement": 25, "Command and Control": 20,
                             "Impact": 15, "Persistence": 15},
    "Credential Access":    {"Lateral Movement": 40, "Exfiltration": 20, "Privilege Escalation": 15,
                             "Impact": 15, "Command and Control": 10},
    "Lateral Movement":     {"Credential Access": 25, "Impact": 25, "Exfiltration": 20,
                             "Command and Control": 15, "Persistence": 15},
    "Command and Control":  {"Exfiltration": 30, "Impact": 25, "Lateral Movement": 20,
                             "Persistence": 15, "Credential Access": 10},
    "Exfiltration":         {"Impact": 50, "Command and Control": 25, "Lateral Movement": 25},
    "Impact":               {"Impact": 40, "Command and Control": 30, "Exfiltration": 30},
}

# Global prior used when an attacker has no observed history yet.
_PRIOR = {"Discovery": 30, "Execution": 15, "Credential Access": 15, "Command and Control": 15,
          "Persistence": 10, "Privilege Escalation": 5, "Lateral Movement": 5, "Exfiltration": 3, "Impact": 2}


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in weights.items()}


class TacticPredictor:
    """Markov next-move predictor over MITRE tactics."""

    def __init__(self, observed_sequence: Optional[list[str]] = None, learn_weight: float = 0.4):
        """
        observed_sequence: the attacker's own ordered tactic history. When
        provided, transitions seen in it are blended into the base matrix with
        weight `learn_weight` so the model adapts to this specific adversary.
        """
        self.observed = [t for t in (observed_sequence or []) if t in TACTICS or t in _TRANSITIONS]
        self.learn_weight = learn_weight
        self._observed_transitions = self._count_observed_transitions()

    def _count_observed_transitions(self) -> dict[str, dict[str, float]]:
        counts: dict[str, dict[str, float]] = {}
        for a, b in zip(self.observed, self.observed[1:]):
            counts.setdefault(a, {}).setdefault(b, 0.0)
            counts[a][b] += 1.0
        return counts

    def _row(self, tactic: Optional[str]) -> dict[str, float]:
        base = dict(_TRANSITIONS.get(tactic, _PRIOR)) if tactic else dict(_PRIOR)
        base = _normalise(base)
        seen = self._observed_transitions.get(tactic or "", {})
        if seen:
            seen = _normalise(seen)
            blended = {}
            keys = set(base) | set(seen)
            for k in keys:
                blended[k] = (1 - self.learn_weight) * base.get(k, 0.0) + \
                             self.learn_weight * seen.get(k, 0.0)
            return _normalise(blended)
        return base

    def predict_next(self, current_tactic: Optional[str] = None, top_n: int = 3) -> list[dict]:
        """Return the top_n most likely next tactics with probabilities."""
        if current_tactic is None and self.observed:
            current_tactic = self.observed[-1]
        row = self._row(current_tactic)
        ranked = sorted(row.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        out = []
        for tactic, prob in ranked:
            tid, tname, example = REPRESENTATIVE_TECHNIQUE.get(tactic, ("T0000", tactic, ""))
            out.append({
                "tactic": tactic,
                "probability": round(prob, 3),
                "technique_id": tid,
                "technique_name": tname,
                "example_command": example,
                "kill_chain_stage": _stage(tactic),
            })
        return out

    def simulate_forward(self, start_tactic: Optional[str] = None,
                         steps: int = 5, seed: Optional[int] = None) -> list[dict]:
        """
        Sample the chain forward `steps` times to forecast the attacker's path.
        Deterministic for a given seed so the UI can replay a forecast.
        """
        rng = random.Random(seed)
        current = start_tactic or (self.observed[-1] if self.observed else None)
        forecast = []
        for i in range(steps):
            row = self._row(current)
            if not row:
                break
            choices, probs = zip(*sorted(row.items(), key=lambda kv: kv[1], reverse=True))
            nxt = rng.choices(choices, weights=probs, k=1)[0]
            tid, tname, example = REPRESENTATIVE_TECHNIQUE.get(nxt, ("T0000", nxt, ""))
            forecast.append({
                "step": i + 1,
                "tactic": nxt,
                "probability": round(row[nxt], 3),
                "technique_id": tid,
                "technique_name": tname,
                "example_command": example,
                "kill_chain_stage": _stage(nxt),
            })
            current = nxt
        return forecast


def _stage(tactic: str) -> str:
    from .kill_chain import stage_for_tactic
    return stage_for_tactic(tactic)
