"""Obsidian vault operations: scan, parse, dedup, write, wikilink."""

import logging
import re
from datetime import date
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n", re.MULTILINE | re.DOTALL)


def load_config(config_path: str | Path) -> dict:
    """Load and validate a research_interests.yaml config file.

    Raises SystemExit(1) with user-friendly message on:
    - File not found
    - YAML syntax error
    - Empty or non-dict config
    """
    path = Path(config_path)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Config file not found: %s — run /reading-config to initialize", path)
        raise SystemExit(1)
    except OSError as e:
        logger.error("Cannot read config file %s: %s", path, e)
        raise SystemExit(1)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error("Config YAML syntax error in %s: %s", path, e)
        raise SystemExit(1)

    if not isinstance(data, dict):
        logger.error("Config file %s is empty or not a YAML mapping", path)
        raise SystemExit(1)

    return data


def parse_date_field(value) -> date | None:
    """Parse a date from frontmatter value.

    Handles both Python date objects (from PyYAML auto-parsing)
    and ISO date strings (from quoted YAML values).
    """
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content.

    Returns empty dict if frontmatter is missing or malformed.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter: %s", e)
        return {}


def scan_papers(vault_path: Path) -> list[dict]:
    """Scan 20_Papers/ for all paper notes, return list of frontmatter dicts.

    Tolerates missing fields — only requires arxiv_id to be present.
    Skips notes without valid frontmatter or without arxiv_id.
    """
    papers_dir = vault_path / "20_Papers"
    if not papers_dir.exists():
        return []

    results = []
    for md_file in papers_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Cannot read %s: %s", md_file, e)
            continue

        fm = parse_frontmatter(content)
        if not fm.get("arxiv_id"):
            continue

        fm["_path"] = str(md_file.relative_to(vault_path))
        results.append(fm)

    return results


def build_dedup_set(scan_results: list[dict]) -> set[str]:
    """Build a set of arxiv_ids from scan results for deduplication."""
    return {r["arxiv_id"] for r in scan_results if r.get("arxiv_id")}


def generate_wikilinks(text: str, keyword_index: dict[str, str]) -> str:
    """Replace known keywords in text with [[wikilink]] format.

    - Skips content inside existing wikilinks [[...]]
    - Skips content inside code blocks (``` and inline `)
    - Case-insensitive matching
    - Uses single-pass combined regex to avoid double-wrapping
    """
    if not keyword_index:
        return text

    # Split text into protected and unprotected segments
    protected_pattern = re.compile(
        r"```.*?```"          # fenced code blocks
        r"|`[^`]+`"           # inline code
        r"|\[\[[^\]]+\]\]",   # existing wikilinks
        re.DOTALL,
    )

    parts = []
    last_end = 0
    for match in protected_pattern.finditer(text):
        if match.start() > last_end:
            segment = text[last_end : match.start()]
            segment = _replace_keywords(segment, keyword_index)
            parts.append(segment)
        parts.append(match.group())  # keep protected text as-is
        last_end = match.end()

    if last_end < len(text):
        segment = text[last_end:]
        segment = _replace_keywords(segment, keyword_index)
        parts.append(segment)

    return "".join(parts)


def _replace_keywords(text: str, keyword_index: dict[str, str]) -> str:
    """Replace keywords with wikilinks in an unprotected text segment.

    Uses a single-pass combined regex to avoid double-wrapping.
    """
    sorted_keywords = sorted(keyword_index.keys(), key=len, reverse=True)
    if not sorted_keywords:
        return text
    combined = "|".join(re.escape(kw) for kw in sorted_keywords)
    pattern = re.compile(f"({combined})", re.IGNORECASE)
    return pattern.sub(lambda m: f"[[{m.group()}]]", text)


def write_note(vault_path: Path, relative_path: str, content: str) -> Path:
    """Write a markdown note to the vault, creating directories as needed.

    Returns the absolute path of the written file.
    """
    full_path = vault_path / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    logger.info("Wrote note: %s", relative_path)
    return full_path
