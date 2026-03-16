"""Integration tests for insight-update/scripts/scan_recent_papers.py."""

import json
import sys
import textwrap
from datetime import date, timedelta
from unittest.mock import patch


class TestScanRecentPapers:
    def test_finds_recent_papers(self, vault_path, output_path):
        """Test: papers with fetched date after --since are included."""
        today = date.today()
        note = vault_path / "20_Papers" / "coding-agent" / "Recent-Paper.md"
        note.write_text(textwrap.dedent(f"""\
            ---
            arxiv_id: "2406.11111"
            title: "Recent Paper"
            domain: coding-agent
            tags: [RL, coding-agent]
            fetched: {today.isoformat()}
            ---
            Content.
        """))

        since = (today - timedelta(days=7)).isoformat()

        argv = [
            "scan_recent_papers.py",
            "--vault", str(vault_path),
            "--since", since,
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("insight-update.scripts.scan_recent_papers")
            mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 1
        assert result["papers"][0]["arxiv_id"] == "2406.11111"
        assert result["papers"][0]["domain"] == "coding-agent"
        assert result["papers"][0]["tags"] == ["RL", "coding-agent"]

    def test_excludes_old_papers(self, vault_path, output_path):
        """Test: papers with fetched date before --since are excluded."""
        note = vault_path / "20_Papers" / "coding-agent" / "Old-Paper.md"
        note.write_text(textwrap.dedent("""\
            ---
            arxiv_id: "2406.22222"
            title: "Old Paper"
            domain: coding-agent
            fetched: "2025-01-01"
            ---
            Content.
        """))

        argv = [
            "scan_recent_papers.py",
            "--vault", str(vault_path),
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("insight-update.scripts.scan_recent_papers")
            mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 0

    def test_skips_notes_without_arxiv_id(self, vault_path, output_path):
        """Test: notes missing arxiv_id are skipped."""
        note = vault_path / "20_Papers" / "coding-agent" / "No-ID.md"
        note.write_text(textwrap.dedent("""\
            ---
            title: "No ID Paper"
            fetched: "2026-03-15"
            ---
            Content.
        """))

        argv = [
            "scan_recent_papers.py",
            "--vault", str(vault_path),
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("insight-update.scripts.scan_recent_papers")
            mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 0

    def test_empty_vault(self, output_path, tmp_path):
        """Test: empty vault returns empty papers list."""
        empty_vault = tmp_path / "empty_vault"
        empty_vault.mkdir()

        argv = [
            "scan_recent_papers.py",
            "--vault", str(empty_vault),
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("insight-update.scripts.scan_recent_papers")
            mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers"] == []
