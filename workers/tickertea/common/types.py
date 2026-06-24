"""Shared dataclasses used across ingestion, detection, and scoring.

The database schema (db/migrations) is the canonical contract; these mirror it for the
write path. Keep field names aligned with the SQL columns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

Direction = Literal["up", "down", "neutral"]  # describes an OBSERVATION, never advice


@dataclass(frozen=True)
class CompanyRef:
    """A pointer into company_identifier (scheme, value) → resolved to company_id."""

    scheme: str  # nse_symbol | bse_code | isin | mca_cin | diffbot_id | lei
    value: str


@dataclass
class RawItem:
    """Exactly what a connector pulled from a source, before any interpretation."""

    external_id: str
    fetched_at: datetime
    body: bytes | str | dict[str, Any]
    content_type: str = "application/json"


@dataclass
class NormalizedEvent:
    """Canonical, source-agnostic event → one ingest_event row."""

    source_key: str
    external_id: str
    event_type: str
    occurred_at: datetime
    company_ref: CompanyRef | None
    payload: dict[str, Any]
    raw_uri: str
    dedupe_key: str


@dataclass
class IngestEvent:
    """A persisted ingest_event row, as handed to detectors."""

    id: UUID
    source_key: str
    company_id: UUID | None
    event_type: str
    occurred_at: datetime | None
    payload: dict[str, Any]
    raw_uri: str


@dataclass(frozen=True)
class EvidenceRef:
    """Links a candidate signal back to a source event (traceability invariant)."""

    ingest_event_id: UUID
    evidence_type: str  # filing | news | job_posting | price_series | mca_record | ...
    excerpt: str | None = None
    artifact_uri: str | None = None
    weight: float = 1.0


@dataclass
class CandidateSignal:
    """A detector's output. MUST carry >= 1 evidence ref (enforced by the engine)."""

    company_id: UUID
    category_slug: str
    title: str
    summary: str
    direction: Direction
    observed_at: datetime
    dedupe_key: str
    evidence: list[EvidenceRef]
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class Score:
    """Descriptive intensities in [0,1]. NOT expected return / price target."""

    magnitude: float
    confidence: float
    novelty: float
    composite: float
    model_version: str
    features: dict[str, Any] = field(default_factory=dict)
