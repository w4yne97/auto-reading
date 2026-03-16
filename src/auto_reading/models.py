"""Data models for auto-reading."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Paper:
    """Represents a paper or project entry from any source."""

    id: str
    title: str
    authors: list[str]
    abstract: str
    source: str
    source_url: str
    published_at: date
    fetched_at: datetime
    tags: list[str]
    category: str
    status: str
    summary: str | None
    insights: list[str]
    relevance_score: float
