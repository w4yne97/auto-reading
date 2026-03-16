"""Tests for SQLite database operations."""

from dataclasses import replace
from datetime import date, datetime

import pytest

from auto_reading.db import PaperDB
from auto_reading.models import Paper


@pytest.fixture
def db(tmp_path) -> PaperDB:
    return PaperDB(tmp_path / "test.db")


def test_init_creates_schema(db: PaperDB):
    """DB init creates the papers table and indexes."""
    import sqlite3

    conn = sqlite3.connect(db.db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_and_get(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    result = db.get(sample_paper.id)
    assert result is not None
    assert result.id == sample_paper.id
    assert result.title == sample_paper.title
    assert result.authors == sample_paper.authors
    assert result.tags == sample_paper.tags


def test_insert_duplicate_skips(db: PaperDB, sample_paper: Paper):
    inserted_1 = db.insert(sample_paper)
    inserted_2 = db.insert(sample_paper)
    assert inserted_1 is True
    assert inserted_2 is False


def test_list_by_status(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    analyzed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        status="read",
        summary="Done",
    )
    db.insert(analyzed)
    unread = db.list_by_status("unread")
    assert len(unread) == 1
    assert unread[0].id == "arxiv:2406.12345"


def test_list_unprocessed(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    processed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        summary="Has summary",
    )
    db.insert(processed)
    unprocessed = db.list_unprocessed()
    assert len(unprocessed) == 1
    assert unprocessed[0].id == sample_paper.id


def test_update(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    updated = replace(
        sample_paper,
        status="read",
        summary="A great summary",
        tags=["coding-agent", "new-tag"],
        relevance_score=0.95,
    )
    db.update(updated)
    result = db.get(sample_paper.id)
    assert result is not None
    assert result.status == "read"
    assert result.summary == "A great summary"
    assert "new-tag" in result.tags
    assert result.relevance_score == 0.95


def test_exists(db: PaperDB, sample_paper: Paper):
    assert db.exists(sample_paper.id) is False
    db.insert(sample_paper)
    assert db.exists(sample_paper.id) is True


def test_list_analyzed(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)  # no summary
    analyzed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        summary="Has summary",
    )
    db.insert(analyzed)
    results = db.list_analyzed()
    assert len(results) == 1
    assert results[0].id == "arxiv:2406.99999"


def test_list_by_category(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    other = replace(sample_paper, id="arxiv:2406.99999", category="tool-use")
    db.insert(other)
    results = db.list_by_category("coding-agent")
    assert len(results) == 1
    assert results[0].id == sample_paper.id
