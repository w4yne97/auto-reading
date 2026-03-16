"""Tests for Paper data model."""

from datetime import date, datetime

from auto_reading.models import Paper


def test_paper_creation(sample_paper: Paper):
    assert sample_paper.id == "arxiv:2406.12345"
    assert sample_paper.title == "CodeAgent: Autonomous Coding with LLMs"
    assert sample_paper.source == "alphaarxiv"
    assert sample_paper.status == "unread"


def test_paper_is_immutable(sample_paper: Paper):
    try:
        sample_paper.title = "Modified"  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_paper_with_analysis():
    paper = Paper(
        id="arxiv:2406.99999",
        title="Test Paper",
        authors=["Author"],
        abstract="Abstract text",
        source="alphaarxiv",
        source_url="https://arxiv.org/abs/2406.99999",
        published_at=date(2026, 3, 15),
        fetched_at=datetime(2026, 3, 16, 10, 0, 0),
        tags=["coding-agent"],
        category="coding-agent",
        status="unread",
        summary="This paper presents...",
        insights=["Key insight 1", "Key insight 2"],
        relevance_score=0.85,
    )
    assert paper.summary == "This paper presents..."
    assert len(paper.insights) == 2
    assert paper.relevance_score == 0.85


def test_paper_replace_returns_new_instance(sample_paper: Paper):
    from dataclasses import replace

    updated = replace(sample_paper, status="read", summary="A summary")
    assert updated.status == "read"
    assert updated.summary == "A summary"
    assert sample_paper.status == "unread"  # original unchanged
    assert sample_paper.summary is None
