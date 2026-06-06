"""
classifier.py — ML-based attacker intent classifier.

Trained on Cowrie session feature matrices; supports online classification
of new sessions. Targets F1 > 0.85 across six intent categories.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.svm import SVC
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, f1_score
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Intent labels ─────────────────────────────────────────────────────────────
INTENT_LABELS = [
    "reconnaissance",
    "credential_harvesting",
    "malware_deployment",
    "lateral_movement",
    "cryptomining",
    "bot_enrollment",
]

# ── Attacker tiers (from behavioral fingerprint) ──────────────────────────────
ATTACKER_TIERS = ["beginner", "automated_bot", "advanced_human"]

MODEL_PATH = Path(os.getenv("MODEL_DIR", "/app/data/models"))


class SessionFeatureExtractor:
    """Converts a raw Cowrie session dict into a numeric feature vector."""

    DANGEROUS_COMMANDS = {
        "wget", "curl", "chmod", "chown", "rm", "dd", "nc", "netcat",
        "python", "python3", "perl", "bash", "sh", "crontab", "passwd",
        "useradd", "ssh", "scp", "rsync", "kill", "pkill", "nohup",
    }

    RECON_COMMANDS = {
        "whoami", "id", "uname", "hostname", "ifconfig", "ip", "ps",
        "ls", "pwd", "cat", "find", "env", "printenv", "df", "free",
        "netstat", "ss", "lsof", "history",
    }

    def extract(self, session: dict) -> np.ndarray:
        commands: list[str] = session.get("commands", [])
        cmd_set = {c.split()[0] for c in commands if c.strip()}

        dangerous_count = len(cmd_set & self.DANGEROUS_COMMANDS)
        recon_count = len(cmd_set & self.RECON_COMMANDS)
        total_commands = len(commands)
        unique_commands = len(cmd_set)
        download_attempts = sum(1 for c in commands if any(t in c for t in ["wget ", "curl ", "tftp "]))
        file_access = sum(1 for c in commands if any(t in c for t in ["cat /etc", "cat /proc", "/shadow", "/passwd"]))
        session_duration = float(session.get("duration_secs", 0))
        login_attempts = int(session.get("login_attempts", 1))
        failed_logins = int(session.get("failed_logins", 0))
        has_persistence = int(any("crontab" in c or ".bashrc" in c for c in commands))
        has_lateral = int(any("ssh " in c or "scp " in c for c in commands))

        return np.array([
            total_commands,
            unique_commands,
            dangerous_count,
            recon_count,
            download_attempts,
            file_access,
            session_duration,
            login_attempts,
            failed_logins,
            has_persistence,
            has_lateral,
            dangerous_count / max(total_commands, 1),
            recon_count / max(total_commands, 1),
        ], dtype=float)


class AttackerClassifier:
    """
    Ensemble classifier (RandomForest + SVM voting) for attacker intent.

    Train:
        clf = AttackerClassifier()
        clf.train(sessions, labels)
        clf.save()

    Predict:
        clf = AttackerClassifier.load()
        intent, tier, confidence = clf.predict(session_dict)
    """

    def __init__(self):
        self.extractor = SessionFeatureExtractor()
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.label_encoder = LabelEncoder() if SKLEARN_AVAILABLE else None
        self.model = None

    def train(self, sessions: list[dict], labels: list[str]) -> float:
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed")

        X = np.vstack([self.extractor.extract(s) for s in sessions])
        y = self.label_encoder.fit_transform(labels)

        X = self.scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        rf = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
        svm = SVC(kernel="rbf", probability=True, C=10, gamma="scale", random_state=42)

        self.model = VotingClassifier(
            estimators=[("rf", rf), ("svm", svm)],
            voting="soft",
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        f1 = f1_score(y_test, y_pred, average="macro")
        logger.info("Classifier trained — macro F1=%.3f", f1)
        logger.info("\n%s", classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))
        return f1

    def predict(self, session: dict) -> tuple[str, str, float]:
        """Returns (intent_label, attacker_tier, confidence_score)."""
        if self.model is None:
            return "unknown", "beginner", 0.0

        feats = self.extractor.extract(session).reshape(1, -1)
        feats = self.scaler.transform(feats)

        probs = self.model.predict_proba(feats)[0]
        idx = int(np.argmax(probs))
        confidence = float(probs[idx])
        intent = self.label_encoder.inverse_transform([idx])[0]

        tier = self._classify_tier(session, intent)
        return intent, tier, confidence

    def _classify_tier(self, session: dict, intent: str) -> str:
        commands = session.get("commands", [])
        duration = session.get("duration_secs", 0)
        login_attempts = session.get("login_attempts", 1)

        if login_attempts > 100 and duration < 30:
            return "automated_bot"
        if intent in ("lateral_movement", "malware_deployment") and len(commands) > 20:
            return "advanced_human"
        return "beginner"

    def save(self):
        MODEL_PATH.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, MODEL_PATH / "classifier.joblib")
        joblib.dump(self.scaler, MODEL_PATH / "scaler.joblib")
        joblib.dump(self.label_encoder, MODEL_PATH / "label_encoder.joblib")
        logger.info("Model saved to %s", MODEL_PATH)

    @classmethod
    def load(cls) -> "AttackerClassifier":
        instance = cls()
        instance.model = joblib.load(MODEL_PATH / "classifier.joblib")
        instance.scaler = joblib.load(MODEL_PATH / "scaler.joblib")
        instance.label_encoder = joblib.load(MODEL_PATH / "label_encoder.joblib")
        return instance
