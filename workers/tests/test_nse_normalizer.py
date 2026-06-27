"""Tests for the NSE announcements normalizer (real NSE row schema)."""
from datetime import timezone

from tickertea.common.types import RawItem
from tickertea.ingestion.normalizers.nse_announcements import NseAnnouncementsNormalizer

NORM = NseAnnouncementsNormalizer()


def _raw(**over):
    row = {
        "symbol": "INFY",
        "sm_isin": "INE009A01021",
        "sm_name": "Infosys Limited",
        "desc": "Change in Directors/ Key Managerial Personnel (KMP)",
        "attchmntText": "Appointment of Mr. X as Chief Technology Officer.",
        "attchmntFile": "https://nsearchives.nseindia.com/corporate/INFY_kmp.pdf",
        "smIndustry": "IT Services",
        "sort_date": "2026-06-25 13:04:28",
        "an_dt": "25-Jun-2026 13:04:28",
        "seq_id": "106674250",
    }
    row.update(over)
    return RawItem(external_id="106674250", fetched_at=None, body=row)  # type: ignore[arg-type]


def test_maps_company_and_subject():
    ev = NORM.normalize(_raw(), "file:///x")
    assert ev.company_ref.scheme == "nse_symbol"
    assert ev.company_ref.value == "INFY"
    assert ev.payload["isin"] == "INE009A01021"
    assert ev.payload["attachment"].endswith(".pdf")
    assert ev.raw_uri == "file:///x"


def test_classifies_management_change():
    assert NORM.normalize(_raw(), "u").event_type == "management_change_disclosure"


def test_classifies_board_meeting_and_generic():
    bm = _raw(desc="Board Meeting Intimation", attchmntText="To consider dividend.")
    assert NORM.normalize(bm, "u").event_type == "board_meeting"
    generic = _raw(desc="Trading Window", attchmntText="Closure of trading window.")
    assert NORM.normalize(generic, "u").event_type == "trading_window"
    other = _raw(desc="Investor Presentation", attchmntText="Q1 deck attached.")
    assert NORM.normalize(other, "u").event_type == "announcement"


def test_isin_fallback_when_no_symbol():
    ev = NORM.normalize(_raw(symbol=""), "u")
    assert ev.company_ref.scheme == "isin" and ev.company_ref.value == "INE009A01021"


def test_unresolvable_company_is_none_not_dropped():
    ev = NORM.normalize(_raw(symbol="", sm_isin=""), "u")
    assert ev.company_ref is None  # event still normalized; never dropped


def test_ist_timestamp_converted_to_utc():
    ev = NORM.normalize(_raw(), "u")
    # 13:04:28 IST -> 07:34:28 UTC
    assert ev.occurred_at.tzinfo == timezone.utc
    assert (ev.occurred_at.hour, ev.occurred_at.minute) == (7, 34)


def test_dedupe_key_is_deterministic():
    a = NORM.normalize(_raw(), "u").dedupe_key
    b = NORM.normalize(_raw(), "u").dedupe_key
    assert a == b and a.startswith("nse_announcements:")
