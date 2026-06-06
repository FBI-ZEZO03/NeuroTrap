"""Tests for the fake credential generator."""

import pytest
from src.deception.credential_generator import CredentialGenerator


@pytest.fixture
def gen():
    return CredentialGenerator(seed=42)


def test_generate_ssh_users(gen):
    users = gen.generate_ssh_users(count=5)
    assert len(users) == 5
    for u in users:
        assert "username" in u
        assert "password" in u
        assert "shadow_hash" in u
        assert u["shadow_hash"].startswith("$6$")


def test_generate_aws_credentials(gen):
    creds = gen.generate_aws_credentials()
    assert creds["AWS_ACCESS_KEY_ID"].startswith("AKIA")
    assert len(creds["AWS_ACCESS_KEY_ID"]) == 20
    assert "AWS_SECRET_ACCESS_KEY" in creds


def test_generate_env_file_beginner(gen):
    env = gen.generate_env_file(tier="beginner")
    assert "APP_ENV=staging" in env
    assert "SECRET_KEY=" in env
    assert "AWS_ACCESS_KEY_ID" not in env


def test_generate_env_file_advanced(gen):
    env = gen.generate_env_file(tier="advanced_human")
    assert "AWS_ACCESS_KEY_ID" in env
    assert "AWS_SECRET_ACCESS_KEY" in env


def test_generate_fake_shadow(gen):
    shadow = gen.generate_fake_shadow(user_count=5)
    lines = [l for l in shadow.split("\n") if l]
    assert len(lines) >= 5
    assert any("root" in l for l in lines)


def test_generate_history_file(gen):
    history = gen.generate_history_file(tier="beginner")
    lines = [l for l in history.split("\n") if l]
    assert len(lines) > 0


def test_seeded_reproducible():
    g1 = CredentialGenerator(seed=99)
    g2 = CredentialGenerator(seed=99)
    creds1 = g1.generate_aws_credentials()
    creds2 = g2.generate_aws_credentials()
    assert creds1["AWS_ACCESS_KEY_ID"] == creds2["AWS_ACCESS_KEY_ID"]
