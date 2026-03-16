"""alphaXiv scraper: extract trending papers from SSR-embedded JSON."""

import json
import logging
from datetime import date, datetime

import requests

from lib.models import Paper

logger = logging.getLogger(__name__)

ALPHAXIV_URL = "https://alphaxiv.org/explore"
_TSR_MARKER = "self.$_TSR="
_REQUEST_TIMEOUT = 10


class AlphaXivError(Exception):
    """Raised when alphaXiv scraping fails."""


def _extract_tsr_json(html: str) -> dict:
    """Extract $_TSR JSON from HTML using json.JSONDecoder.raw_decode.

    This is more robust than regex for deeply nested JSON.
    """
    idx = html.find(_TSR_MARKER)
    if idx == -1:
        raise AlphaXivError("Could not find $_TSR in alphaXiv HTML")
    idx += len(_TSR_MARKER)
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(html, idx)
    except json.JSONDecodeError as e:
        raise AlphaXivError(f"Failed to parse $_TSR JSON: {e}") from e
    return data


def parse_ssr_json(html: str) -> list[Paper]:
    """Extract papers from alphaXiv SSR-embedded JSON in HTML."""
    data = _extract_tsr_json(html)

    papers = []
    for page in data.get("pages", []):
        for item in page.get("papers", []):
            paper_id = item.get("universal_paper_id", "")
            if not paper_id:
                continue

            authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            summary = item.get("paper_summary", {})
            abstract = summary.get("abstract", "") if isinstance(summary, dict) else ""
            visits = item.get("visits_count", {})
            visit_count = visits.get("all", 0) if isinstance(visits, dict) else 0

            try:
                pub_str = item.get("publication_date", "")
                pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                pub_date = date.today()

            topics = [t for t in item.get("topics", []) if t.startswith("cs.")]

            papers.append(
                Paper(
                    arxiv_id=paper_id,
                    title=item.get("title", ""),
                    authors=authors,
                    abstract=abstract,
                    source="alphaxiv",
                    url=f"https://arxiv.org/abs/{paper_id}",
                    published=pub_date,
                    categories=topics,
                    alphaxiv_votes=item.get("total_votes"),
                    alphaxiv_visits=visit_count,
                )
            )

    return papers


def fetch_trending(max_pages: int = 3) -> list[Paper]:
    """Fetch trending papers from alphaXiv.

    For MVP, fetches only the first page (~20 papers). Pagination requires
    cursor extraction from SSR state which may change with frontend updates.
    Raises AlphaXivError on failure (caller should handle fallback).
    """
    params = {"sort": "Hot", "categories": "computer-science"}

    try:
        resp = requests.get(ALPHAXIV_URL, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise AlphaXivError(f"Failed to fetch alphaXiv: {e}") from e

    papers = parse_ssr_json(resp.text)
    logger.info("Fetched %d papers from alphaXiv", len(papers))
    return papers
