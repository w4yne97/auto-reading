"""Tests for Obsidian Markdown writer."""

from dataclasses import replace
from pathlib import Path

import pytest

from auto_reading.writer import ObsidianWriter


@pytest.fixture
def vault_path(tmp_path) -> Path:
    return tmp_path / "vault"


@pytest.fixture
def writer(vault_path) -> ObsidianWriter:
    return ObsidianWriter(
        vault_path=vault_path,
        categories=["coding-agent", "tool-use", "llm-reasoning"],
    )


def test_init_vault_creates_directories(
    writer: ObsidianWriter, vault_path: Path
):
    writer.init_vault()
    assert (vault_path / "papers").is_dir()
    assert (vault_path / "papers" / "coding-agent").is_dir()
    assert (vault_path / "papers" / "tool-use").is_dir()
    assert (vault_path / "digests").is_dir()
    assert (vault_path / "insights").is_dir()


def test_write_paper_creates_file(
    writer: ObsidianWriter, vault_path: Path, sample_paper
):
    analyzed = replace(
        sample_paper,
        summary="A great paper about coding agents.",
        insights=["Insight 1", "Insight 2"],
        relevance_score=0.92,
    )
    writer.init_vault()
    path = writer.write_paper(analyzed)
    assert path is not None
    assert path.exists()
    content = path.read_text()
    assert "CodeAgent" in content
    assert "coding-agent" in content
    assert "A great paper about coding agents." in content
    assert "Insight 1" in content


def test_write_paper_in_category_subfolder(
    writer: ObsidianWriter, vault_path: Path, sample_paper
):
    writer.init_vault()
    path = writer.write_paper(sample_paper)
    assert path is not None
    assert "coding-agent" in str(path.parent.name)


def test_write_paper_skips_existing(
    writer: ObsidianWriter, vault_path: Path, sample_paper
):
    writer.init_vault()
    path1 = writer.write_paper(sample_paper)
    path2 = writer.write_paper(sample_paper)
    assert path1 is not None
    assert path2 is None  # skipped


def test_write_paper_force_overwrites_but_preserves_notes(
    writer: ObsidianWriter, vault_path: Path, sample_paper
):
    writer.init_vault()
    path = writer.write_paper(sample_paper)
    assert path is not None

    # Simulate user adding notes
    original = path.read_text()
    modified = original.replace(
        "(Add your notes here)", "My custom research notes here"
    )
    path.write_text(modified)

    updated = replace(sample_paper, summary="Updated summary")
    path2 = writer.write_paper(updated, force=True)
    assert path2 is not None
    content = path2.read_text()
    assert "Updated summary" in content
    assert "My custom research notes here" in content


def test_write_paper_moves_on_category_change(
    writer: ObsidianWriter, vault_path: Path, sample_paper
):
    writer.init_vault()
    path1 = writer.write_paper(sample_paper)
    assert path1 is not None
    assert "coding-agent" in str(path1)

    # Simulate category change via re-analysis
    recategorized = replace(sample_paper, category="tool-use")
    path2 = writer.write_paper(recategorized, force=True)
    assert path2 is not None
    assert "tool-use" in str(path2)
    assert not path1.exists()  # old file removed


def test_slug_generation(writer: ObsidianWriter):
    slug = writer._make_slug("CodeAgent: Autonomous Coding with LLMs!")
    assert slug == "codeagent-autonomous-coding-with-llms"
    assert " " not in slug
    assert "!" not in slug
