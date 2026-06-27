"""Normalizer: NSE announcement raw row -> canonical NormalizedEvent.

Maps the live NSE corporate-announcements schema (symbol, sm_isin, desc, attchmntText,
attchmntFile, sort_date/an_dt, seq_id) onto a source-agnostic NormalizedEvent. It assigns
a coarse event_type from the disclosure subject so detectors can subscribe by type, but it
does NOT decide significance — that's the detectors' job.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from tickertea.common.types import CompanyRef, NormalizedEvent, RawItem

# NSE publishes timestamps in IST (Asia/Kolkata, fixed UTC+5:30, no DST).
_IST = timezone(timedelta(hours=5, minutes=30))

# Subject keywords -> event_type. Checked in priority order against desc + attachment text.
_KMP_KEYWORDS = (
    "key managerial personnel", "kmp", "change in directors", "appointment",
    "resignation", "cessation", "managing director", "chief executive",
    "chief financial", "chief technology", "chief operating", "whole-time director",
    "company secretary", "compliance officer", " ceo", " cfo", " cto", " coo",
)


class NseAnnouncementsNormalizer:
    source_key = "nse_announcements"

    def normalize(self, item: RawItem, raw_uri: str) -> NormalizedEvent:
        body: dict[str, Any] = item.body if isinstance(item.body, dict) else {}
        subject = (body.get("desc") or "").strip()
        text = (body.get("attchmntText") or "").strip()

        return NormalizedEvent(
            source_key=self.source_key,
            external_id=item.external_id,
            event_type=self._classify(subject, text),
            occurred_at=self._occurred_at(body),
            company_ref=self._company_ref(body),
            payload={
                "subject": subject,
                "description": text,
                "attachment": body.get("attchmntFile"),
                "symbol": body.get("symbol"),
                "isin": body.get("sm_isin"),
                "company_name": body.get("sm_name"),
                "industry": body.get("smIndustry"),
                "announced_at": body.get("an_dt"),
            },
            raw_uri=raw_uri,
            dedupe_key=self._dedupe_key(item.external_id),
        )

    # --- helpers --------------------------------------------------------------------
    @staticmethod
    def _company_ref(body: dict[str, Any]) -> CompanyRef | None:
        if symbol := (body.get("symbol") or "").strip():
            return CompanyRef("nse_symbol", symbol)
        if isin := (body.get("sm_isin") or "").strip():
            return CompanyRef("isin", isin)
        return None  # unresolved events are still persisted (company_id NULL), never dropped

    def _dedupe_key(self, external_id: str) -> str:
        digest = hashlib.sha256(f"{self.source_key}:{external_id}".encode()).hexdigest()[:24]
        return f"{self.source_key}:{digest}"

    @staticmethod
    def _classify(subject: str, text: str) -> str:
        haystack = f" {subject} {text} ".lower()
        if any(k in haystack for k in _KMP_KEYWORDS):
            return "management_change_disclosure"
        if "board meeting" in haystack:
            return "board_meeting"
        if "trading window" in haystack:
            return "trading_window"
        return "announcement"

    @classmethod
    def _occurred_at(cls, body: dict[str, Any]) -> datetime:
        """Parse the disclosure time (IST) into a UTC datetime.

        Prefer `sort_date` ('2026-06-25 13:04:28'); fall back to `an_dt`
        ('25-Jun-2026 13:04:28'). Returns the current UTC time if neither parses, so an
        event is never dropped for a malformed timestamp.
        """
        for value, fmt in ((body.get("sort_date"), "%Y-%m-%d %H:%M:%S"),
                           (body.get("an_dt"), "%d-%b-%Y %H:%M:%S")):
            if not value:
                continue
            try:
                naive = datetime.strptime(str(value).strip(), fmt)
                return naive.replace(tzinfo=_IST).astimezone(timezone.utc)
            except ValueError:
                continue
        return datetime.now(timezone.utc)
