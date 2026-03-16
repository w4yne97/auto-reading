#!/usr/bin/env python3
"""Scan papers newer than a given date, output as JSON for Claude.

Usage:
    python insight-update/scripts/scan_recent_papers.py \
        --vault /path/to/vault \
        --since 2026-03-10 \
        --output /tmp/auto-reading/recent_papers.json \
        [--verbose]
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from lib.vault import parse_date_field, parse_frontmatter

logger = logging.getLogger("scan_recent_papers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan recent papers")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--since", required=True, help="ISO date cutoff")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    vault_path = Path(args.vault)
    papers_dir = vault_path / "20_Papers"
    since_date = date.fromisoformat(args.since)

    recent = []
    if papers_dir.exists():
        for md_file in papers_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(content)
            if not fm.get("arxiv_id"):
                continue
            fetched_date = parse_date_field(fm.get("fetched"))
            if fetched_date and fetched_date >= since_date:
                recent.append({
                    "arxiv_id": fm.get("arxiv_id"),
                    "title": fm.get("title", ""),
                    "domain": fm.get("domain", ""),
                    "tags": fm.get("tags", []),
                    "path": str(md_file.relative_to(vault_path)),
                })

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"papers": recent}, ensure_ascii=False, indent=2))
    logger.info("Found %d papers since %s", len(recent), args.since)


if __name__ == "__main__":
    main()
