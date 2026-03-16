"""Tests for CLI commands."""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from auto_reading.cli import app

runner = CliRunner()


@pytest.fixture
def config_file(tmp_path):
    vault = tmp_path / "vault"
    config = {
        "obsidian": {"vault_path": str(vault)},
        "categories": ["coding-agent"],
        "sources": {
            "alphaarxiv": {"enabled": True, "topics": ["coding agent"]},
            "github": {
                "enabled": True,
                "topics": ["coding-agent"],
                "tracked_repos": ["paul-gauthier/aider"],
            },
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "auto-reading" in result.output.lower() or "Usage" in result.output


def test_cli_fetch_requires_source(config_file):
    result = runner.invoke(app, ["fetch", "--config", str(config_file)])
    assert result.exit_code != 0 or "source" in result.output.lower()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_analyze_requires_flag(config_file):
    result = runner.invoke(app, ["analyze", "--config", str(config_file)])
    assert result.exit_code != 0 or "specify" in result.output.lower()


def test_cli_analyze_retry_errors(config_file, tmp_path):
    """--retry-errors selects papers with error status."""
    from dataclasses import replace as dc_replace

    from auto_reading.db import PaperDB
    from auto_reading.models import Paper

    db = PaperDB(config_file.parent / "auto-reading.db")
    error_paper = Paper(
        id="arxiv:0000.00001",
        title="Error Paper",
        authors=["A"],
        abstract="Abstract",
        source="alphaarxiv",
        source_url="https://arxiv.org/abs/0000.00001",
        published_at=date(2026, 3, 15),
        fetched_at=datetime(2026, 3, 16),
        tags=[],
        category="other",
        status="error",
        summary=None,
        insights=[],
        relevance_score=0.0,
    )
    db.insert(error_paper)
    db.close()

    mock_anthropic = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [
        MagicMock(
            text=json.dumps(
                {
                    "summary": "Retried",
                    "category": "coding-agent",
                    "tags": [],
                    "relevance_score": 0.5,
                    "insights": [],
                }
            )
        )
    ]
    mock_anthropic.Anthropic.return_value.messages.create.return_value = (
        mock_msg
    )
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = runner.invoke(
            app,
            ["analyze", "--retry-errors", "--config", str(config_file)],
        )
    assert result.exit_code == 0
    assert "1 analyzed" in result.output
