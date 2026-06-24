"""Tests for the scoring engine invariants."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tickertea.common.types import CandidateSignal, EvidenceRef
from tickertea.scoring.engine import ScoringConfig, ScoringEngine


def _candidate(title="Open roles up 3.2σ vs trailing mean", summary="Observation only.", z=3.2):
    return CandidateSignal(
        company_id=uuid4(),
        category_slug="hiring_spike",
        title=title,
        summary=summary,
        direction="up",
        observed_at=datetime.now(timezone.utc),
        dedupe_key="hiring_spike:test",
        evidence=[EvidenceRef(ingest_event_id=uuid4(), evidence_type="job_posting")],
        features={"zscore": z},
    )


def test_score_in_unit_range():
    res = ScoringEngine().score(_candidate(), ScoringConfig())
    s = res.score
    for v in (s.magnitude, s.confidence, s.novelty, s.composite):
        assert 0.0 <= v <= 1.0


def test_no_evidence_rejected():
    c = _candidate()
    c.evidence = []
    with pytest.raises(ValueError):
        ScoringEngine().score(c, ScoringConfig())


def test_advice_language_suppressed_not_published():
    c = _candidate(title="Strong buy: target price 4200")
    res = ScoringEngine().score(c, ScoringConfig())
    assert res.publish is False
    assert res.suppressed_reason and res.suppressed_reason.startswith("advice_language")


def test_publish_threshold():
    # A large z-score with corroborating evidence should clear the default threshold.
    c = _candidate(z=4.5)
    c.evidence = [
        EvidenceRef(ingest_event_id=uuid4(), evidence_type="job_posting"),
        EvidenceRef(ingest_event_id=uuid4(), evidence_type="news"),
    ]
    res = ScoringEngine().score(c, ScoringConfig())
    assert res.publish is True
