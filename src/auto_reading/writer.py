"""Obsidian vault Markdown writer."""

import logging
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader

from auto_reading.models import Paper

logger = logging.getLogger(__name__)

MY_NOTES_HEADER = "## My Notes"


class ObsidianWriter:
    """Writes paper notes to an Obsidian vault."""

    def __init__(self, vault_path: Path, categories: list[str]):
        self._vault_path = vault_path
        self._categories = categories
        self._env = Environment(
            loader=PackageLoader("auto_reading", "templates"),
            keep_trailing_newline=True,
        )

    def init_vault(self) -> None:
        """Create vault directory structure if it doesn't exist."""
        dirs = ["papers", "digests", "insights", "sources"]
        for d in dirs:
            (self._vault_path / d).mkdir(parents=True, exist_ok=True)

        for category in self._categories:
            (self._vault_path / "papers" / category).mkdir(
                parents=True, exist_ok=True
            )

    def write_paper(self, paper: Paper, force: bool = False) -> Path | None:
        """Write a paper note to the vault.

        Returns the path if written, None if skipped (already exists).
        On force-sync with category change, moves the file to the new folder.
        """
        slug = self._make_slug(paper.title)
        filename = f"{paper.published_at.isoformat()}-{slug}.md"
        category_dir = self._vault_path / "papers" / paper.category
        category_dir.mkdir(parents=True, exist_ok=True)
        filepath = category_dir / filename

        # Check for existing file in a different category (category change)
        old_path = self._find_existing_note(
            filename, exclude_dir=category_dir
        )

        if filepath.exists() and not force:
            logger.info("Skipping existing note: %s", filepath)
            return None

        if old_path and not force:
            logger.info(
                "Skipping existing note (different category): %s", old_path
            )
            return None

        # Preserve user notes from whichever existing file we find
        user_notes: str | None = None
        if filepath.exists():
            user_notes = self._extract_user_notes(filepath)
        elif old_path:
            user_notes = self._extract_user_notes(old_path)
            old_path.unlink()
            logger.info(
                "Moved note from %s to %s",
                old_path.parent.name,
                paper.category,
            )

        template = self._env.get_template("paper_note.md")
        content = template.render(paper=paper)

        if user_notes is not None:
            content = self._replace_notes_section(content, user_notes)

        filepath.write_text(content)
        logger.info("Wrote paper note: %s", filepath)
        return filepath

    def _find_existing_note(
        self, filename: str, exclude_dir: Path
    ) -> Path | None:
        """Search for a note with the same filename in other category folders."""
        papers_dir = self._vault_path / "papers"
        if not papers_dir.exists():
            return None
        for category_dir in papers_dir.iterdir():
            if not category_dir.is_dir() or category_dir == exclude_dir:
                continue
            candidate = category_dir / filename
            if candidate.exists():
                return candidate
        return None

    def _extract_user_notes(self, filepath: Path) -> str | None:
        """Extract user-written content from the My Notes section."""
        content = filepath.read_text()
        marker_idx = content.find(MY_NOTES_HEADER)
        if marker_idx == -1:
            return None
        notes_start = marker_idx + len(MY_NOTES_HEADER)
        return content[notes_start:].strip()

    def _replace_notes_section(
        self, content: str, user_notes: str
    ) -> str:
        """Replace the My Notes section with preserved user content."""
        marker_idx = content.find(MY_NOTES_HEADER)
        if marker_idx == -1:
            return content
        before = content[: marker_idx + len(MY_NOTES_HEADER)]
        return f"{before}\n{user_notes}\n"

    def _make_slug(self, title: str) -> str:
        """Convert title to URL-friendly slug."""
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug)
        slug = slug.strip("-")
        return slug
