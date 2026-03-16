"""Tests for vault operations."""

import textwrap
from pathlib import Path

from lib.vault import parse_frontmatter, scan_papers, build_dedup_set, generate_wikilinks, write_note


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            title: "Test Paper"
            arxiv_id: "2406.12345"
            domain: coding-agent
            tags: [RL, RLHF]
            score: 8.2
            status: unread
            ---

            ## Summary
            Some content here.
        """)
        fm = parse_frontmatter(content)
        assert fm["title"] == "Test Paper"
        assert fm["arxiv_id"] == "2406.12345"
        assert fm["tags"] == ["RL", "RLHF"]

    def test_missing_frontmatter(self):
        content = "# Just a heading\n\nSome text."
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_malformed_yaml(self):
        content = "---\ntitle: [unclosed\n---\nBody."
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_empty_frontmatter(self):
        content = "---\n---\nBody."
        fm = parse_frontmatter(content)
        assert fm == {}


class TestScanPapers:
    def test_scan_papers_directory(self, tmp_path: Path):
        papers_dir = tmp_path / "20_Papers" / "coding-agent"
        papers_dir.mkdir(parents=True)

        note1 = papers_dir / "Paper-A.md"
        note1.write_text(textwrap.dedent("""\
            ---
            title: "Paper A"
            arxiv_id: "2406.00001"
            domain: coding-agent
            score: 7.5
            ---

            Content.
        """))

        note2 = papers_dir / "Paper-B.md"
        note2.write_text(textwrap.dedent("""\
            ---
            title: "Paper B"
            arxiv_id: "2406.00002"
            domain: coding-agent
            score: 6.0
            ---

            Content.
        """))

        results = scan_papers(tmp_path)
        assert len(results) == 2
        ids = {r["arxiv_id"] for r in results}
        assert ids == {"2406.00001", "2406.00002"}

    def test_scan_skips_corrupted_frontmatter(self, tmp_path: Path):
        papers_dir = tmp_path / "20_Papers" / "other"
        papers_dir.mkdir(parents=True)

        bad = papers_dir / "Bad-Note.md"
        bad.write_text("# No frontmatter\nJust text.")

        good = papers_dir / "Good-Note.md"
        good.write_text("---\narxiv_id: '2406.00003'\ntitle: Good\n---\nContent.")

        results = scan_papers(tmp_path)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00003"

    def test_scan_empty_vault(self, tmp_path: Path):
        results = scan_papers(tmp_path)
        assert results == []

    def test_scan_tolerates_missing_fields(self, tmp_path: Path):
        papers_dir = tmp_path / "20_Papers" / "coding-agent"
        papers_dir.mkdir(parents=True)

        v1_note = papers_dir / "Old-Note.md"
        v1_note.write_text("---\narxiv_id: '2406.00004'\ncategory: coding-agent\ndate: 2026-01-01\n---\nOld.")

        results = scan_papers(tmp_path)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00004"


class TestBuildDedupSet:
    def test_dedup_from_scan_results(self):
        scan_results = [
            {"arxiv_id": "2406.00001", "title": "A"},
            {"arxiv_id": "2406.00002", "title": "B"},
        ]
        dedup = build_dedup_set(scan_results)
        assert dedup == {"2406.00001", "2406.00002"}

    def test_dedup_empty(self):
        assert build_dedup_set([]) == set()

    def test_dedup_skips_missing_id(self):
        scan_results = [
            {"arxiv_id": "2406.00001"},
            {"title": "No ID"},
        ]
        dedup = build_dedup_set(scan_results)
        assert dedup == {"2406.00001"}


class TestGenerateWikilinks:
    def test_replace_known_keyword(self):
        text = "We use BLIP for training."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert "[[BLIP]]" in result

    def test_preserve_existing_wikilink(self):
        text = "See [[BLIP]] for details."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert result.count("[[BLIP]]") == 1

    def test_skip_code_blocks(self):
        text = "Use `BLIP` in code.\n```\nBLIP = load()\n```"
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert "[[BLIP]]" not in result
        assert "`BLIP`" in result

    def test_no_match(self):
        text = "Nothing relevant here."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert result == text


class TestWriteNote:
    def test_write_creates_file(self, tmp_path: Path):
        path = write_note(tmp_path, "20_Papers/test/Note.md", "---\ntitle: X\n---\nBody")
        assert path.exists()
        assert "title: X" in path.read_text()

    def test_write_creates_directories(self, tmp_path: Path):
        path = write_note(tmp_path, "deep/nested/dir/Note.md", "Content")
        assert path.exists()
        assert path.read_text() == "Content"
