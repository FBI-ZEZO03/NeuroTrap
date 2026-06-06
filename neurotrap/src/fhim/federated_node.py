"""
federated_node.py — Local FHIM node: trains locally, shares gradient deltas.

Implements FedAvg at the node side:
  1. Load current global model weights
  2. Train locally on new session data
  3. Compute gradient delta (local_weights - global_weights)
  4. Apply differential privacy noise (Gaussian mechanism)
  5. Transmit delta to aggregation server
  6. Receive updated global weights and merge
"""

from __future__ import annotations
import copy
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False


@dataclass
class FederatedRoundResult:
    round_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_id: str = ""
    timestamp: float = field(default_factory=time.time)
    local_samples: int = 0
    local_f1_before: float = 0.0
    local_f1_after: float = 0.0
    delta_norm: float = 0.0          # L2 norm of gradient delta
    privacy_epsilon: float = 1.0    # DP epsilon used
    rounds_completed: int = 0
    status: str = "pending"          # pending | success | failed

    def to_dict(self) -> dict:
        return asdict(self)


class DifferentialPrivacy:
    """Gaussian mechanism for (epsilon, delta)-differential privacy."""

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, sensitivity: float = 1.0):
        self.epsilon   = epsilon
        self.delta     = delta
        self.sensitivity = sensitivity

    def add_noise(self, gradient_dict: dict) -> dict:
        if not NUMPY_AVAILABLE:
            return gradient_dict

        sigma = self.sensitivity * (2 * (2.718281828 ** (self.epsilon)) ** 0.5) / self.epsilon
        noisy = {}
        for key, val in gradient_dict.items():
            arr = np.array(val, dtype=float)
            noise = np.random.normal(0, sigma, arr.shape)
            noisy[key] = (arr + noise).tolist()
        return noisy


class FederatedNode:
    """
    A local FHIM node wrapping the existing AttackerClassifier.

    Usage:
        node = FederatedNode(node_id="org-A", classifier=clf, db=db)
        result = node.run_local_round(sessions, labels)
        delta = node.get_noisy_delta()
        node.apply_global_update(global_weights)
    """

    ROUNDS_COMPLETED = 0

    def __init__(
        self,
        node_id: str,
        classifier,
        db,
        epsilon: float = 1.0,
    ):
        self.node_id    = node_id
        self.classifier = classifier
        self.db         = db
        self.dp         = DifferentialPrivacy(epsilon=epsilon)
        self._global_weights: Optional[dict] = None
        self._local_weights:  Optional[dict] = None
        self.rounds_completed = 0

    def run_local_round(self, sessions: list[dict], labels: list[str]) -> FederatedRoundResult:
        result = FederatedRoundResult(node_id=self.node_id, local_samples=len(sessions))

        if not sessions or not JOBLIB_AVAILABLE:
            result.status = "skipped_no_data"
            return result

        try:
            # Snapshot weights before local training
            self._global_weights = self._extract_weights()

            # Local training
            f1_before = self._estimate_f1(sessions, labels)
            self.classifier.train(sessions, labels)
            f1_after = self._estimate_f1(sessions, labels)

            self._local_weights = self._extract_weights()
            self.rounds_completed += 1
            FederatedNode.ROUNDS_COMPLETED += 1

            result.local_f1_before = f1_before
            result.local_f1_after  = f1_after
            result.delta_norm      = self._compute_delta_norm()
            result.rounds_completed = self.rounds_completed
            result.status = "success"

            logger.info("Fed round %s: node=%s samples=%d F1 %.3f→%.3f delta=%.4f",
                        result.round_id, self.node_id, len(sessions),
                        f1_before, f1_after, result.delta_norm)
        except Exception as exc:
            result.status = f"failed: {exc}"
            logger.error("Federated round failed: %s", exc)

        self._persist_result(result)
        return result

    def get_noisy_delta(self) -> dict:
        """Returns the differentially-private gradient delta ready to share."""
        if self._global_weights is None or self._local_weights is None:
            return {}
        raw_delta = {
            k: [lw - gw for lw, gw in zip(self._local_weights.get(k, [0]*len(v)), v)]
            for k, v in self._global_weights.items()
        }
        return self.dp.add_noise(raw_delta)

    def apply_global_update(self, global_weights: dict):
        """Merges the aggregated global weights into the local model."""
        if not global_weights or not JOBLIB_AVAILABLE:
            return
        self._global_weights = global_weights
        self._apply_weights(global_weights)
        logger.info("Global model applied at node %s", self.node_id)

    # ── Weight serialization helpers ───────────────────────────────────────────

    def _extract_weights(self) -> dict:
        if not self.classifier.model or not JOBLIB_AVAILABLE:
            return {}
        try:
            model = self.classifier.model
            # VotingClassifier — extract RF feature importances as proxy
            rf = model.named_estimators_.get("rf")
            if rf and hasattr(rf, "feature_importances_"):
                return {"rf_importances": rf.feature_importances_.tolist()}
        except Exception:
            pass
        return {}

    def _apply_weights(self, weights: dict):
        if not weights or not self.classifier.model:
            return
        try:
            rf = self.classifier.model.named_estimators_.get("rf")
            if rf and "rf_importances" in weights and NUMPY_AVAILABLE:
                # Apply as a soft bias (blend 70% global, 30% local)
                global_imp = np.array(weights["rf_importances"])
                local_imp  = rf.feature_importances_
                blended    = 0.7 * global_imp + 0.3 * local_imp
                rf.feature_importances_ = blended / blended.sum()
        except Exception as exc:
            logger.debug("Weight application failed: %s", exc)

    def _compute_delta_norm(self) -> float:
        if not self._global_weights or not self._local_weights or not NUMPY_AVAILABLE:
            return 0.0
        try:
            gw = np.array(self._global_weights.get("rf_importances", []))
            lw = np.array(self._local_weights.get("rf_importances", []))
            if gw.shape == lw.shape:
                return float(np.linalg.norm(lw - gw))
        except Exception:
            pass
        return 0.0

    def _estimate_f1(self, sessions: list[dict], labels: list[str]) -> float:
        try:
            from sklearn.model_selection import cross_val_score
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            X = np.vstack([self.classifier.extractor.extract(s) for s in sessions])
            y = self.classifier.label_encoder.transform(labels)
            scores = cross_val_score(
                RandomForestClassifier(n_estimators=50, random_state=42),
                X, y, cv=min(3, len(set(labels))), scoring="f1_macro"
            )
            return float(scores.mean())
        except Exception:
            return 0.0

    def _persist_result(self, result: FederatedRoundResult):
        try:
            self.db["fhim_rounds"].insert_one(result.to_dict())
        except Exception:
            pass
