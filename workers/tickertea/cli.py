"""Tickertea worker CLI.

    tickertea ingest --source nse_announcements
    tickertea detect --once
    tickertea score  --once
    tickertea analog --signal <uuid>

Each command drives a stage of the write path (see tickertea/pipeline.py and
docs/architecture/01 + 03 + 04 + 05). Connections/credentials come from .env.local via
tickertea.common.settings.
"""
from __future__ import annotations

import typer

from tickertea import pipeline
from tickertea.detect.registry import all_detectors
from tickertea.ingestion.registry import registered_sources

app = typer.Typer(help="Tickertea ingestion / detection / scoring / analog workers")


@app.command()
def ingest(source: str = typer.Option(..., help="source_key, e.g. nse_announcements")) -> None:
    """Run a connector: pull -> raw to S3 -> normalize -> ingest_event."""
    if source not in registered_sources():
        raise typer.BadParameter(f"unknown source '{source}'. known: {registered_sources()}")
    s = pipeline.run_ingest(source)
    typer.echo(
        f"[ingest] {source}: fetched={s.fetched} new_events={s.inserted} run={s.run_id}"
    )


@app.command()
def detect(
    once: bool = typer.Option(True, help="process the queue once and exit"),
    limit: int = typer.Option(500, help="max events per pass"),
) -> None:
    """Consume ingest events; run detectors; score; write signals + evidence + score."""
    if not once:
        raise typer.BadParameter("continuous mode not implemented yet; use --once")
    slugs = [d.category_slug for d in all_detectors()]
    typer.echo(f"[detect] detectors: {slugs}")
    s = pipeline.run_detect(limit=limit)
    typer.echo(
        f"[detect] events={s.events_processed} failed={s.events_failed} "
        f"signals={s.signals_total} published={s.signals_published}"
    )


@app.command()
def score(once: bool = typer.Option(True, help="run one repair pass and exit")) -> None:
    """Maintenance: recompute the current score for any signal missing one."""
    if not once:
        raise typer.BadParameter("continuous mode not implemented yet; use --once")
    n = pipeline.run_rescore()
    typer.echo(f"[score] rescored {n} signal(s)")


@app.command()
def analog(signal: str = typer.Option(..., help="seed signal id")) -> None:
    """Run a historical-analog search for a seed signal."""
    typer.echo(f"[analog] would search analogs for signal {signal} (skeleton)")


if __name__ == "__main__":
    app()
