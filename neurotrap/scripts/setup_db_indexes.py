"""
setup_db_indexes.py — Creates all required indexes for NeuroTrap.

Run once after first docker compose up:
    python scripts/setup_db_indexes.py

Uses the central data layer, so it works against MongoDB when available and is a
harmless no-op (indexes are not needed) against the embedded SQLite fallback.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db import get_db, backend  # noqa: E402

ASCENDING = 1
DESCENDING = -1


def main():
    db = get_db()
    print(f"Storage backend: {backend()}")

    # alert_events
    db["alert_events"].create_index([("src_ip", ASCENDING)])
    db["alert_events"].create_index([("timestamp", DESCENDING)])
    db["alert_events"].create_index([("attack_type", ASCENDING)])
    db["alert_events"].create_index([("severity", ASCENDING)])
    db["alert_events"].create_index([("honeypot_source", ASCENDING)])
    print("[OK]alert_events indexes created")

    # attacker_profiles
    db["attacker_profiles"].create_index([("src_ip", ASCENDING)], unique=True)
    db["attacker_profiles"].create_index([("threat_score", DESCENDING)])
    db["attacker_profiles"].create_index([("last_seen", DESCENDING)])
    db["attacker_profiles"].create_index([("classified_intent", ASCENDING)])
    print("[OK]attacker_profiles indexes created")

    # deception_environments
    db["deception_environments"].create_index([("env_id", ASCENDING)], unique=True)
    db["deception_environments"].create_index([("src_ip", ASCENDING)])
    db["deception_environments"].create_index([("is_active", ASCENDING)])
    print("[OK]deception_environments indexes created")

    # response_log
    db["response_log"].create_index([("timestamp", DESCENDING)])
    db["response_log"].create_index([("src_ip", ASCENDING)])
    db["response_log"].create_index([("action", ASCENDING)])
    print("[OK]response_log indexes created")

    # cowrie_sessions
    db["cowrie_sessions"].create_index([("src_ip", ASCENDING)])
    db["cowrie_sessions"].create_index([("analyzed", ASCENDING)])
    print("[OK]cowrie_sessions indexes created")

    # attacker_twins (ADT — Attacker Digital Twin)
    db["attacker_twins"].create_index([("src_ip", ASCENDING)], unique=True)
    db["attacker_twins"].create_index([("threat_score", DESCENDING)])
    db["attacker_twins"].create_index([("updated_at", DESCENDING)])
    print("[OK] attacker_twins indexes created")

    # honeypot_sessions (native Python honeypots)
    db["honeypot_sessions"].create_index([("src_ip", ASCENDING)])
    db["honeypot_sessions"].create_index([("honeypot", ASCENDING)])
    db["honeypot_sessions"].create_index([("started_at", DESCENDING)])
    db["honeypot_sessions"].create_index([("analyzed", ASCENDING)])
    print("[OK]honeypot_sessions indexes created")

    print("\nAll indexes created successfully.")
    if hasattr(db, "close"):
        db.close()


if __name__ == "__main__":
    main()
