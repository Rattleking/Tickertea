"""Maps source_key -> (Connector, Normalizer). Register new sources here."""
from __future__ import annotations

from tickertea.ingestion.base import Connector, Normalizer
from tickertea.ingestion.connectors.nse_announcements import NseAnnouncementsConnector
from tickertea.ingestion.normalizers.nse_announcements import NseAnnouncementsNormalizer

_CONNECTORS: dict[str, Connector] = {}
_NORMALIZERS: dict[str, Normalizer] = {}


def register(connector: Connector, normalizer: Normalizer) -> None:
    assert connector.source_key == normalizer.source_key
    _CONNECTORS[connector.source_key] = connector
    _NORMALIZERS[normalizer.source_key] = normalizer


def get_connector(source_key: str) -> Connector:
    return _CONNECTORS[source_key]


def get_normalizer(source_key: str) -> Normalizer:
    return _NORMALIZERS[source_key]


def registered_sources() -> list[str]:
    return sorted(_CONNECTORS)


# --- Built-in registrations ---------------------------------------------------------
register(NseAnnouncementsConnector(), NseAnnouncementsNormalizer())
# TODO: bse_announcements, mca_filings, diffbot_news, diffbot_org, linkedin_jobs, news_rss
