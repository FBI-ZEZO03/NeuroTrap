"""Tests for the autonomous response engine decision logic."""

import pytest
from unittest.mock import MagicMock, patch
from src.response.response_engine import ResponseEngine, ResponseDecision


def make_mock_profile(ip="1.2.3.4", score=50.0, intent="reconnaissance", tier="beginner", ttps=None):
    p = MagicMock()
    p.src_ip = ip
    p.threat_score = score
    p.classified_intent = intent
    p.attacker_tier = tier
    p.ttps = ttps or []
    p.is_blocked = False
    return p


@pytest.fixture
def engine():
    db = MagicMock()
    db.__getitem__.return_value = MagicMock()
    return ResponseEngine(db)


def test_low_score_log_only(engine):
    profile = make_mock_profile(score=25.0)
    with patch.object(engine, '_execute_async') as mock_exec:
        decision = engine.evaluate(profile)
    assert decision.action == "log_only"
    mock_exec.assert_not_called()


def test_medium_score_slow_redirect(engine):
    profile = make_mock_profile(score=55.0)
    with patch.object(engine, '_execute_async') as mock_exec:
        decision = engine.evaluate(profile)
    assert decision.action == "slow_redirect"
    mock_exec.assert_called_once()


def test_high_score_isolate_alert(engine):
    profile = make_mock_profile(score=80.0)
    with patch.object(engine, '_execute_async') as mock_exec:
        decision = engine.evaluate(profile)
    assert decision.action == "isolate_alert"


def test_critical_score_block_emergency(engine):
    profile = make_mock_profile(score=95.0)
    with patch.object(engine, '_execute_async') as mock_exec:
        decision = engine.evaluate(profile)
    assert decision.action == "block_emergency"


def test_threshold_boundaries(engine):
    for score, expected in [(39.9, "log_only"), (40.0, "slow_redirect"), (70.0, "isolate_alert"), (90.0, "block_emergency")]:
        profile = make_mock_profile(score=score)
        with patch.object(engine, '_execute_async'):
            decision = engine.evaluate(profile)
        assert decision.action == expected, f"score={score} expected={expected} got={decision.action}"


def test_format_alert_body(engine):
    profile = make_mock_profile(score=75.0, intent="malware_deployment", tier="advanced_human")
    profile.ttps = [{"technique_id": "T1105"}, {"technique_id": "T1003.008"}]
    decision = ResponseDecision("isolate_alert", "1.2.3.4", 75.0)
    body = engine._format_alert_body(profile, decision)
    assert "1.2.3.4" in body
    assert "malware_deployment" in body
    assert "T1105" in body
