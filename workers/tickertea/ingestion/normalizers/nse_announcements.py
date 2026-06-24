"""Example normalizer: NSE announcement raw row -> canonical NormalizedEvent."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from tickertea.common.types import CompanyRef, NormalizedEvent, RawItem


class NseAnnouncementsNormalizer:
    source_key = "nse_announcements"

    def normalize(self, item: RawItem, raw_uri: str) -> NormalizedEvent:
        body: dict[str, Any] = item.body if isinstance(item.body, dict) else {}
        symbol = body.get("symbol")
        return NormalizedEvent(
            source_key=self.source_key,
            external_id=item.external_id,
            event_type=self._classify(body.get("subject", "")),
            occurred_at=self._parse_dt(body.get("broadcast_time")),
            company_ref=CompanyRef("nse_symbol", symbol) if symbol else None,
            payload={
                "subject": body.get("subject"),
                "description": body.get("description"),
                "attachment": body.get("attachment"),
            },
            raw_uri=raw_uri,
            dedupe_key=self._dedupe_key(item.external_id),
        )

    def _dedupe_key(self, external_id: str) -> str:
        digest = hashlib.sha256(f"{self.source_key}:{external_id}".encode()).hexdigest()[:24]
        return f"{self.source_key}:{digest}"

    @staticmethod
    def _classify(subject: str) -> str:
        s = subject.lower()
        if "board meeting" in s:
            return "board_meeting"
        if "appointment" in s or "resignation" in s:
            return "management_change_disclosure"
        return "announcement"

    @staticmethod
    def _parse_dt(value: str | None) -> datetime:
        # Replace with the real NSE timestamp format; falls back to a fixed epoch in skeleton.
        return datetime.fromisoformat(value) if value else datetime.fromtimestamp(0)
