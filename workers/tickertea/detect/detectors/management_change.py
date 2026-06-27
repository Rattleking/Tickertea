"""Management Change detector: a CXO / board / KMP appointment or exit was disclosed.

Unlike a statistical detector (e.g. hiring_spike, which needs a trailing baseline), this is
event-driven: a single authoritative disclosure IS the observable business change, so it
fires on the first real filing with no history required. It reads the company's own NSE
disclosure and emits an evidence-backed candidate describing the change — never advice.
"""
from __future__ import annotations

from tickertea.common.types import CandidateSignal, EvidenceRef, IngestEvent

# Event types (set by the NSE normalizer) this detector subscribes to.
_SUBSCRIBED = {"management_change_disclosure", "board_meeting"}

# Phrases that confirm an actual personnel change (guards against a board_meeting that is
# only, say, a dividend declaration).
_CHANGE_TERMS = (
    "key managerial personnel", "kmp", "change in directors", "appointment", "appointed",
    "resignation", "resigned", "cessation", "ceased", "managing director", "chief executive",
    "chief financial", "chief technology", "chief operating", "whole-time director",
    "company secretary", "compliance officer", "ceo", "cfo", "cto", "coo",
)
# Senior roles get a higher magnitude (more material business change).
_SENIOR_TERMS = (
    "managing director", "chief executive", "chief financial", "chief technology",
    "chief operating", "whole-time director", "ceo", "cfo", "cto", "coo",
)


class ManagementChangeDetector:
    category_slug = "management_change"
    version = "management_change.v1"

    def evaluate(self, ctx, event: IngestEvent) -> list[CandidateSignal]:
        if event.company_id is None or event.event_type not in _SUBSCRIBED:
            return []

        subject = (event.payload.get("subject") or "").strip()
        description = (event.payload.get("description") or "").strip()
        haystack = f"{subject} {description}".lower()
        if not any(term in haystack for term in _CHANGE_TERMS):
            return []  # subscribed event, but not actually a personnel change

        change_type = self._change_type(haystack)
        is_senior = any(term in haystack for term in _SENIOR_TERMS)
        magnitude = 0.75 if is_senior else 0.55

        excerpt = description or subject
        if len(excerpt) > 500:
            excerpt = excerpt[:497] + "…"

        title = subject or "Management change disclosed"
        if len(title) > 200:
            title = title[:197] + "…"

        return [
            CandidateSignal(
                company_id=event.company_id,
                category_slug=self.category_slug,
                title=title,
                summary=(
                    f"Company disclosed a management change "
                    f"({change_type}) via an NSE corporate announcement"
                    f"{': ' + subject if subject else ''}. Observation only."
                ),
                direction="neutral",  # a personnel change is not inherently up or down
                observed_at=event.occurred_at,
                dedupe_key=f"{self.category_slug}:{event.company_id}:{event.id}",
                evidence=[
                    EvidenceRef(
                        ingest_event_id=event.id,
                        evidence_type="filing",
                        excerpt=excerpt or None,
                        artifact_uri=event.payload.get("attachment"),
                        weight=1.0,
                    )
                ],
                features={
                    "magnitude": magnitude,
                    "change_type": change_type,
                    "is_senior_role": is_senior,
                    "subject": subject,
                },
            )
        ]

    @staticmethod
    def _change_type(haystack: str) -> str:
        if any(t in haystack for t in ("resignation", "resigned", "cessation", "ceased")):
            return "departure"
        if any(t in haystack for t in ("appointment", "appointed")):
            return "appointment"
        return "change"
