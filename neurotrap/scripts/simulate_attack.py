"""
simulate_attack.py — End-to-end attack simulation for testing all 5 pipeline layers.

Simulates the 5-stage attack campaign from the Week 6 spec:
  1. Reconnaissance nmap scan (synthetic Scapy events)
  2. SSH brute-force (synthetic Cowrie login events)
  3. Successful login + command execution
  4. Malware upload attempt
  5. Lateral movement

Run against a live NeuroTrap stack:
    python scripts/simulate_attack.py --api http://localhost:5000
"""

from __future__ import annotations
import argparse
import json
import time
import random
import string
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[!] requests not installed — install with: pip install requests")

from src.detection.alert_schema import AlertEvent
from src.behavior.ttp_extractor import TTPExtractor
from src.behavior.behavior_engine import BehaviorEngine
from src.behavior.attacker_profile import AttackerProfile
from src.deception.deception_engine import DeceptionEngine
from src.response.response_engine import ResponseEngine

ATTACKER_IP = "198.51.100.42"     # TEST-NET-3 — safe to use in tests


def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def stage1_recon():
    banner("Stage 1 — Reconnaissance (nmap SYN scan)")
    events = []
    for port in [22, 80, 443, 3306, 8080, 445, 21, 23, 25, 110]:
        e = AlertEvent(
            src_ip=ATTACKER_IP,
            dst_port=port,
            attack_type="port_scan",
            severity="low",
            honeypot_source="scapy",
            protocol="tcp",
            extra={"flags": "SYN"},
        )
        events.append(e)
        print(f"  -> SYN -> port {port}")
        time.sleep(0.05)
    print(f"  ✓ {len(events)} port scan events generated")
    return events


def stage2_brute_force(n: int = 50):
    banner(f"Stage 2 — SSH Brute-force ({n} attempts)")
    common_passes = ["admin", "password", "123456", "root", "ubuntu", "test"]
    events = []
    for i in range(n):
        failed = AlertEvent.from_cowrie({
            "eventid": "cowrie.login.failed",
            "src_ip": ATTACKER_IP,
            "dst_port": 22,
            "session": f"bf-{i:04d}",
            "username": random.choice(["root", "admin", "ubuntu"]),
            "password": random.choice(common_passes),
        })
        events.append(failed)
    print(f"  ✓ {n} brute-force events generated")
    return events


def stage3_login_and_commands():
    banner("Stage 3 — Successful Login + Command Execution")
    session_id = "sess-success-001"
    commands = [
        "whoami", "id", "uname -a", "hostname",
        "ifconfig", "ps aux", "cat /etc/passwd",
        "ls /home", "cat /etc/shadow",
    ]
    events = []
    events.append(AlertEvent.from_cowrie({
        "eventid": "cowrie.login.success",
        "src_ip": ATTACKER_IP,
        "dst_port": 22,
        "session": session_id,
        "username": "admin",
        "password": "admin123",
    }))
    for cmd in commands:
        events.append(AlertEvent.from_cowrie({
            "eventid": "cowrie.command.input",
            "src_ip": ATTACKER_IP,
            "dst_port": 22,
            "session": session_id,
            "input": cmd,
        }))
        print(f"  cmd: {cmd}")
    print(f"  ✓ {len(events)} login+command events generated")
    return events, commands, session_id


def stage4_malware_upload():
    banner("Stage 4 — Malware Upload")
    events = []
    events.append(AlertEvent.from_cowrie({
        "eventid": "cowrie.session.file_download",
        "src_ip": ATTACKER_IP,
        "dst_port": 22,
        "session": "sess-success-001",
        "url": "http://198.51.100.99/xmrig",
        "outfile": "/tmp/xmrig",
        "shasum": "deadbeef" * 8,
    }))
    events.append(AlertEvent.from_cowrie({
        "eventid": "cowrie.command.input",
        "src_ip": ATTACKER_IP,
        "dst_port": 22,
        "session": "sess-success-001",
        "input": "chmod +x /tmp/xmrig && /tmp/xmrig --cpu-max-threads-hint 90 -o pool.example.com:3333",
    }))
    print("  ✓ Malware download + execution events generated")
    return events


def stage5_lateral_movement():
    banner("Stage 5 — Lateral Movement")
    events = []
    for target in ["10.0.0.2", "10.0.0.3", "10.0.0.10"]:
        events.append(AlertEvent.from_cowrie({
            "eventid": "cowrie.command.input",
            "src_ip": ATTACKER_IP,
            "dst_port": 22,
            "session": "sess-success-001",
            "input": f"ssh admin@{target}",
        }))
        print(f"  -> lateral SSH attempt to {target}")
    print(f"  ✓ {len(events)} lateral movement events generated")
    return events


