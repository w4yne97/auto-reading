"""CLI entry point for auto-reading."""

import asyncio
import logging
from pathlib import Path

import typer

from auto_reading import __version__
from auto_reading.config import load_config

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="auto-reading",
    help="LLM-driven paper tracking system for AI research.",
)

CONFIG_OPTION = typer.Option(
    "config.yaml", "--config", "-c", help="Path to config file"
)
VERBOSE_OPTION = typer.Option(
    False, "--verbose", "-v", help="Enable debug logging"
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def version_callback(value: bool):
    if value:
        typer.echo(f"auto-reading {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=version_callback, is_eager=True
    ),
):
    """Auto-Reading: LLM-driven paper tracking for AI research."""


@app.command()
def fetch(
    source: str = typer.Argument(
        help="Source to fetch from: alphaarxiv, github"
    ),
    topic: str = typer.Option(
        None, "--topic", "-t", help="Topic to search for"
    ),
    days: int = typer.Option(
        None, "--days", "-d", help="Days to look back"
    ),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Fetch papers from a source."""
    _setup_logging(verbose)
    cfg = load_config(config)
    days = days or cfg.fetch.default_days

    from auto_reading.db import PaperDB

    db = PaperDB(config.parent / "auto-reading.db")

    async def _fetch():
        papers = []
        if source == "alphaarxiv":
            from auto_reading.fetchers.alphaarxiv import AlphaRxivFetcher

            fetcher = AlphaRxivFetcher()
            topics = [topic] if topic else cfg.sources.alphaarxiv.topics
            papers = await fetcher.fetch(topics=topics, days=days)
        elif source == "github":
            from auto_reading.fetchers.github import GitHubFetcher

            fetcher = GitHubFetcher(
                tracked_repos=cfg.sources.github.tracked_repos,
            )
            topics = [topic] if topic else cfg.sources.github.topics
            papers = await fetcher.fetch(topics=topics, days=days)
        else:
            typer.echo(f"Unknown source: {source}", err=True)
            raise typer.Exit(1)

        new_count = 0
        for paper in papers[: cfg.fetch.max_papers_per_run]:
            if db.insert(paper):
                new_count += 1

        typer.echo(
            f"Fetched {len(papers)} papers, {new_count} new, "
            f"{len(papers) - new_count} duplicates skipped."
        )

    asyncio.run(_fetch())
    db.close()


@app.command()
def analyze(
    unprocessed: bool = typer.Option(
        False, "--unprocessed", help="Analyze all unprocessed papers"
    ),
    paper_id: str = typer.Option(
        None, "--paper", help="Analyze a specific paper by ID"
    ),
    retry_errors: bool = typer.Option(
        False, "--retry-errors", help="Retry papers with error status"
    ),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Analyze papers with Claude."""
    _setup_logging(verbose)
    cfg = load_config(config)

    import anthropic

    from auto_reading.analyzer import Analyzer
    from auto_reading.db import PaperDB

    db = PaperDB(config.parent / "auto-reading.db")
    client = anthropic.Anthropic()
    analyzer = Analyzer(
        client=client, model=cfg.claude.model, categories=cfg.categories
    )

    if paper_id:
        papers = [p for p in [db.get(paper_id)] if p is not None]
    elif retry_errors:
        papers = db.list_by_status("error")
    elif unprocessed:
        papers = db.list_unprocessed()
    else:
        typer.echo(
            "Specify --unprocessed, --paper <id>, or --retry-errors",
            err=True,
        )
        raise typer.Exit(1)

    success = 0
    errors = 0
    for paper in papers:
        try:
            from dataclasses import replace as dc_replace

            result = analyzer.analyze(paper)
            updated = result.apply_to(paper)
            db.update(updated)
            success += 1
            typer.echo(
                f"  Analyzed: {paper.title[:60]}... → {result.category}"
            )
        except Exception as e:
            errors += 1
            logger.error("Failed to analyze %s: %s", paper.id, e)
            db.update(dc_replace(paper, status="error"))

    typer.echo(f"Done: {success} analyzed, {errors} errors.")
    db.close()


@app.command()
def sync(
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing notes"
    ),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Sync analyzed papers to Obsidian vault."""
    _setup_logging(verbose)
    cfg = load_config(config)

    from auto_reading.db import PaperDB
    from auto_reading.writer import ObsidianWriter

    db = PaperDB(config.parent / "auto-reading.db")
    writer = ObsidianWriter(
        vault_path=cfg.obsidian.vault_path, categories=cfg.categories
    )
    writer.init_vault()

    papers = db.list_analyzed()

    written = 0
    skipped = 0
    for paper in papers:
        path = writer.write_paper(paper, force=force)
        if path:
            written += 1
        else:
            skipped += 1

    typer.echo(f"Synced: {written} written, {skipped} skipped.")
    db.close()


@app.command()
def run(
    source: str = typer.Argument(
        help="Source to fetch from: alphaarxiv, github"
    ),
    topic: str = typer.Option(
        None, "--topic", "-t", help="Topic to search for"
    ),
    days: int = typer.Option(
        None, "--days", "-d", help="Days to look back"
    ),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """All-in-one: fetch -> analyze -> sync."""
    _setup_logging(verbose)
    fetch(
        source=source,
        topic=topic,
        days=days,
        config=config,
        verbose=verbose,
    )
    analyze(
        unprocessed=True,
        paper_id=None,
        retry_errors=False,
        config=config,
        verbose=verbose,
    )
    sync(force=False, config=config, verbose=verbose)
