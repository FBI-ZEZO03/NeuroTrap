"""Attacker Digital Twin (ADT) — NeuroTrap Innovation Module 05."""

from .digital_twin import AttackerDigitalTwin, DigitalTwin
from .kill_chain import KILL_CHAIN_STAGES, build_kill_chain
from .predictor import TACTICS, TacticPredictor

__all__ = [
    "AttackerDigitalTwin",
    "DigitalTwin",
    "TacticPredictor",
    "TACTICS",
    "KILL_CHAIN_STAGES",
    "build_kill_chain",
]
