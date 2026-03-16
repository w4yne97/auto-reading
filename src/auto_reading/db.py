"""SQLite database operations for paper storage."""

import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from auto_reading.models import Paper

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    abstract TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    summary TEXT,
    insights TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL
);

CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(category);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_at);
"""


def _paper_to_row(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": json.dumps(paper.authors),
        "abstract": paper.abstract,
        "source": paper.source,
        "source_url": paper.source_url,
        "published_at": paper.published_at.isoformat(),
        "fetched_at": paper.fetched_at.isoformat(),
        "tags": json.dumps(paper.tags),
        "category": paper.category,
        "status": paper.status,
        "summary": paper.summary,
        "insights": json.dumps(paper.insights),
        "relevance_score": paper.relevance_score,
    }


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        abstract=row["abstract"],
        source=row["source"],
        source_url=row["source_url"],
        published_at=date.fromisoformat(row["published_at"]),
        fetched_at=datetime.fromisoformat(row["fetched_at"]),
        tags=json.loads(row["tags"]),
        category=row["category"],
        status=row["status"],
        summary=row["summary"],
        insights=json.loads(row["insights"]),
        relevance_score=row["relevance_score"],
    )


class PaperDB:
    """SQLite-backed paper storage with deduplication."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def insert(self, paper: Paper) -> bool:
        """Insert a paper. Returns True if inserted, False if duplicate."""
        try:
            row = _paper_to_row(paper)
            self._conn.execute(
                """INSERT INTO papers (id, title, authors, abstract, source,
                   source_url, published_at, fetched_at, tags, category,
                   status, summary, insights, relevance_score)
                   VALUES (:id, :title, :authors, :abstract, :source,
                   :source_url, :published_at, :fetched_at, :tags, :category,
                   :status, :summary, :insights, :relevance_score)""",
                row,
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get(self, paper_id: str) -> Paper | None:
        """Get a paper by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        )
        row = cursor.fetchone()
        return _row_to_paper(row) if row else None

    def exists(self, paper_id: str) -> bool:
        """Check if a paper exists in the database."""
        cursor = self._conn.execute(
            "SELECT 1 FROM papers WHERE id = ?", (paper_id,)
        )
        return cursor.fetchone() is not None

    def update(self, paper: Paper) -> None:
        """Update an existing paper."""
        row = _paper_to_row(paper)
        self._conn.execute(
            """UPDATE papers SET title=:title, authors=:authors,
               abstract=:abstract, source=:source, source_url=:source_url,
               published_at=:published_at, fetched_at=:fetched_at,
               tags=:tags, category=:category, status=:status,
               summary=:summary, insights=:insights,
               relevance_score=:relevance_score
               WHERE id=:id""",
            row,
        )
        self._conn.commit()

    def list_by_status(self, status: str) -> list[Paper]:
        """List papers by status."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE status = ? ORDER BY published_at DESC",
            (status,),
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_unprocessed(self) -> list[Paper]:
        """List papers that haven't been analyzed yet (no summary)."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE summary IS NULL ORDER BY fetched_at ASC"
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_by_category(self, category: str) -> list[Paper]:
        """List papers by category."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE category = ? ORDER BY published_at DESC",
            (category,),
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_analyzed(self) -> list[Paper]:
        """List all papers that have been analyzed (have a summary)."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE summary IS NOT NULL ORDER BY published_at DESC"
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
