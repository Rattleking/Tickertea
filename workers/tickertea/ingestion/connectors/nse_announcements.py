"""Connector: NSE corporate announcements (live).

Pulls the National Stock Exchange corporate-announcements feed — the authoritative,
real-time stream of disclosures every listed company is obligated to file (board
meetings, KMP/director changes, capex, fundraising, insider trading windows, …). This
is TickerTea's first real-world event source.

The feed is a public JSON endpoint, but NSE rejects non-browser clients: it requires a
browser User-Agent and a session cookie that is only minted when you first load a page.
So we prime cookies with a homepage GET, then hit the API on the same client.

Connectors do NOT decide what is interesting (that's the detectors' job) — this only
fetches and yields raw rows. Incremental pulls use `seq_id` as the watermark; the
dedupe_key (derived from seq_id by the normalizer) is the real exactly-once guarantee.

Config via env (all optional; defaults to the live latest-equities feed):
  NSE_SYMBOL     — restrict to one company's filings (e.g. INFY). Enables backfill.
  NSE_FROM_DATE  — window start, dd-mm-yyyy (requires NSE_TO_DATE).
  NSE_TO_DATE    — window end, dd-mm-yyyy.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from tickertea.common.types import RawItem
from tickertea.ingestion.base import Cursor

logger = logging.getLogger(__name__)

_HOME_URL = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
_API_URL = "https://www.nseindia.com/api/corporate-announcements"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": _HOME_URL,
}


class NseAnnouncementsConnector:
    source_key = "nse_announcements"

    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout

    def discover(self, cursor: Cursor) -> Iterable[RawItem]:
        last_seen = cursor.state.get("last_external_id")
        rows = self._fetch()
        # NSE returns newest-first. Yield strictly NEW rows oldest-first so the pipeline's
        # watermark (last_external_id) advances to the newest seq_id, and so events are
        # ingested in chronological order.
        fresh = [r for r in rows if self._is_new(r.get("seq_id"), last_seen)]
        fresh.sort(key=lambda r: _seq_sort_key(r.get("seq_id")))
        logger.info(
            "nse_announcements: fetched=%d new=%d (watermark=%s)",
            len(rows), len(fresh), last_seen,
        )
        now = self._now()
        for row in fresh:
            seq_id = str(row.get("seq_id") or "").strip()
            if not seq_id:
                logger.warning("skipping NSE row with no seq_id: %s", row.get("desc"))
                continue
            yield RawItem(external_id=seq_id, fetched_at=now, body=row)

    # --- HTTP -----------------------------------------------------------------------
    def _fetch(self) -> list[dict[str, Any]]:
        params: dict[str, str] = {"index": "equities"}
        if symbol := os.environ.get("NSE_SYMBOL"):
            params["symbol"] = symbol.upper()
        frm, to = os.environ.get("NSE_FROM_DATE"), os.environ.get("NSE_TO_DATE")
        if frm and to:
            params["from_date"], params["to_date"] = frm, to

        with httpx.Client(headers=_HEADERS, timeout=self._timeout, follow_redirects=True) as c:
            c.get(_HOME_URL)  # prime session cookies; NSE 401s the API otherwise
            resp = c.get(_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        # The endpoint returns either a bare list or {"data": [...]}.
        rows = data if isinstance(data, list) else data.get("data", [])
        return [r for r in rows if isinstance(r, dict)]

    @staticmethod
    def _is_new(seq_id: Any, last_seen: str | None) -> bool:
        if last_seen is None:
            return True
        a, b = _seq_sort_key(seq_id), _seq_sort_key(last_seen)
        return a > b

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


def _seq_sort_key(seq_id: Any) -> tuple[int, str]:
    """Order seq_ids numerically when possible, else lexically. The tuple keeps numeric
    ids (the normal case) strictly ordered while still totally ordering any odd values."""
    s = str(seq_id or "").strip()
    return (int(s), "") if s.isdigit() else (-1, s)
