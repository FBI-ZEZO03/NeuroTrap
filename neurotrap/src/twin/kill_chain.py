"""
kill_chain.py — Maps observed attacker activity onto the cyber kill chain.

The Attacker Digital Twin tracks where an adversary sits in the 7-stage
Lockheed-Martin kill chain. Both MITRE ATT&CK tactics (from the TTP extractor)
and raw honeypot attack types (from alert_events) are folded into a single
progression model, so a twin built purely from honeypot captures still yields a
meaningful stage estimate.
"""

from __future__ import annotations

# Canonical kill-chain stages, in order.
KILL_CHAIN_STAGES = [
    "Reconnaissance",
    "Weaponization",
    "Delivery",
    "Exploitation",
    "Installation",
    "Command & Control",
    "Actions on Objectives",
]

_STAGE_INDEX = {s: i for i, s in enumerate(KILL_CHAIN_STAGES)}

# MITRE ATT&CK tactic → kill-chain stage.
TACTIC_TO_STAGE = {
    "Reconnaissance": "Reconnaissance",
    "Discovery": "Reconnaissance",
    "Resource Development": "Weaponization",
    "Initial Access": "Delivery",
    "Execution": "Exploitation",
    "Privilege Escalation": "Exploitation",
    "Persistence": "Installation",
    "Defense Evasion": "Installation",
    "Command and Control": "Command & Control",
    "Credential Access": "Actions on Objectives",
    "Lateral Movement": "Actions on Objectives",
    "Collection": "Actions on Objectives",
    "Exfiltration": "Actions on Objectives",
    "Impact": "Actions on Objectives",
}

# Honeypot alert_events.attack_type → MITRE tactic (so honeypot-only twins work).
ATTACK_TYPE_TO_TACTIC = {
    "port_scan": "Discovery",
    "tool_fingerprint": "Discovery",
    "protocol_anomaly": "Discovery",
    "brute_force": "Credential Access",
    "command_injection": "Execution",
    "malware_upload": "Command and Control",
    "data_exfiltration": "Exfiltration",
    "lateral_movement": "Lateral Movement",
    "unknown": "Discovery",
}


def stage_for_tactic(tactic: str) -> str:
    return TACTIC_TO_STAGE.get(tactic, "Reconnaissance")


def tactic_for_attack_type(attack_type: str) -> str:
    return ATTACK_TYPE_TO_TACTIC.get(attack_type, "Discovery")


def build_kill_chain(tactics: list[str]) -> dict:
    """
    Given the set of tactics an attacker has exercised, return a kill-chain
    progression summary:

        {
          "stages": [{"name", "reached", "index"}, ...],   # all 7, ordered
          "current_stage": "Exploitation",
          "current_index": 3,
          "depth": 4,                  # number of distinct stages reached
          "progress": 0.57,            # current_index / (len-1)
          "furthest": "Exploitation",
        }
    """
    reached = set()
    for t in tactics:
        reached.add(stage_for_tactic(t))

    reached_indices = sorted(_STAGE_INDEX[s] for s in reached) if reached else []
    current_index = reached_indices[-1] if reached_indices else 0
    current_stage = KILL_CHAIN_STAGES[current_index]

    stages = [
        {"name": name, "index": i, "reached": (name in reached)}
        for i, name in enumerate(KILL_CHAIN_STAGES)
    ]

    progress = current_index / (len(KILL_CHAIN_STAGES) - 1) if reached else 0.0

    return {
        "stages": stages,
        "current_stage": current_stage,
        "current_index": current_index,
        "depth": len(reached),
        "progress": round(progress, 3),
        "furthest": current_stage,
    }
