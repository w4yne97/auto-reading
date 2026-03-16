# Auto-Reading Phase 1 (MVP) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an on-demand CLI tool that fetches papers from AlphaRxiv and GitHub, analyzes them with Claude, and syncs structured notes into an Obsidian vault.

**Architecture:** Python CLI (typer) → Core service layer (fetchers, analyzer, DB, writer) → Obsidian vault (Markdown files). Each module has a single responsibility and communicates through the `Paper` dataclass. SQLite stores metadata; Jinja2 generates Markdown.

**Tech Stack:** Python 3.12+, uv, typer, httpx, anthropic SDK, Pydantic, Jinja2, SQLite, pytest

**Spec:** `docs/superpowers/specs/2026-03-16-auto-reading-design.md`

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Project metadata, dependencies, CLI entry point |
| `config.yaml` | Default user configuration |
| `src/auto_reading/__init__.py` | Package init, version |
| `src/auto_reading/models.py` | `Paper` frozen dataclass |
| `src/auto_reading/config.py` | Pydantic config models, YAML loading, validation |
| `src/auto_reading/db.py` | SQLite CRUD, schema init, dedup, JSON serialization |
| `src/auto_reading/fetchers/__init__.py` | Fetcher registry |
| `src/auto_reading/fetchers/base.py` | `BaseFetcher` abstract class |
| `src/auto_reading/fetchers/alphaarxiv.py` | AlphaRxiv scraping fetcher |
| `src/auto_reading/fetchers/github.py` | GitHub trending + releases fetcher |
| `src/auto_reading/analyzer.py` | Claude API analysis (summary, classify, score) |
| `src/auto_reading/writer.py` | Obsidian Markdown generation + vault sync |
| `src/auto_reading/templates/paper_note.md` | Jinja2 template for paper notes |
| `src/auto_reading/templates/weekly_digest.md` | Jinja2 template for digests (scaffold only) |
| `src/auto_reading/cli.py` | Typer CLI commands (fetch, analyze, sync, run) |
| `tests/conftest.py` | Shared fixtures (tmp dirs, sample papers, mock config) |
| `tests/test_models.py` | Paper dataclass tests |
| `tests/test_config.py` | Config loading + validation tests |
| `tests/test_db.py` | SQLite CRUD + dedup tests |
| `tests/test_fetchers.py` | Fetcher tests (mocked HTTP) |
| `tests/test_analyzer.py` | Analyzer tests (mocked Claude API) |
| `tests/test_writer.py` | Writer tests (file generation + idempotency) |
| `tests/test_cli.py` | CLI integration tests |

---

## Chunk 1: Foundation — Project Scaffolding, Models, Config, Database

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/auto_reading/__init__.py`
- Create: `config.yaml`
- Create: `.gitignore`

- [ ] **Step 1: Initialize uv project**

Run:
```bash
cd /Users/w4ynewang/Documents/code/auto-reading
uv init --lib --name auto-reading
```

- [ ] **Step 2: Replace pyproject.toml with full config**

```toml
[project]
name = "auto-reading"
version = "0.1.0"
description = "LLM-driven paper tracking system for AI research"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
    "httpx>=0.28.0",
    "anthropic>=0.52.0",
    "pydantic>=2.11.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
    "beautifulsoup4>=4.12.0",
]

[project.scripts]
auto-reading = "auto_reading.cli:app"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=5.0",
    "respx>=0.22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Write __init__.py**

```python
"""Auto-Reading: LLM-driven paper tracking system."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Write default config.yaml**

```yaml
obsidian:
  vault_path: ~/auto-reading-vault

sources:
  alphaarxiv:
    enabled: true
    topics: ["coding agent", "code generation", "llm agent"]
  github:
    enabled: true
    topics: ["coding-agent", "ai-coding"]
    tracked_repos:
      - "paul-gauthier/aider"
      - "OpenDevin/OpenDevin"
      - "princeton-nlp/SWE-agent"

categories:
  - coding-agent
  - llm-reasoning
  - code-generation
  - tool-use
  - evaluation
  - infrastructure

claude:
  model: claude-sonnet-4-6
  max_tokens: 4096

fetch:
  default_days: 7
  max_papers_per_run: 50
```

- [ ] **Step 5: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
dist/
*.egg-info/
.superpowers/
auto-reading.db
.env
```

- [ ] **Step 6: Install dependencies**

Run:
```bash
uv sync
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/auto_reading/__init__.py config.yaml .gitignore uv.lock .python-version
git commit -m "chore: scaffold project with uv, dependencies, and default config"
```

---

### Task 2: Paper Data Model

