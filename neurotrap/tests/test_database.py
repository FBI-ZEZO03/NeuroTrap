"""Tests for the central DB layer's embedded SQLite fallback store."""

import os
import pytest

from src.db.fallback_store import FallbackDB


@pytest.fixture
def db(tmp_path):
    path = os.path.join(tmp_path, "test.db")
    database = FallbackDB(path)
    yield database
    database.close()


def test_insert_and_count(db):
    c = db["alert_events"]
    c.insert_one({"src_ip": "1.1.1.1", "attack_type": "brute_force"})
    c.insert_one({"src_ip": "2.2.2.2", "attack_type": "port_scan"})
    assert c.count_documents({}) == 2
    assert c.count_documents({"attack_type": "brute_force"}) == 1


def test_find_projection_strips_id(db):
    c = db["alert_events"]
    c.insert_one({"src_ip": "1.1.1.1"})
    doc = c.find_one({"src_ip": "1.1.1.1"}, {"_id": 0})
    assert "_id" not in doc
    assert doc["src_ip"] == "1.1.1.1"


def test_update_one_upsert_inserts_then_updates(db):
    c = db["deception_environments"]
    res = c.update_one({"env_id": "abc"}, {"$set": {"is_active": True}}, upsert=True)
    assert res.upserted_id is not None
    assert c.count_documents({"env_id": "abc"}) == 1

    res2 = c.update_one({"env_id": "abc"}, {"$set": {"is_active": False}}, upsert=True)
    assert res2.matched_count == 1
    assert c.find_one({"env_id": "abc"})["is_active"] is False
    assert c.count_documents({"env_id": "abc"}) == 1  # no duplicate


def test_comparison_operators(db):
    c = db["attacker_profiles"]
    for i in range(5):
        c.insert_one({"src_ip": f"10.0.0.{i}", "threat_score": i * 20, "last_seen": i})
    assert c.count_documents({"threat_score": {"$gte": 60}}) == 2
    assert c.count_documents({"last_seen": {"$gt": 2}}) == 2
    assert c.count_documents({"threat_score": {"$in": [0, 80]}}) == 2


def test_sort_skip_limit(db):
    c = db["alert_events"]
    for ts in [10, 50, 30, 20, 40]:
        c.insert_one({"timestamp": ts})
    docs = list(c.find({}, {"_id": 0}).sort("timestamp", -1).skip(1).limit(2))
    assert [d["timestamp"] for d in docs] == [40, 30]


def test_dotted_path_query(db):
    c = db["alert_events"]
    c.insert_one({"connection": {"protocol": "ftp"}})
    c.insert_one({"connection": {"protocol": "http"}})
    assert c.count_documents({"connection.protocol": "ftp"}) == 1


def test_aggregate_group_sum_avg_switch(db):
    """Mirrors the /api/events/stats aggregation pipeline."""
    c = db["alert_events"]
    c.insert_one({"attack_type": "brute_force", "severity": "critical"})
    c.insert_one({"attack_type": "brute_force", "severity": "low"})
    c.insert_one({"attack_type": "port_scan", "severity": "medium"})

    pipeline = [
        {"$group": {
            "_id": "$attack_type",
            "count": {"$sum": 1},
            "avg_severity_score": {"$avg": {
                "$switch": {
                    "branches": [
                        {"case": {"$eq": ["$severity", "critical"]}, "then": 4},
                        {"case": {"$eq": ["$severity", "high"]}, "then": 3},
                        {"case": {"$eq": ["$severity", "medium"]}, "then": 2},
                    ],
                    "default": 1,
                }
            }},
        }},
        {"$sort": {"count": -1}},
    ]
    result = c.aggregate(pipeline)
    by_type = {r["_id"]: r for r in result}
    assert by_type["brute_force"]["count"] == 2
    assert by_type["brute_force"]["avg_severity_score"] == pytest.approx(2.5)  # (4+1)/2
    assert by_type["port_scan"]["avg_severity_score"] == pytest.approx(2.0)
    # $sort count desc → brute_force first
    assert result[0]["_id"] == "brute_force"


def test_delete_many(db):
    c = db["response_log"]
    c.insert_one({"action": "block"})
    c.insert_one({"action": "block"})
    c.insert_one({"action": "allow"})
    res = c.delete_many({"action": "block"})
    assert res.deleted_count == 2
    assert c.count_documents({}) == 1


def test_persistence_across_reopen(tmp_path):
    path = os.path.join(tmp_path, "persist.db")
    d1 = FallbackDB(path)
    d1["alert_events"].insert_one({"src_ip": "5.5.5.5"})
    d1.close()

    d2 = FallbackDB(path)
    assert d2["alert_events"].count_documents({"src_ip": "5.5.5.5"}) == 1
    d2.close()
