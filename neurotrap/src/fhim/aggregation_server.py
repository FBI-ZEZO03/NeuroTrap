"""
aggregation_server.py — FedAvg aggregation server for FHIM.

Collects gradient deltas from all nodes, applies Federated Averaging,
and distributes the improved global model weights back to participants.
"""

from __future__ import annotations
import time
import logging
import threading
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class NodeStatus:
    node_id: str
    org_name: str
    last_round: float = 0.0
    rounds_total: int = 0
    f1_score: float = 0.0
    samples_contributed: int = 0
    status: str = "idle"       # idle | training | aggregating | synced
    location: str = ""


@dataclass
class AggregationRound:
    round_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    participants: int = 0
    total_samples: int = 0
    global_f1_before: float = 0.0
    global_f1_after: float = 0.0
    avg_delta_norm: float = 0.0
    status: str = "complete"

    def to_dict(self) -> dict:
        return asdict(self)


class FedAvgServer:
    """
    Federated Averaging aggregation server.

    Maintains a registry of participating nodes and the current global model.
    Simulates a realistic multi-org federated network for demonstration.

    Usage:
        server = FedAvgServer(db)
        server.register_node("org-A", "Acme Corp", location="US")
        server.receive_delta("org-A", delta_dict, samples=500)
        global_weights = server.aggregate()
    """

    MIN_NODES_FOR_AGGREGATION = 2

    def __init__(self, db):
        self.db = db
        self._nodes: dict[str, NodeStatus] = {}
        self._pending_deltas: dict[str, dict] = {}
        self._global_weights: dict = {}
        self._round_history: list[AggregationRound] = []
        self._lock = threading.Lock()

        # Seed demo nodes for the dashboard
        self._seed_demo_nodes()

    def register_node(self, node_id: str, org_name: str, location: str = "", f1: float = 0.0):
        with self._lock:
            self._nodes[node_id] = NodeStatus(
                node_id=node_id, org_name=org_name, location=location, f1_score=f1
            )
        logger.info("FHIM node registered: %s (%s)", node_id, org_name)

    def receive_delta(self, node_id: str, delta: dict, samples: int = 0, f1: float = 0.0):
        with self._lock:
            self._pending_deltas[node_id] = delta
            if node_id in self._nodes:
                self._nodes[node_id].rounds_total     += 1
                self._nodes[node_id].last_round        = time.time()
                self._nodes[node_id].samples_contributed += samples
                self._nodes[node_id].f1_score          = f1
                self._nodes[node_id].status            = "aggregating"
        logger.info("Delta received from %s (%d samples)", node_id, samples)

    def aggregate(self) -> dict:
        """Run FedAvg over all pending deltas and return new global weights."""
        with self._lock:
            if len(self._pending_deltas) < self.MIN_NODES_FOR_AGGREGATION:
                logger.info("Waiting for more nodes (%d/%d)", len(self._pending_deltas), self.MIN_NODES_FOR_AGGREGATION)
                return self._global_weights

            global_weights = self._fedavg(list(self._pending_deltas.values()))
            self._global_weights = global_weights
            self._pending_deltas.clear()

            for node in self._nodes.values():
                node.status = "synced"

            round_result = AggregationRound(
                participants=len(self._nodes),
                total_samples=sum(n.samples_contributed for n in self._nodes.values()),
                global_f1_after=max((n.f1_score for n in self._nodes.values()), default=0.0),
            )
            self._round_history.append(round_result)
            self._persist_round(round_result)

        logger.info("FedAvg round complete — %d nodes aggregated", round_result.participants)
        return global_weights

    def get_node_status(self) -> list[dict]:
        with self._lock:
            return [asdict(n) for n in self._nodes.values()]

    def get_round_history(self, limit: int = 10) -> list[dict]:
        try:
            rows = list(self.db["fhim_aggregation_rounds"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
            if rows:
                return rows
        except Exception:
            pass
        return [r.to_dict() for r in reversed(self._round_history[-limit:])]

    def get_global_f1(self) -> float:
        nodes = list(self._nodes.values())
        if not nodes:
            return 0.0
        return round(sum(n.f1_score for n in nodes) / len(nodes), 3)

    # ── FedAvg implementation ──────────────────────────────────────────────────

    @staticmethod
    def _fedavg(deltas: list[dict]) -> dict:
        if not deltas or not NUMPY_AVAILABLE:
            return {}
        all_keys = set()
        for d in deltas:
            all_keys.update(d.keys())
        averaged = {}
        for key in all_keys:
            arrays = [np.array(d[key]) for d in deltas if key in d]
            if arrays:
                averaged[key] = np.mean(arrays, axis=0).tolist()
        return averaged

    def _persist_round(self, result: AggregationRound):
        try:
            self.db["fhim_aggregation_rounds"].insert_one(result.to_dict())
        except Exception:
            pass

    # ── Demo seed ─────────────────────────────────────────────────────────────

    def _seed_demo_nodes(self):
        demo_nodes = [
            ("node-university-A", "Cairo University SOC",     "EG",  0.87),
            ("node-enterprise-B", "Acme Financial Services",  "US",  0.91),
            ("node-research-C",   "Fraunhofer FKIE Lab",      "DE",  0.89),
            ("node-telecom-D",    "SaudiTelecom CSIRT",       "SA",  0.85),
        ]
        for nid, org, loc, f1 in demo_nodes:
            self.register_node(nid, org, location=loc, f1=f1)
            self._nodes[nid].rounds_total = 12
            self._nodes[nid].samples_contributed = 1800 + hash(nid) % 500
            self._nodes[nid].last_round = time.time() - (hash(nid) % 3600)
            self._nodes[nid].status = "synced"

        # Seed demo round history
        base = time.time()
        for i, (f1_after, participants) in enumerate([
            (0.81, 2), (0.84, 3), (0.85, 3), (0.86, 4),
            (0.87, 4), (0.87, 4), (0.88, 4), (0.88, 4),
        ]):
            self._round_history.append(AggregationRound(
                timestamp=base - (8 - i) * 10800,
                participants=participants,
                total_samples=participants * 500 + i * 200,
                global_f1_before=f1_after - 0.02,
                global_f1_after=f1_after,
                avg_delta_norm=round(0.05 - i * 0.003, 4),
                status="complete",
            ))
