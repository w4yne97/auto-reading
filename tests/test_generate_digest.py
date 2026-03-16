"""Integration tests for weekly-digest/scripts/generate_digest.py."""

import json
import sys
import textwrap
from datetime import date, timedelta
from unittest.mock import patch


class TestGenerateDigest:
    def test_collects_recent_papers(self, vault_path, output_path):
        """Test: papers fetched within --days are included and sorted by score."""
        today = date.today()
        for i, (title, score) in enumerate([
            ("High Score Paper", 9.0),
            ("Low Score Paper", 3.0),
            ("Mid Score Paper", 6.5),
        ]):
            note = vault_path / "20_Papers" / "coding-agent" / f"Paper-{i}.md"
            note.write_text(textwrap.dedent(f"""\
                ---
                arxiv_id: "2406.{10000 + i}"
                title: "{title}"
                domain: coding-agent
                score: {score}
                fetched: {today.isoformat()}
                ---
                Content.
            """))

        argv = [
            "generate_digest.py",
            "--vault", str(vault_path),
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("weekly-digest.scripts.generate_digest")
            mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers_count"] == 3
        assert len(result["top_papers"]) == 3
        # Should be sorted by score descending
        scores = [float(p.get("score", 0)) for p in result["top_papers"]]
        assert scores == sorted(scores, reverse=True)

    def test_collects_daily_notes(self, vault_path, output_path):
        """Test: daily notes within date range are collected."""
        today = date.today()
        daily_dir = vault_path / "10_Daily"
        for i in range(3):
            d = today - timedelta(days=i)
            (daily_dir / f"{d.isoformat()}-论文推荐.md").write_text("Content")

        # Also add an old one
        old_date = today - timedelta(days=30)
        (daily_dir / f"{old_date.isoformat()}-论文推荐.md").write_text("Old")

        argv = [
            "generate_digest.py",
            "--vault", str(vault_path),
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("weekly-digest.scripts.generate_digest")
            mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["daily_notes"]) == 3

    def test_collects_insight_updates(self, vault_path, output_path):
        """Test: insight docs updated within date range are collected."""
        today = date.today()
        insight_dir = vault_path / "30_Insights" / "RL-for-Code"
        insight_dir.mkdir(parents=True)
        (insight_dir / "_index.md").write_text(textwrap.dedent(f"""\
            ---
            title: "RL for Code"
            type: insight-index
            updated: {today.isoformat()}
            ---
            Overview.
        """))

        argv = [
            "generate_digest.py",
            "--vault", str(vault_path),
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("weekly-digest.scripts.generate_digest")
            mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["insight_updates"]) == 1
        assert result["insight_updates"][0]["title"] == "RL for Code"
        assert result["insight_updates"][0]["type"] == "insight-index"

    def test_period_field_in_output(self, vault_path, output_path):
        """Test: output contains correct period field."""
        today = date.today()
        cutoff = today - timedelta(days=7)

        argv = [
            "generate_digest.py",
            "--vault", str(vault_path),
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("weekly-digest.scripts.generate_digest")
            mod.main()

        result = json.loads(output_path.read_text())
        assert result["period"]["from"] == cutoff.isoformat()
        assert result["period"]["to"] == today.isoformat()

    def test_dedup_papers_by_arxiv_id(self, vault_path, output_path):
        """Test: duplicate arxiv_ids are deduplicated."""
        today = date.today()
        for subdir in ["coding-agent", "rl-for-code"]:
            d = vault_path / "20_Papers" / subdir
            d.mkdir(parents=True, exist_ok=True)
            (d / "Same-Paper.md").write_text(textwrap.dedent(f"""\
                ---
                arxiv_id: "2406.99999"
                title: "Duplicate Paper"
                score: 7.0
                fetched: {today.isoformat()}
                ---
                Content.
            """))

        argv = [
            "generate_digest.py",
            "--vault", str(vault_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("weekly-digest.scripts.generate_digest")
            mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers_count"] == 1
