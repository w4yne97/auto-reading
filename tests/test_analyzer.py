"""Tests for Claude-based paper analyzer."""

import json
from unittest.mock import MagicMock

import pytest

from auto_reading.analyzer import Analyzer, AnalysisResult

MOCK_CLAUDE_RESPONSE = {
    "summary": "This paper presents CodeAgent, a novel system...",
    "category": "coding-agent",
    "tags": ["coding-agent", "code-generation", "autonomous"],
    "relevance_score": 0.92,
    "insights": [
        "First to combine planning with execution in coding agents",
        "Achieves 85% pass rate on SWE-bench",
    ],
}


@pytest.fixture
def mock_anthropic():
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps(MOCK_CLAUDE_RESPONSE))
    ]
    mock_client.messages.create = MagicMock(return_value=mock_message)
    return mock_client


@pytest.fixture
def analyzer(mock_anthropic) -> Analyzer:
    return Analyzer(
        client=mock_anthropic,
        model="claude-sonnet-4-6",
        categories=["coding-agent", "tool-use", "llm-reasoning"],
    )


def test_analyze_paper(analyzer: Analyzer, sample_paper):
    result = analyzer.analyze(sample_paper)
    assert result.summary == MOCK_CLAUDE_RESPONSE["summary"]
    assert result.category == "coding-agent"
    assert result.relevance_score == 0.92
    assert len(result.insights) == 2
    assert len(result.tags) == 3


def test_analyze_applies_to_paper(analyzer: Analyzer, sample_paper):
    result = analyzer.analyze(sample_paper)
    updated = result.apply_to(sample_paper)
    assert updated.summary == MOCK_CLAUDE_RESPONSE["summary"]
    assert updated.category == "coding-agent"
    assert updated.relevance_score == 0.92
    assert updated.status == "unread"  # status unchanged


def test_analyze_handles_invalid_json(sample_paper):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="not valid json")]
    mock_client.messages.create = MagicMock(return_value=mock_message)

    analyzer = Analyzer(
        client=mock_client,
        model="claude-sonnet-4-6",
        categories=["coding-agent"],
    )
    with pytest.raises(ValueError, match="Failed to parse"):
        analyzer.analyze(sample_paper)


def test_analyze_handles_api_error(sample_paper):
    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        side_effect=Exception("API Error")
    )
    analyzer = Analyzer(
        client=mock_client,
        model="claude-sonnet-4-6",
        categories=["coding-agent"],
    )
    with pytest.raises(Exception, match="API Error"):
        analyzer.analyze(sample_paper)


def test_analyze_retries_on_transient_error(sample_paper, mock_anthropic):
    """Analyzer retries up to 3 times with backoff on API errors."""
    fail_then_succeed = MagicMock(
        side_effect=[
            Exception("rate limited"),
            Exception("rate limited"),
            mock_anthropic.messages.create.return_value,  # success on 3rd try
        ]
    )
    mock_anthropic.messages.create = fail_then_succeed
    analyzer = Analyzer(
        client=mock_anthropic,
        model="claude-sonnet-4-6",
        categories=["coding-agent"],
    )
    result = analyzer.analyze(sample_paper)
    assert result.summary is not None
    assert fail_then_succeed.call_count == 3


def test_analyze_raises_after_max_retries(sample_paper):
    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        side_effect=Exception("persistent error")
    )
    analyzer = Analyzer(
        client=mock_client,
        model="claude-sonnet-4-6",
        categories=["coding-agent"],
    )
    with pytest.raises(Exception, match="persistent error"):
        analyzer.analyze(sample_paper)
    assert mock_client.messages.create.call_count == 3
