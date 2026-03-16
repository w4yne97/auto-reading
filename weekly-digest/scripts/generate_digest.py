#!/usr/bin/env python3
"""Scan vault for recent papers and daily notes, output digest data as JSON.

Usage:
    python weekly-digest/scripts/generate_digest.py \
        --vault /path/to/vault \
        --output /tmp/auto-reading/digest_data.json \
        [--days 7] [--verbose]
"""

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from lib.vault import parse_date_field, parse_frontmatter

logger = logging.getLogger("generate_digest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate digest data")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    vault_path = Path(args.vault)
    cutoff = date.today() - timedelta(days=args.days)

    papers = []
    papers_dir = vault_path / "20_Papers"
    if papers_dir.exists():
        seen_ids: set[str] = set()
        for md_file in papers_dir.rglob("*.md"):
            try:
                fm = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            except OSError:
                continue
            arxiv_id = fm.get("arxiv_id", "")
            if not arxiv_id or arxiv_id in seen_ids:
                continue
            fetched_date = parse_date_field(fm.get("fetched"))
            if fetched_date and fetched_date >= cutoff:
                seen_ids.add(arxiv_id)
                papers.append(fm)

    papers.sort(key=lambda p: float(p.get("score", 0)), reverse=True)

    daily_notes = []
    daily_dir = vault_path / "10_Daily"
    if daily_dir.exists():
        for md_file in sorted(daily_dir.glob("*.md"), reverse=True):
            if md_file.stem[:10] >= cutoff.isoformat():
                daily_notes.append(md_file.name)

    insight_updates = []
    insights_dir = vault_path / "30_Insights"
    if insights_dir.exists():
        for md_file in insights_dir.rglob("*.md"):
            try:
                fm = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            except OSError:
                continue
            updated_date = parse_date_field(fm.get("updated"))
            if updated_date and updated_date >= cutoff:
                insight_updates.append({
                    "title": fm.get("title", md_file.stem),
                    "type": fm.get("type", "unknown"),
                    "updated": updated_date.isoformat(),
                })

    result = {
        "period": {"from": cutoff.isoformat(), "to": date.today().isoformat()},
        "papers_count": len(papers),
        "top_papers": papers[:5],
        "daily_notes": daily_notes,
        "insight_updates": insight_updates,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    logger.info("Digest data: %d papers, %d daily notes, %d insight updates",
                len(papers), len(daily_notes), len(insight_updates))


if __name__ == "__main__":
    main()
