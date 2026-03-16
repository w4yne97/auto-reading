"""AlphaRxiv paper fetcher via web scraping."""

import logging
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from auto_reading.fetchers.base import BaseFetcher
from auto_reading.models import Paper

logger = logging.getLogger(__name__)

ALPHAARXIV_URL = "https://alphaarxiv.org/"


class AlphaRxivFetcher(BaseFetcher):
    """Fetches trending papers from AlphaRxiv via HTML scraping."""

    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(ALPHAARXIV_URL, timeout=30.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("AlphaRxiv fetch failed: %s", e)
            return []

        return self._parse_papers(response.text, topics)

    def _parse_papers(self, html: str, topics: list[str]) -> list[Paper]:
        soup = BeautifulSoup(html, "html.parser")
        papers: list[Paper] = []

        for card in soup.select(".paper-card"):
            try:
                paper = self._parse_card(card)
                if paper is not None:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse paper card: %s", e)
                continue

        return papers

    def _parse_card(self, card) -> Paper | None:
        arxiv_id = card.get("data-arxiv-id")
        if not arxiv_id:
            return None

        title_el = card.select_one(".paper-title a")
        title = title_el.get_text(strip=True) if title_el else "Unknown"
        url = (
            title_el["href"]
            if title_el and title_el.has_attr("href")
            else f"https://arxiv.org/abs/{arxiv_id}"
        )

        authors_el = card.select_one(".paper-authors")
        authors_text = authors_el.get_text(strip=True) if authors_el else ""
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]

        abstract_el = card.select_one(".paper-abstract")
        abstract = abstract_el.get_text(strip=True) if abstract_el else ""

        date_el = card.select_one(".paper-date")
        published_at = (
            date.fromisoformat(date_el.get_text(strip=True))
            if date_el
            else date.today()
        )

        return Paper(
            id=f"arxiv:{arxiv_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            source="alphaarxiv",
            source_url=url,
            published_at=published_at,
            fetched_at=datetime.now(),
            tags=[],
            category="other",
            status="unread",
            summary=None,
            insights=[],
            relevance_score=0.0,
        )