def run_local_pipeline(all_events: list[AlertEvent], all_commands: list[str]):
    banner("Running through local analysis pipeline")

    # TTP extraction
    extractor = TTPExtractor()
    ttps = extractor.extract(all_commands)
    print(f"\n  MITRE ATT&CK TTPs detected ({len(ttps)}):")
    for ttp in ttps:
        print(f"    {ttp.technique_id}  {ttp.technique_name}  [{ttp.tactic}]  conf={ttp.confidence:.2f}")

    ttp_score = extractor.threat_score_contribution(all_commands)
    print(f"\n  TTP threat score contribution: {ttp_score:.1f}")

    # Rule-based classification
    session = {
        "src_ip": ATTACKER_IP,
        "commands": all_commands,
        "duration_secs": 450,
        "login_attempts": 55,
        "failed_logins": 50,
    }
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    print(f"\n  Classification: intent={intent}  tier={tier}  confidence={conf:.2f}")

    # Build profile
    profile = AttackerProfile(src_ip=ATTACKER_IP, attacker_tier=tier)
    profile.update_from_session(session, intent, tier, conf, extractor.extract_as_dicts(all_commands), ttp_score)
    print(f"  Threat Score: {profile.threat_score:.1f}/100")

    # Persist events + profile to the live DB so the dashboard reflects real data
    try:
        from src.db import get_db as _get_db
        from src.behavior.attacker_profile import ProfileStore
        _db = _get_db()
        for event in all_events:
            _db["alert_events"].insert_one(event.to_dict())
        store = ProfileStore(_db["attacker_profiles"])
        store.save(profile)
        print(f"  ✓ {len(all_events)} events + 1 attacker profile written to DB")
    except Exception as exc:
        print(f"  [!] DB write skipped: {exc}")

    # Deception environment
    banner("Deception Engine — Spawning environment")
    try:
        from src.db import get_db as _get_db
        _live_db = _get_db()
        engine = DeceptionEngine(_live_db, docker_client=None)
    except Exception:
        mock_db = type("MockDB", (), {"__getitem__": lambda s, k: type("C", (), {
            "update_one": lambda *a, **kw: None,
            "insert_one": lambda *a: None,
            "find_one": lambda *a, **kw: None,
        })()})()
        engine = DeceptionEngine(mock_db, docker_client=None)
    env = engine.generate_environment(profile)
    print(f"  env_id:   {env.env_id}")
    print(f"  hostname: {env.hostname}")
    print(f"  services: {env.services}")
    print(f"  tier:     {env.attacker_tier}")

    # Response decision
    banner("Response Engine — Evaluating threat")
    mock_db = type("MockDB", (), {"__getitem__": lambda s, k: type("C", (), {
        "update_one": lambda *a, **kw: None,
        "insert_one": lambda *a: None,
        "find_one": lambda *a, **kw: None,
    })()})()
    r_engine = ResponseEngine(mock_db)
    with __import__("unittest.mock", fromlist=["patch"]).patch.object(r_engine, "_execute_async", lambda f, *a: None):
        decision = r_engine.evaluate(profile)
    print(f"  Action taken: {decision.action}")
    print(f"  Score at decision: {decision.threat_score:.1f}")

    banner("Simulation Complete")
    print(f"  Total events:    {len(all_events)}")
    print(f"  Total commands:  {len(all_commands)}")
    print(f"  TTPs detected:   {len(ttps)}")
    print(f"  Threat score:    {profile.threat_score:.1f}/100")
    print(f"  Response:        {decision.action}")
    print()


def main():
    parser = argparse.ArgumentParser(description="NeuroTrap E2E attack simulation")
    parser.add_argument("--api", help="Base URL of running API (e.g. http://localhost:5000)")
    parser.add_argument("--brute-count", type=int, default=50)
    args = parser.parse_args()

    all_events: list[AlertEvent] = []
    all_commands: list[str] = []

    all_events.extend(stage1_recon())
    all_events.extend(stage2_brute_force(args.brute_count))
    stage3_events, commands, _ = stage3_login_and_commands()
    all_events.extend(stage3_events)
    all_commands.extend(commands)
    all_events.extend(stage4_malware_upload())
    all_commands.extend(["chmod +x /tmp/xmrig", "/tmp/xmrig --cpu-max-threads-hint 90"])
    all_events.extend(stage5_lateral_movement())
    all_commands.extend(["ssh admin@10.0.0.2", "ssh admin@10.0.0.3"])

    run_local_pipeline(all_events, all_commands)


if __name__ == "__main__":
    main()
