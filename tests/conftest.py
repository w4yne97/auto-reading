"""Shared test fixtures."""

from datetime import date, datetime

import pytest

from auto_reading.models import Paper


@pytest.fixture
def sample_paper() -> Paper:
    return Paper(
        id="arxiv:2406.12345",
        title="CodeAgent: Autonomous Coding with LLMs",
        authors=["Alice Smith", "Bob Jones"],
        abstract="We present CodeAgent, a system for autonomous code generation...",
        source="alphaarxiv",
        source_url="https://arxiv.org/abs/2406.12345",
        published_at=date(2026, 3, 15),
        fetched_at=datetime(2026, 3, 16, 10, 0, 0),
        tags=["coding-agent", "code-generation"],
        category="coding-agent",
        status="unread",
        summary=None,
        insights=[],
        relevance_score=0.0,
    )
