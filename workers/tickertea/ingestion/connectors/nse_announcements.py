"""Example connector: NSE corporate announcements.

Skeleton — the discover() body shows the shape (paged pull, cursor watermark) without a
live HTTP integration. Replace the stubbed fetch with a real httpx call to the NSE feed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from tickertea.common.types import RawItem
from tickertea.ingestion.base import Cursor


class NseAnnouncementsConnector:
    source_key = "nse_announcements"

    def discover(self, cursor: Cursor) -> Iterable[RawItem]:
        # last_seen = cursor.state.get("last_external_id")
        # resp = httpx.get(NSE_ANNOUNCEMENTS_URL, params={...})
        # for row in resp.json()["rows"]:
        #     if row["id"] == last_seen: break
        #     yield RawItem(external_id=row["id"], fetched_at=now, body=row)
        #
        # The caller persists each RawItem to S3, then calls the normalizer, then
        # inserts ingest_event ON CONFLICT (dedupe_key) DO NOTHING, then advances the
        # cursor to the newest external_id. Nothing is dropped on failure.
        _ = cursor
        return iter(())  # skeleton: no live items yet

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
