"""Tickertea worker CLI.

    tickertea ingest --source nse_announcements
    tickertea detect --once
    tickertea score  --once
    tickertea analog --signal <uuid>

Wiring to Postgres/Redis/S3 lives behind these commands; the skeleton shows the stage
boundaries so each can scale independently. See docs/architecture/01 + 03 + 04 + 05.
"""
from __future__ import annotations

import typer

from tickertea.detect.registry import all_detectors
from tickertea.ingestion.registry import registered_sources

app = typer.Typer(help="Tickertea ingestion / detection / scoring / analog workers")


@app.command()
def ingest(source: str = typer.Option(..., help="source_key, e.g. nse_announcements")) -> None:
    """Run a connector: pull -> raw to S3 -> normalize -> ingest_event -> enqueue."""
    if source not in registered_sources():
        raise typer.BadParameter(f"unknown source '{source}'. known: {registered_sources()}")
    typer.echo(f"[ingest] would run connector+normalizer for '{source}' (skeleton)")


@app.command()
def detect(once: bool = typer.Option(False, help="process the queue once and exit")) -> None:
    """Consume ingest events; run detectors; write candidate signals + evidence."""
    slugs = [d.category_slug for d in all_detectors()]
    typer.echo(f"[detect] {'one pass' if once else 'loop'} over detectors: {slugs} (skeleton)")


@app.command()
def score(once: bool = typer.Option(False, help="score pending candidates once and exit")) -> None:
    """Score candidate signals; apply guardrail; publish or suppress."""
    typer.echo(f"[score] {'one pass' if once else 'loop'} (skeleton)")


@app.command()
def analog(signal: str = typer.Option(..., help="seed signal id")) -> None:
    """Run a historical-analog search for a seed signal."""
    typer.echo(f"[analog] would search analogs for signal {signal} (skeleton)")


if __name__ == "__main__":
    app()
