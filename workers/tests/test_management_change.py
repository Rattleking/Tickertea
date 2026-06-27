"""Tests for the event-driven management_change detector."""
from datetime import datetime, timezone
from uuid import uuid4

from tickertea.common.types import IngestEvent
from tickertea.detect.detectors.management_change import ManagementChangeDetector

DET = ManagementChangeDetector()


def _event(event_type="management_change_disclosure", company_id=..., **payload):
    base = {
        "subject": "Change in Directors/ Key Managerial Personnel (KMP)",
        "description": "Appointment of Mr. X as Chief Technology Officer.",
        "attachment": "https://nsearchives.nseindia.com/corporate/INFY_kmp.pdf",
    }
    base.update(payload)
    return IngestEvent(
        id=uuid4(),
        source_key="nse_announcements",
        company_id=uuid4() if company_id is ... else company_id,
        event_type=event_type,
        occurred_at=datetime(2026, 6, 25, 7, 34, 28, tzinfo=timezone.utc),
        payload=base,
        raw_uri="file:///x",
    )


def test_emits_evidence_backed_candidate():
    [cand] = DET.evaluate(None, _event())
    assert cand.category_slug == "management_change"
    assert cand.direction == "neutral"
    assert len(cand.evidence) == 1
    ev = cand.evidence[0]
    assert ev.evidence_type == "filing"
    assert ev.artifact_uri and ev.excerpt
    assert cand.features["change_type"] == "appointment"
    assert cand.features["is_senior_role"] is True


def test_skips_null_company():
    assert DET.evaluate(None, _event(company_id=None)) == []


def test_skips_unsubscribed_event_type():
    assert DET.evaluate(None, _event(event_type="announcement")) == []


def test_board_meeting_without_personnel_change_skipped():
    ev = _event(
        event_type="board_meeting",
        subject="Board Meeting Intimation",
        description="To consider and approve the dividend.",
    )
    assert DET.evaluate(None, ev) == []


def test_board_meeting_with_appointment_fires():
    ev = _event(
        event_type="board_meeting",
        subject="Board Meeting Outcome",
        description="Board approved appointment of new Managing Director.",
    )
    [cand] = DET.evaluate(None, ev)
    assert cand.features["is_senior_role"] is True


def test_departure_classified_with_lower_magnitude_when_non_senior():
    ev = _event(
        subject="Change in KMP",
        description="Resignation of the Company Secretary.",
    )
    [cand] = DET.evaluate(None, ev)
    assert cand.features["change_type"] == "departure"
    assert cand.features["is_senior_role"] is False
    assert cand.features["magnitude"] == 0.55


def test_no_advice_language_in_output():
    from tickertea.scoring.guardrail import check_text
    [cand] = DET.evaluate(None, _event())
    assert check_text(cand.title, cand.summary).ok
