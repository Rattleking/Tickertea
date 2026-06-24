"""Ingestion framework contracts: Connector and Normalizer.

Design rule: connectors and normalizers NEVER decide what is interesting. They only
fetch and shape data. Deciding what is a signal is the detectors' job. This keeps
ingestion dumb, replayable, and reusable across many signal categories.
See docs/architecture/03-ingestion-framework.md.
"""
from __future__ import annotations

from typing import Any, Iterable, Protocol

from tickertea.common.types import NormalizedEvent, RawItem


class Cursor:
    """A jsonb watermark for incremental pulls (mirrors ingest_run.cursor)."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = state or {}


class Connector(Protocol):
    """Knows how to talk to ONE source. Pure I/O, no business logic."""

    source_key: str

    def discover(self, cursor: Cursor) -> Iterable[RawItem]:
        """Yield raw items since the cursor watermark. Must be idempotent."""
        ...


class Normalizer(Protocol):
    """Maps a source-specific RawItem into the canonical NormalizedEvent."""

    source_key: str

    def normalize(self, item: RawItem, raw_uri: str) -> NormalizedEvent:
        """Map raw → canonical. Resolve company_ref where possible; None if unknown
        (the event is still persisted with company_id NULL — never dropped)."""
        ...