**Files:**
- Create: `src/auto_reading/models.py`
- Create: `tests/test_models.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

`tests/conftest.py`:
```python
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
```

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auto_reading.models'`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/models.py`:
```python
"""Data models for auto-reading."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Paper:
    """Represents a paper or project entry from any source."""

    id: str
    title: str
    authors: list[str]
    abstract: str
    source: str
    source_url: str
    published_at: date
    fetched_at: datetime
    tags: list[str]
    category: str
    status: str
    summary: str | None
    insights: list[str]
    relevance_score: float
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/models.py tests/conftest.py tests/test_models.py
git commit -m "feat: add Paper frozen dataclass with tests"
```

---

### Task 3: Configuration Loading & Validation

**Files:**
- Create: `src/auto_reading/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
"""Tests for configuration loading and validation."""

import pytest
import yaml

from auto_reading.config import (
    AppConfig,
    ClaudeConfig,
    FetchConfig,
    ObsidianConfig,
    load_config,
)


def test_load_valid_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "obsidian": {"vault_path": str(tmp_path / "vault")},
                "categories": ["coding-agent", "tool-use"],
            }
        )
    )
    config = load_config(config_file)
    assert config.obsidian.vault_path == tmp_path / "vault"
    assert "coding-agent" in config.categories


def test_config_defaults(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump({"obsidian": {"vault_path": str(tmp_path / "vault")}})
    )
    config = load_config(config_file)
    assert config.claude.model == "claude-sonnet-4-6"
    assert config.claude.max_tokens == 4096
    assert config.fetch.default_days == 7
    assert config.fetch.max_papers_per_run == 50
    assert config.sources.alphaarxiv.enabled is True


def test_config_missing_vault_path(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"categories": ["coding-agent"]}))
    with pytest.raises(ValueError, match="vault_path"):
        load_config(config_file)


def test_config_empty_categories(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "obsidian": {"vault_path": str(tmp_path / "vault")},
                "categories": [],
            }
        )
    )
    with pytest.raises(ValueError, match="categories"):
        load_config(config_file)


def test_config_max_papers_must_be_positive(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "obsidian": {"vault_path": str(tmp_path / "vault")},
                "fetch": {"max_papers_per_run": 0},
            }
        )
    )
    with pytest.raises(ValueError, match="max_papers_per_run"):
        load_config(config_file)


def test_config_expands_tilde(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump({"obsidian": {"vault_path": "~/my-vault"}})
    )
    config = load_config(config_file)
    assert "~" not in str(config.obsidian.vault_path)


def test_config_file_not_found():
    from pathlib import Path

    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/config.py`:
```python
"""Configuration loading and validation."""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "coding-agent",
    "llm-reasoning",
    "code-generation",
    "tool-use",
    "evaluation",
    "infrastructure",
]


class ObsidianConfig(BaseModel):
    vault_path: Path

    @field_validator("vault_path", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser()


class AlphaRxivSourceConfig(BaseModel):
    enabled: bool = True
    topics: list[str] = ["coding agent", "code generation", "llm agent"]


class GitHubSourceConfig(BaseModel):
    enabled: bool = True
    topics: list[str] = ["coding-agent", "ai-coding"]
    tracked_repos: list[str] = [
        "paul-gauthier/aider",
        "OpenDevin/OpenDevin",
        "princeton-nlp/SWE-agent",
    ]


class SourcesConfig(BaseModel):
    alphaarxiv: AlphaRxivSourceConfig = AlphaRxivSourceConfig()
    github: GitHubSourceConfig = GitHubSourceConfig()


class ClaudeConfig(BaseModel):
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096


class FetchConfig(BaseModel):
    default_days: int = 7
    max_papers_per_run: int = 50

    @field_validator("max_papers_per_run")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_papers_per_run must be > 0")
        return v


class AppConfig(BaseModel):
    obsidian: ObsidianConfig
    sources: SourcesConfig = SourcesConfig()
    categories: list[str] = DEFAULT_CATEGORIES[:]
    claude: ClaudeConfig = ClaudeConfig()
    fetch: FetchConfig = FetchConfig()

    @field_validator("categories")
    @classmethod
    def must_have_categories(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("categories must contain at least one entry")
        return v


def load_config(path: Path) -> AppConfig:
    """Load and validate configuration from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    return AppConfig(**raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/config.py tests/test_config.py
git commit -m "feat: add config loading with Pydantic validation"
```

---

### Task 4: SQLite Database Layer

**Files:**
- Create: `src/auto_reading/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_db.py`:
```python
"""Tests for SQLite database operations."""

import json
from dataclasses import replace
from datetime import date, datetime

import pytest

from auto_reading.db import PaperDB
from auto_reading.models import Paper


@pytest.fixture
def db(tmp_path) -> PaperDB:
    return PaperDB(tmp_path / "test.db")


def test_init_creates_schema(db: PaperDB):
    """DB init creates the papers table and indexes."""
    import sqlite3

    conn = sqlite3.connect(db.db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_and_get(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    result = db.get(sample_paper.id)
    assert result is not None
    assert result.id == sample_paper.id
    assert result.title == sample_paper.title
    assert result.authors == sample_paper.authors
    assert result.tags == sample_paper.tags


def test_insert_duplicate_skips(db: PaperDB, sample_paper: Paper):
    inserted_1 = db.insert(sample_paper)
    inserted_2 = db.insert(sample_paper)
    assert inserted_1 is True
    assert inserted_2 is False


def test_list_by_status(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    analyzed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        status="read",
        summary="Done",
    )
    db.insert(analyzed)
    unread = db.list_by_status("unread")
    assert len(unread) == 1
    assert unread[0].id == "arxiv:2406.12345"


def test_list_unprocessed(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    processed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        summary="Has summary",
    )
    db.insert(processed)
    unprocessed = db.list_unprocessed()
    assert len(unprocessed) == 1
    assert unprocessed[0].id == sample_paper.id


def test_update(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    updated = replace(
        sample_paper,
        status="read",
        summary="A great summary",
        tags=["coding-agent", "new-tag"],
        relevance_score=0.95,
    )
    db.update(updated)
    result = db.get(sample_paper.id)
    assert result is not None
    assert result.status == "read"
    assert result.summary == "A great summary"
    assert "new-tag" in result.tags
    assert result.relevance_score == 0.95


def test_exists(db: PaperDB, sample_paper: Paper):
    assert db.exists(sample_paper.id) is False
    db.insert(sample_paper)
    assert db.exists(sample_paper.id) is True


def test_list_analyzed(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)  # no summary
    analyzed = replace(
        sample_paper,
        id="arxiv:2406.99999",
        summary="Has summary",
    )
    db.insert(analyzed)
    results = db.list_analyzed()
    assert len(results) == 1
    assert results[0].id == "arxiv:2406.99999"


def test_list_by_category(db: PaperDB, sample_paper: Paper):
    db.insert(sample_paper)
    other = replace(sample_paper, id="arxiv:2406.99999", category="tool-use")
    db.insert(other)
    results = db.list_by_category("coding-agent")
    assert len(results) == 1
    assert results[0].id == sample_paper.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/db.py`:
```python
"""SQLite database operations for paper storage."""

import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from auto_reading.models import Paper

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    abstract TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    summary TEXT,
    insights TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL
);

CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(category);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_at);
"""


def _paper_to_row(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": json.dumps(paper.authors),
        "abstract": paper.abstract,
        "source": paper.source,
        "source_url": paper.source_url,
        "published_at": paper.published_at.isoformat(),
        "fetched_at": paper.fetched_at.isoformat(),
        "tags": json.dumps(paper.tags),
        "category": paper.category,
        "status": paper.status,
        "summary": paper.summary,
        "insights": json.dumps(paper.insights),
        "relevance_score": paper.relevance_score,
    }


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        abstract=row["abstract"],
        source=row["source"],
        source_url=row["source_url"],
        published_at=date.fromisoformat(row["published_at"]),
        fetched_at=datetime.fromisoformat(row["fetched_at"]),
        tags=json.loads(row["tags"]),
        category=row["category"],
        status=row["status"],
        summary=row["summary"],
        insights=json.loads(row["insights"]),
        relevance_score=row["relevance_score"],
    )


class PaperDB:
    """SQLite-backed paper storage with deduplication."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def insert(self, paper: Paper) -> bool:
        """Insert a paper. Returns True if inserted, False if duplicate."""
        try:
            row = _paper_to_row(paper)
            self._conn.execute(
                """INSERT INTO papers (id, title, authors, abstract, source,
                   source_url, published_at, fetched_at, tags, category,
                   status, summary, insights, relevance_score)
                   VALUES (:id, :title, :authors, :abstract, :source,
                   :source_url, :published_at, :fetched_at, :tags, :category,
                   :status, :summary, :insights, :relevance_score)""",
                row,
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get(self, paper_id: str) -> Paper | None:
        """Get a paper by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        )
        row = cursor.fetchone()
        return _row_to_paper(row) if row else None

    def exists(self, paper_id: str) -> bool:
        """Check if a paper exists in the database."""
        cursor = self._conn.execute(
            "SELECT 1 FROM papers WHERE id = ?", (paper_id,)
        )
        return cursor.fetchone() is not None

    def update(self, paper: Paper) -> None:
        """Update an existing paper."""
        row = _paper_to_row(paper)
        self._conn.execute(
            """UPDATE papers SET title=:title, authors=:authors,
               abstract=:abstract, source=:source, source_url=:source_url,
               published_at=:published_at, fetched_at=:fetched_at,
               tags=:tags, category=:category, status=:status,
               summary=:summary, insights=:insights,
               relevance_score=:relevance_score
               WHERE id=:id""",
            row,
        )
        self._conn.commit()

    def list_by_status(self, status: str) -> list[Paper]:
        """List papers by status."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE status = ? ORDER BY published_at DESC",
            (status,),
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_unprocessed(self) -> list[Paper]:
        """List papers that haven't been analyzed yet (no summary)."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE summary IS NULL ORDER BY fetched_at ASC"
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_by_category(self, category: str) -> list[Paper]:
        """List papers by category."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE category = ? ORDER BY published_at DESC",
            (category,),
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def list_analyzed(self) -> list[Paper]:
        """List all papers that have been analyzed (have a summary)."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE summary IS NOT NULL ORDER BY published_at DESC"
        )
        return [_row_to_paper(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/db.py tests/test_db.py
git commit -m "feat: add SQLite database layer with CRUD and dedup"
```

---

## Chunk 2: Fetchers — AlphaRxiv and GitHub

### Task 5: Base Fetcher Interface

**Files:**
- Create: `src/auto_reading/fetchers/__init__.py`
- Create: `src/auto_reading/fetchers/base.py`

- [ ] **Step 1: Write the base fetcher**

`src/auto_reading/fetchers/base.py`:
```python
"""Abstract base class for paper fetchers."""

from abc import ABC, abstractmethod

from auto_reading.models import Paper


class BaseFetcher(ABC):
    """Base class for all paper source fetchers.

    Source-specific configuration (e.g., tracked repos, auth tokens)
    should be passed via the constructor, so that fetch() has a
    uniform signature across all fetchers.
    """

    @abstractmethod
    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        """Fetch papers matching topics from the last N days.

        Args:
            topics: List of topic keywords to search for.
            days: Number of days to look back.

        Returns:
            List of Paper objects (unanalyzed — summary/insights/score empty).
        """
        ...
```

`src/auto_reading/fetchers/__init__.py`:
```python
"""Paper source fetchers."""

from auto_reading.fetchers.base import BaseFetcher

__all__ = ["BaseFetcher"]
```

- [ ] **Step 1b: Write a quick test for BaseFetcher abstractness**

Add to `tests/test_fetchers.py`:
```python
import pytest
from auto_reading.fetchers.base import BaseFetcher


def test_base_fetcher_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseFetcher()
```

- [ ] **Step 2: Commit**

```bash
git add src/auto_reading/fetchers/
git commit -m "feat: add BaseFetcher abstract interface"
```

---

### Task 6: AlphaRxiv Fetcher

**Files:**
- Create: `src/auto_reading/fetchers/alphaarxiv.py`
- Create: `tests/test_fetchers.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_fetchers.py`:
```python
"""Tests for paper fetchers."""

import httpx
import pytest
import respx

from auto_reading.fetchers.alphaarxiv import AlphaRxivFetcher

SAMPLE_ALPHAARXIV_HTML = """
<html>
<body>
<div class="paper-list">
  <div class="paper-card" data-arxiv-id="2406.12345">
    <h2 class="paper-title">
      <a href="https://arxiv.org/abs/2406.12345">CodeAgent: Autonomous Coding</a>
    </h2>
    <div class="paper-authors">Alice Smith, Bob Jones</div>
    <div class="paper-abstract">
      We present CodeAgent, a system for autonomous code generation using LLMs.
    </div>
    <div class="paper-date">2026-03-15</div>
  </div>
  <div class="paper-card" data-arxiv-id="2406.67890">
    <h2 class="paper-title">
      <a href="https://arxiv.org/abs/2406.67890">Unrelated Biology Paper</a>
    </h2>
    <div class="paper-authors">Carol White</div>
    <div class="paper-abstract">
      A study on protein folding mechanisms in extreme environments.
    </div>
    <div class="paper-date">2026-03-14</div>
  </div>
</div>
</body>
</html>
"""


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_parses_papers():
    respx.get("https://alphaarxiv.org/").respond(
        200, html=SAMPLE_ALPHAARXIV_HTML
    )
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert len(papers) >= 1
    paper = papers[0]
    assert paper.id == "arxiv:2406.12345"
    assert paper.source == "alphaarxiv"
    assert paper.source_url == "https://arxiv.org/abs/2406.12345"
    assert paper.summary is None
    assert paper.status == "unread"


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_handles_http_error():
    respx.get("https://alphaarxiv.org/").respond(500)
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_handles_malformed_html():
    respx.get("https://alphaarxiv.org/").respond(
        200, html="<html><body>No papers here</body></html>"
    )
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert papers == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fetchers.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

Note: The actual AlphaRxiv HTML structure must be discovered at implementation time. The fetcher below uses CSS selectors that should be adjusted to match the real site. The test HTML above is a reasonable placeholder. At implementation time, the developer should:
1. Visit `https://alphaarxiv.org/` and inspect the actual HTML structure
2. Adjust the CSS selectors in the fetcher accordingly
3. Update the test HTML to match the real structure

`src/auto_reading/fetchers/alphaarxiv.py`:
```python
"""AlphaRxiv paper fetcher via web scraping."""

import logging
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from auto_reading.fetchers.base import BaseFetcher
from auto_reading.models import Paper

logger = logging.getLogger(__name__)

ALPHAARXIV_URL = "https://alphaarxiv.org/"


class AlphaRxivFetcher(BaseFetcher):
    """Fetches trending papers from AlphaRxiv via HTML scraping."""

    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(ALPHAARXIV_URL, timeout=30.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("AlphaRxiv fetch failed: %s", e)
            return []

        return self._parse_papers(response.text, topics)

    def _parse_papers(self, html: str, topics: list[str]) -> list[Paper]:
        soup = BeautifulSoup(html, "html.parser")
        papers: list[Paper] = []

        for card in soup.select(".paper-card"):
            try:
                paper = self._parse_card(card)
                if paper is not None:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse paper card: %s", e)
                continue

        return papers

    def _parse_card(self, card) -> Paper | None:
        arxiv_id = card.get("data-arxiv-id")
        if not arxiv_id:
            return None

        title_el = card.select_one(".paper-title a")
        title = title_el.get_text(strip=True) if title_el else "Unknown"
        url = title_el["href"] if title_el and title_el.has_attr("href") else f"https://arxiv.org/abs/{arxiv_id}"

        authors_el = card.select_one(".paper-authors")
        authors_text = authors_el.get_text(strip=True) if authors_el else ""
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]

        abstract_el = card.select_one(".paper-abstract")
        abstract = abstract_el.get_text(strip=True) if abstract_el else ""

        date_el = card.select_one(".paper-date")
        published_at = (
            date.fromisoformat(date_el.get_text(strip=True))
            if date_el
            else date.today()
        )

        return Paper(
            id=f"arxiv:{arxiv_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            source="alphaarxiv",
            source_url=url,
            published_at=published_at,
            fetched_at=datetime.now(),
            tags=[],
            category="other",
            status="unread",
            summary=None,
            insights=[],
            relevance_score=0.0,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fetchers.py -v`
Expected: 4 passed (3 AlphaRxiv + 1 BaseFetcher abstraction test)

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/fetchers/alphaarxiv.py tests/test_fetchers.py
git commit -m "feat: add AlphaRxiv fetcher with HTML scraping"
```

---

### Task 7: GitHub Fetcher

**Files:**
- Create: `src/auto_reading/fetchers/github.py`
- Modify: `tests/test_fetchers.py` (append new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fetchers.py`:
```python
from auto_reading.fetchers.github import GitHubFetcher

SAMPLE_GITHUB_RELEASES_JSON = [
    {
        "tag_name": "v0.50.0",
        "name": "Aider v0.50.0",
        "body": "## What's new\n- Added multi-file editing\n- Improved context handling",
        "published_at": "2026-03-14T10:00:00Z",
        "html_url": "https://github.com/paul-gauthier/aider/releases/tag/v0.50.0",
    },
    {
        "tag_name": "v0.49.0",
        "name": "Aider v0.49.0",
        "body": "Bug fixes and improvements",
        "published_at": "2026-03-07T10:00:00Z",
        "html_url": "https://github.com/paul-gauthier/aider/releases/tag/v0.49.0",
    },
]


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_releases():
    respx.get(
        "https://api.github.com/repos/paul-gauthier/aider/releases"
    ).respond(200, json=SAMPLE_GITHUB_RELEASES_JSON)
    fetcher = GitHubFetcher(tracked_repos=["paul-gauthier/aider"])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert len(papers) >= 1
    paper = papers[0]
    assert paper.id == "github:paul-gauthier/aider:v0.50.0"
    assert paper.source == "github"
    assert "aider" in paper.title.lower() or "Aider" in paper.title


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_releases_handles_error():
    respx.get(
        "https://api.github.com/repos/paul-gauthier/aider/releases"
    ).respond(404)
    fetcher = GitHubFetcher(tracked_repos=["paul-gauthier/aider"])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_no_tracked_repos():
    fetcher = GitHubFetcher(tracked_repos=[])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert papers == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fetchers.py::test_github_fetch_releases -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/fetchers/github.py`:
```python
"""GitHub fetcher for releases from tracked repositories."""

import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from auto_reading.fetchers.base import BaseFetcher
from auto_reading.models import Paper

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubFetcher(BaseFetcher):
    """Fetches release notes from tracked GitHub repositories.

    Source-specific config (tracked repos, auth) is passed via constructor,
    keeping the fetch() signature consistent with BaseFetcher.
    """

    def __init__(
        self, tracked_repos: list[str], token: str | None = None
    ):
        self._tracked_repos = tracked_repos
        self._headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        if not self._tracked_repos:
            return []
        return await self._fetch_releases(days)

    async def _fetch_releases(self, days: int) -> list[Paper]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        papers: list[Paper] = []

        async with httpx.AsyncClient(headers=self._headers) as client:
            for repo in self._tracked_repos:
                try:
                    repo_papers = await self._fetch_repo_releases(
                        client, repo, cutoff
                    )
                    papers.extend(repo_papers)
                except Exception as e:
                    logger.warning("Failed to fetch releases for %s: %s", repo, e)
                    continue

        return papers

    async def _fetch_repo_releases(
        self, client: httpx.AsyncClient, repo: str, cutoff: datetime
    ) -> list[Paper]:
        url = f"{GITHUB_API}/repos/{repo}/releases"
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("GitHub API error for %s: %s", repo, e)
            return []

        releases = response.json()
        papers: list[Paper] = []

        for release in releases:
            published_str = release.get("published_at", "")
            if not published_str:
                continue

            published_dt = datetime.fromisoformat(
                published_str.replace("Z", "+00:00")
            )
            if published_dt < cutoff:
                continue

            tag = release.get("tag_name", "unknown")
            title = release.get("name") or f"{repo} {tag}"
            body = release.get("body", "") or ""
            html_url = release.get("html_url", f"https://github.com/{repo}")

            owner = repo.split("/")[0] if "/" in repo else repo

            paper = Paper(
                id=f"github:{repo}:{tag}",
                title=title,
                authors=[owner],
                abstract=body[:2000],
                source="github",
                source_url=html_url,
                published_at=published_dt.date(),
                fetched_at=datetime.now(),
                tags=[],
                category="other",
                status="unread",
                summary=None,
                insights=[],
                relevance_score=0.0,
            )
            papers.append(paper)

        return papers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fetchers.py -v`
Expected: 7 passed (4 prior + 3 GitHub tests)

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/fetchers/github.py tests/test_fetchers.py
git commit -m "feat: add GitHub fetcher for tracked repo releases"
```

---

## Chunk 3: Analyzer and Writer

### Task 8: Claude Analyzer

**Files:**
- Create: `src/auto_reading/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_analyzer.py`:
```python
"""Tests for Claude-based paper analyzer."""

import json
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analyzer.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/analyzer.py`:
```python
"""Claude-based paper analysis: summarization, classification, scoring."""

import json
import logging
import time
from dataclasses import dataclass, replace

from auto_reading.models import Paper

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 4, 16]  # seconds

SYSTEM_PROMPT = """You are a research paper analyst specializing in AI/ML.
Given a paper's title and abstract, produce a JSON analysis."""

USER_PROMPT_TEMPLATE = """## Paper
Title: {title}
Abstract: {abstract}

## Available Categories
{categories}

## Instructions
Analyze this paper and return JSON (no markdown fences, just raw JSON):
{{
  "summary": "2-3 paragraph summary of key contributions and methods",
  "category": "one of the available categories, or 'other'",
  "tags": ["3-5 descriptive tags, reuse existing tags when applicable"],
  "relevance_score": 0.0-1.0,
  "insights": ["2-3 key takeaways or novel ideas"]
}}

Relevance scoring guide:
- 0.8-1.0: Directly about coding agents, code generation with LLMs
- 0.5-0.8: Related (general LLM agents, tool use, code understanding)
- 0.2-0.5: Tangentially related (general NLP, ML infrastructure)
- 0.0-0.2: Minimal relevance to coding agents"""


@dataclass(frozen=True)
class AnalysisResult:
    """Result of Claude's paper analysis."""

    summary: str
    category: str
    tags: list[str]
    relevance_score: float
    insights: list[str]

    def apply_to(self, paper: Paper) -> Paper:
        """Create a new Paper with analysis results applied."""
        return replace(
            paper,
            summary=self.summary,
            category=self.category,
            tags=self.tags,
            relevance_score=self.relevance_score,
            insights=self.insights,
        )


class Analyzer:
    """Analyzes papers using the Claude API."""

    def __init__(self, client, model: str, categories: list[str]):
        self._client = client
        self._model = model
        self._categories = categories

    def analyze(self, paper: Paper) -> AnalysisResult:
        """Analyze a single paper with retry on transient errors.

        Retries up to 3 times with exponential backoff (1s, 4s, 16s).
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=paper.title,
            abstract=paper.abstract,
            categories="\n".join(f"- {c}" for c in self._categories),
        )

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                message = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                response_text = message.content[0].text
                return self._parse_response(response_text)
            except ValueError:
                raise  # JSON parse errors are not transient, don't retry
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = BACKOFF_DELAYS[attempt]
                    logger.warning(
                        "Claude API error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                        e,
                    )
                    time.sleep(delay)

        raise last_error  # type: ignore[misc]

    def _parse_response(self, response_text: str) -> AnalysisResult:
        """Parse Claude's JSON response into an AnalysisResult."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse Claude response as JSON: {e}\n"
                f"Response: {response_text[:500]}"
            )

        return AnalysisResult(
            summary=data["summary"],
            category=data.get("category", "other"),
            tags=data.get("tags", []),
            relevance_score=float(data.get("relevance_score", 0.0)),
            insights=data.get("insights", []),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analyzer.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/auto_reading/analyzer.py tests/test_analyzer.py
git commit -m "feat: add Claude-based paper analyzer with structured prompts"
```

---

### Task 9: Obsidian Writer

**Files:**
- Create: `src/auto_reading/writer.py`
- Create: `src/auto_reading/templates/paper_note.md`
- Create: `src/auto_reading/templates/weekly_digest.md`
- Create: `tests/test_writer.py`

- [ ] **Step 1: Write the Jinja2 templates**

`src/auto_reading/templates/paper_note.md`:
```
---
title: "{{ paper.title }}"
authors: [{{ paper.authors | join(', ') }}]
source: {{ paper.source }}
url: {{ paper.source_url }}
date: {{ paper.published_at.isoformat() }}
tags: [{{ paper.tags | join(', ') }}]
category: {{ paper.category }}
relevance: {{ paper.relevance_score }}
status: {{ paper.status }}
---

## Summary
{{ paper.summary or '(Not yet analyzed)' }}

## Key Insights
{% if paper.insights %}{% for insight in paper.insights %}- {{ insight }}
{% endfor %}{% else %}- (Not yet analyzed)
{% endif %}
## My Notes
(Add your notes here)
```

`src/auto_reading/templates/weekly_digest.md`:
```
---
title: "Weekly Digest: {{ week }}"
date: {{ date }}
paper_count: {{ papers | length }}
---

# Weekly Digest: {{ week }}

## Top Papers by Relevance
{% for paper in papers | sort(attribute='relevance_score', reverse=True) %}
### {{ paper.title }} ({{ "%.2f" | format(paper.relevance_score) }})
- **Category:** {{ paper.category }}
- **Source:** [Link]({{ paper.source_url }})
- {{ paper.summary | default('No summary available') | truncate(200) }}
{% endfor %}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_writer.py`:
```python
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


def test_init_vault_creates_directories(writer: ObsidianWriter, vault_path: Path):
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
    from dataclasses import replace as dc_replace

    recategorized = dc_replace(sample_paper, category="tool-use")
    path2 = writer.write_paper(recategorized, force=True)
    assert path2 is not None
    assert "tool-use" in str(path2)
    assert not path1.exists()  # old file removed


def test_slug_generation(writer: ObsidianWriter):
    slug = writer._make_slug("CodeAgent: Autonomous Coding with LLMs!")
    assert slug == "codeagent-autonomous-coding-with-llms"
    assert " " not in slug
    assert "!" not in slug
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_writer.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 4: Write minimal implementation**

`src/auto_reading/writer.py`:
```python
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
        old_path = self._find_existing_note(filename, exclude_dir=category_dir)

        if filepath.exists() and not force:
            logger.info("Skipping existing note: %s", filepath)
            return None

        if old_path and not force:
            logger.info("Skipping existing note (different category): %s", old_path)
            return None

        # Preserve user notes from whichever existing file we find
        user_notes: str | None = None
        if filepath.exists():
            user_notes = self._extract_user_notes(filepath)
        elif old_path:
            user_notes = self._extract_user_notes(old_path)
            old_path.unlink()
            logger.info("Moved note from %s to %s", old_path.parent.name, paper.category)

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

    def _replace_notes_section(self, content: str, user_notes: str) -> str:
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_writer.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add src/auto_reading/writer.py src/auto_reading/templates/ tests/test_writer.py
git commit -m "feat: add Obsidian writer with vault init, templates, and force-sync"
```

---

## Chunk 4: CLI Integration

### Task 10: CLI Commands

**Files:**
- Create: `src/auto_reading/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from typer.testing import CliRunner

from auto_reading.cli import app

runner = CliRunner()


@pytest.fixture
def config_file(tmp_path):
    import yaml

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
    from auto_reading.db import PaperDB
    from auto_reading.models import Paper
    from datetime import date, datetime
    from dataclasses import replace as dc_replace
    from unittest.mock import patch, MagicMock

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

    with patch("auto_reading.cli.anthropic") as mock_anthropic:
        import json

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
        result = runner.invoke(
            app, ["analyze", "--retry-errors", "--config", str(config_file)]
        )
    assert result.exit_code == 0
    assert "1 analyzed" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

`src/auto_reading/cli.py`:
```python
"""CLI entry point for auto-reading."""

import asyncio
import logging
from pathlib import Path

import typer

from auto_reading import __version__
from auto_reading.config import load_config

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="auto-reading",
    help="LLM-driven paper tracking system for AI research.",
)

CONFIG_OPTION = typer.Option(
    "config.yaml", "--config", "-c", help="Path to config file"
)
VERBOSE_OPTION = typer.Option(False, "--verbose", "-v", help="Enable debug logging")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def version_callback(value: bool):
    if value:
        typer.echo(f"auto-reading {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=version_callback, is_eager=True
    ),
):
    """Auto-Reading: LLM-driven paper tracking for AI research."""


@app.command()
def fetch(
    source: str = typer.Argument(help="Source to fetch from: alphaarxiv, github"),
    topic: str = typer.Option(None, "--topic", "-t", help="Topic to search for"),
    days: int = typer.Option(None, "--days", "-d", help="Days to look back"),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Fetch papers from a source."""
    _setup_logging(verbose)
    cfg = load_config(config)
    days = days or cfg.fetch.default_days

    from auto_reading.db import PaperDB

    db = PaperDB(config.parent / "auto-reading.db")

    async def _fetch():
        papers = []
        if source == "alphaarxiv":
            from auto_reading.fetchers.alphaarxiv import AlphaRxivFetcher

            fetcher = AlphaRxivFetcher()
            topics = [topic] if topic else cfg.sources.alphaarxiv.topics
            papers = await fetcher.fetch(topics=topics, days=days)
        elif source == "github":
            from auto_reading.fetchers.github import GitHubFetcher

            fetcher = GitHubFetcher(
                tracked_repos=cfg.sources.github.tracked_repos,
            )
            topics = [topic] if topic else cfg.sources.github.topics
            papers = await fetcher.fetch(topics=topics, days=days)
        else:
            typer.echo(f"Unknown source: {source}", err=True)
            raise typer.Exit(1)

        new_count = 0
        for paper in papers[: cfg.fetch.max_papers_per_run]:
            if db.insert(paper):
                new_count += 1

        typer.echo(
            f"Fetched {len(papers)} papers, {new_count} new, "
            f"{len(papers) - new_count} duplicates skipped."
        )

    asyncio.run(_fetch())
    db.close()


@app.command()
def analyze(
    unprocessed: bool = typer.Option(
        False, "--unprocessed", help="Analyze all unprocessed papers"
    ),
    paper_id: str = typer.Option(None, "--paper", help="Analyze a specific paper by ID"),
    retry_errors: bool = typer.Option(
        False, "--retry-errors", help="Retry papers with error status"
    ),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Analyze papers with Claude."""
    _setup_logging(verbose)
    cfg = load_config(config)

    import anthropic

    from auto_reading.analyzer import Analyzer
    from auto_reading.db import PaperDB

    db = PaperDB(config.parent / "auto-reading.db")
    client = anthropic.Anthropic()
    analyzer = Analyzer(
        client=client, model=cfg.claude.model, categories=cfg.categories
    )

    if paper_id:
        papers = [p for p in [db.get(paper_id)] if p is not None]
    elif retry_errors:
        papers = db.list_by_status("error")
    elif unprocessed:
        papers = db.list_unprocessed()
    else:
        typer.echo("Specify --unprocessed, --paper <id>, or --retry-errors", err=True)
        raise typer.Exit(1)

    success = 0
    errors = 0
    for paper in papers:
        try:
            from dataclasses import replace as dc_replace

            result = analyzer.analyze(paper)
            updated = result.apply_to(paper)
            db.update(updated)
            success += 1
            typer.echo(f"  Analyzed: {paper.title[:60]}... → {result.category}")
        except Exception as e:
            errors += 1
            logger.error("Failed to analyze %s: %s", paper.id, e)
            db.update(dc_replace(paper, status="error"))

    typer.echo(f"Done: {success} analyzed, {errors} errors.")
    db.close()


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", help="Overwrite existing notes"),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Sync analyzed papers to Obsidian vault."""
    _setup_logging(verbose)
    cfg = load_config(config)

    from auto_reading.db import PaperDB
    from auto_reading.writer import ObsidianWriter

    db = PaperDB(config.parent / "auto-reading.db")
    writer = ObsidianWriter(
        vault_path=cfg.obsidian.vault_path, categories=cfg.categories
    )
    writer.init_vault()

    papers = db.list_analyzed()

    written = 0
    skipped = 0
    for paper in papers:
        path = writer.write_paper(paper, force=force)
        if path:
            written += 1
        else:
            skipped += 1

    typer.echo(f"Synced: {written} written, {skipped} skipped.")
    db.close()


@app.command()
def run(
    source: str = typer.Argument(help="Source to fetch from: alphaarxiv, github"),
    topic: str = typer.Option(None, "--topic", "-t", help="Topic to search for"),
    days: int = typer.Option(None, "--days", "-d", help="Days to look back"),
    config: Path = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """All-in-one: fetch → analyze → sync."""
    _setup_logging(verbose)
    fetch(source=source, topic=topic, days=days, config=config, verbose=verbose)
    analyze(unprocessed=True, paper_id=None, retry_errors=False, config=config, verbose=verbose)
    sync(force=False, config=config, verbose=verbose)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 5 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/auto_reading/cli.py tests/test_cli.py
git commit -m "feat: add CLI with fetch, analyze, sync, and run commands"
```

---

### Task 11: Coverage Check & Final Verification

- [ ] **Step 1: Run coverage**

Run: `uv run pytest --cov=auto_reading --cov-report=term-missing -v`
Expected: ≥80% coverage

- [ ] **Step 2: Manually test the full pipeline** (requires ANTHROPIC_API_KEY)

```bash
# Fetch from AlphaRxiv
uv run auto-reading fetch alphaarxiv --topic "coding agent" --days 7 --config config.yaml

# Analyze unprocessed
uv run auto-reading analyze --unprocessed --config config.yaml

# Sync to vault
uv run auto-reading sync --config config.yaml

# Check vault
ls -la ~/auto-reading-vault/papers/
```

- [ ] **Step 3: Fix any issues found during manual testing**

Adjust CSS selectors in AlphaRxiv fetcher based on actual site HTML structure.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: Phase 1 MVP complete — fetch, analyze, sync pipeline"
```
