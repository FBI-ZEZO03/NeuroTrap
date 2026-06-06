"""Tests for the deception engine — environment generation and lifecycle."""

import time
import pytest
from unittest.mock import MagicMock
from src.deception.deception_engine import DeceptionEngine
from src.behavior.attacker_profile import AttackerProfile


def make_profile(ip="10.0.0.1", tier="beginner", score=35.0, ttps=None):
    p = AttackerProfile(src_ip=ip, attacker_tier=tier, threat_score=score, ttps=ttps or [])
    return p


@pytest.fixture
def engine():
    db = MagicMock()
    db.__getitem__.return_value = MagicMock()
    return DeceptionEngine(db, docker_client=None)


def test_generate_environment_beginner(engine):
    profile = make_profile(tier="beginner")
    env = engine.generate_environment(profile)
    assert env.src_ip == "10.0.0.1"
    assert env.attacker_tier == "beginner"
    assert "ssh" in env.services
    assert env.is_active is True
    assert env.env_id is not None


def test_generate_environment_advanced(engine):
    profile = make_profile(tier="advanced_human", score=85.0)
    env = engine.generate_environment(profile)
    assert env.attacker_tier == "advanced_human"
    assert "docker" in env.services or "https" in env.services
    assert env.env_file_content != ""


def test_environment_personalized_by_ttp(engine):
    ttps = [{"tactic": "Lateral Movement", "technique_id": "T1021.004", "technique_name": "SSH", "confidence": 0.9, "matched_command": "ssh"}]
    profile = make_profile(tier="advanced_human", ttps=ttps)
    env = engine.generate_environment(profile)
    assert "redis" in env.services or "jump" in env.hostname


def test_get_active_environments(engine):
    p1 = make_profile(ip="1.1.1.1", tier="beginner")
    p2 = make_profile(ip="2.2.2.2", tier="automated_bot")
    engine.generate_environment(p1)
    engine.generate_environment(p2)
    envs = engine.get_active_environments()
    assert len(envs) == 2


def test_teardown_removes_from_active(engine):
    profile = make_profile()
    env = engine.generate_environment(profile)
    env_id = env.env_id
    engine.teardown(env_id)
    assert engine.get_environment(env_id) is None


def test_engagement_logging(engine):
    profile = make_profile()
    env = engine.generate_environment(profile)
    engine.log_activity(env.env_id, "command_executed", "ls -la")
    updated = engine.get_environment(env.env_id)
    assert len(updated.engagement_log) == 1
    assert updated.engagement_log[0]["action"] == "command_executed"


def test_credentials_generated(engine):
    profile = make_profile()
    env = engine.generate_environment(profile)
    assert len(env.generated_credentials) > 0
    assert "username" in env.generated_credentials[0]
