# Auto-Reading: LLM-Driven Paper Tracking System

## Overview

An LLM/agent-driven system that automatically fetches, categorizes, summarizes, and extracts insights from academic papers and tech reports. Designed for an AI researcher focused on **Coding Agent**, NLP, and Agent research.

The system uses **Python** for core data processing and **Claude** for intelligent analysis, with **Obsidian** as the knowledge base frontend.

## Goals

1. Replace manual paper tracking (AlphaRxiv browsing, blog checking) with automated fetching
2. Categorize papers by research direction with Claude-powered classification
3. Generate structured summaries and extract cross-paper insights
4. Store everything in a searchable, browsable Obsidian vault
5. Evolve from on-demand CLI to fully automated pipeline

## Architecture

### Hybrid Architecture: Python Core + MCP Bridge

Two entry points sharing one set of core logic:

- **CLI (Phase 1)**: Direct command-line invocation for fetch/analyze/sync
- **MCP Server (Phase 2)**: Claude Code integration for natural language interaction

```
┌─────────────────────────────────────────────────┐
│                 Entrypoints                      │
│   ┌──────────┐    ┌──────────────┐              │
│   │ CLI      │    │ MCP Server   │  ← Phase 2   │
│   │ (typer)  │    │              │              │
│   └─────┬────┘    └──────┬───────┘              │
│         └────────┬───────┘                      │
│                  ▼                               │
│   ┌──────────────────────────┐                  │
│   │   Core Service Layer     │                  │
│   │  ┌────────┐ ┌─────────┐  │                  │
│   │  │Fetcher │ │Analyzer │  │                  │
│   │  └────┬───┘ └────┬────┘  │                  │
│   │       ▼          ▼       │                  │
│   │  ┌─────────────────────┐ │                  │
│   │  │  Paper Store (DB)   │ │                  │
│   │  └─────────┬───────────┘ │                  │
│   └────────────┼─────────────┘                  │
│                ▼                                 │
│   ┌──────────────────────────┐                  │
│   │  Obsidian Writer         │                  │
│   │  (Markdown generation)   │                  │
│   └──────────────────────────┘                  │
└─────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| **Fetcher** | Pull papers/projects from data sources, return unified data structures |
| **Analyzer** | Call Claude API for summarization, classification, scoring, insight extraction |
| **Paper Store** | SQLite storage for paper metadata, deduplication, search, reading status |
| **Obsidian Writer** | Generate Markdown files from templates, write to vault by category |

## Data Model

### Paper (Application Model)

```python
@dataclass(frozen=True)
class Paper:
    id: str                  # Source-prefixed ID (see Data Sources for format)
    title: str
    authors: list[str]
    abstract: str
    source: str              # "alphaarxiv" | "github"
    source_url: str
    published_at: date
    fetched_at: datetime
    tags: list[str]          # Claude-assigned, free-form but guided by config
    category: str            # Must be one of config.yaml categories
    status: str              # "unread" | "reading" | "read" | "archived"
    summary: str | None      # Claude-generated summary
    insights: list[str]      # Claude-extracted insights
    relevance_score: float   # 0-1, Claude-assessed relevance
```

### SQLite Schema

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,           -- e.g. "arxiv:2406.12345"
    title TEXT NOT NULL,
    authors TEXT NOT NULL,         -- JSON array: '["Author1", "Author2"]'
    abstract TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT NOT NULL,    -- ISO date
    fetched_at TEXT NOT NULL,      -- ISO datetime
    tags TEXT NOT NULL DEFAULT '[]',       -- JSON array
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    summary TEXT,
    insights TEXT NOT NULL DEFAULT '[]',   -- JSON array
    relevance_score REAL
);

CREATE INDEX idx_papers_source ON papers(source);
CREATE INDEX idx_papers_category ON papers(category);
CREATE INDEX idx_papers_status ON papers(status);
CREATE INDEX idx_papers_published ON papers(published_at);
```

List fields (`authors`, `tags`, `insights`) are stored as JSON arrays. SQLite's `json_each()` function enables queries like:
```sql
SELECT * FROM papers, json_each(papers.tags) WHERE json_each.value = 'coding-agent';
```

### Obsidian Vault Structure

```
auto-reading-vault/
├── papers/
│   ├── coding-agent/
│   │   ├── 2026-03-16-paper-title-slug.md
│   │   └── ...
│   ├── llm-reasoning/
│   │   └── ...
│   ├── code-generation/
│   │   └── ...
│   └── tool-use/
│       └── ...
├── digests/
│   ├── 2026-W11-weekly-digest.md
│   └── ...
├── insights/
│   ├── coding-agent-trends.md
│   └── ...
├── sources/
│   ├── alphaarxiv.md
│   └── github.md
└── templates/
    ├── paper-note.md
    └── weekly-digest.md
```

**Classification strategy:** Folder by primary category + multi-tag in frontmatter. Browse by folder, search by tag.

### Paper Note Template

```markdown
---
title: "Paper Title"
authors: [Author1, Author2]
source: alphaarxiv
url: https://arxiv.org/abs/xxxx
date: 2026-03-16
tags: [coding-agent, llm]
category: coding-agent
relevance: 0.92
status: unread
---

## Summary
(Claude-generated 2-3 paragraph summary)

## Key Insights
- Insight 1
- Insight 2

## My Notes
(Empty, for manual notes)
```

## Data Sources (MVP)

### AlphaRxiv

AlphaRxiv is a community-driven platform that surfaces trending arXiv papers. Integration approach:

- **Method**: Web scraping via httpx + HTML parsing (no official public API)
- **Target**: Trending/latest papers filtered by topic keywords
- **Fragility note**: As a scraping-based source, HTML structure changes may break the fetcher. The fetcher should be defensively coded with clear error messages on parse failures.
- **Fallback**: If AlphaRxiv proves unreliable, the arXiv API (`export.arxiv.org/api/query`) can serve as a direct replacement with keyword-based search
- **Rate limiting**: Respect `robots.txt`, add 1-2s delay between requests
- **Deduplication**: By arXiv ID (e.g., `2406.12345`)
- **ID format**: `arxiv:{arxiv_id}` (e.g., `arxiv:2406.12345`)

### GitHub

Two distinct sub-sources, both producing entries in the unified Paper model:

- **Trending repos**: Via unofficial GitHub trending endpoint or scraping `github.com/trending`. Captures emerging coding agent projects.
- **Release notes**: Via GitHub Releases API (`GET /repos/{owner}/{repo}/releases`). Tracks updates from key projects (e.g., aider, cursor, continue, opendevin, swe-agent).
- **Authentication**: GitHub personal access token (optional but recommended for rate limits)
- **Rate limiting**: 60 req/hr unauthenticated, 5000 req/hr with token
- **Deduplication**: By repo URL + release tag
- **ID format**: `github:{owner}/{repo}` for trending, `github:{owner}/{repo}:{tag}` for releases
- **Field mapping to Paper model**:
  - `title` → repo name or release title
  - `authors` → repo owner / contributors
  - `abstract` → repo description or release body (truncated)
  - `published_at` → repo creation date or release date
  - `source_url` → repo URL or release URL

## Core Flow

```
fetch              analyze                 sync
 │                   │                      │
 ▼                   ▼                      ▼
AlphaRxiv API  ──→  Dedup   ──→  Claude API  ──→  Generate Markdown
GitHub API         (SQLite)     · Summary          · Category subfolder
                                · Classify         · Frontmatter
                                · Score            · Write to vault
                                · Insights
```

### Key Design Decisions

1. **Deduplication**: Based on source-prefixed ID (see Data Sources); no duplicate fetching
2. **Classification by Claude**: Given a configurable category list, Claude selects primary category (must be from config list) + free-form tags (guided by topic context). Tags are descriptive labels Claude generates based on the content — no predefined tag vocabulary, but Claude is instructed to be consistent and reuse existing tags when applicable.
3. **Configurable categories**: Stored in `config.yaml`, user can add/remove at any time. If Claude cannot map a paper to any configured category, it assigns `"other"`.
4. **Incremental processing**: Only analyze newly fetched, unprocessed papers
5. **Abstract-only analysis (Phase 1)**: Claude works from title + abstract only. Full-text PDF processing is a potential Phase 3 enhancement requiring PDF extraction and chunking, which is out of scope for MVP.

## Analyzer: Prompt Design

Claude receives a single structured prompt per paper that produces all analysis outputs in one API call.

**Input**: Title + abstract + configured category list
**Output**: JSON with summary, category, tags, relevance_score, insights

```
System: You are a research paper analyst specializing in AI/ML.
Given a paper's title and abstract, produce a JSON analysis.

User:
## Paper
Title: {title}
Abstract: {abstract}

## Available Categories
{categories from config.yaml}

## Instructions
Analyze this paper and return JSON:
{
  "summary": "2-3 paragraph summary of key contributions and methods",
  "category": "one of the available categories, or 'other'",
  "tags": ["3-5 descriptive tags, reuse existing tags when applicable"],
  "relevance_score": 0.0-1.0,
  "insights": ["2-3 key takeaways or novel ideas"]
}

Relevance scoring guide:
- 0.8-1.0: Directly about coding agents, code generation with LLMs
- 0.5-0.8: Related (general LLM agents, tool use, code understanding)
- 0.2-0.5: Tangentially related (general NLP, ML infrastructure)
- 0.0-0.2: Minimal relevance to coding agents
```

**Cost estimation**: ~2K input tokens + ~1K output tokens per paper ≈ $0.01/paper (Sonnet). A batch of 50 papers ≈ $0.50. The `--limit` flag on CLI commands caps papers per run.

## Error Handling

- **Fetcher errors**: Log warning, skip the failing source, continue with others. Failed fetches do not write partial data to DB.
- **Claude API errors**: Retry up to 3 times with exponential backoff (1s, 4s, 16s). On persistent failure, mark paper as `status: "error"` in DB for later retry via `auto-reading analyze --retry-errors`.
- **Rate limits**: Respect source-specific rate limits. Claude API 429s trigger automatic backoff.
- **Sync errors**: If a Markdown file cannot be written (permission, disk full), log error and continue with remaining papers. Never leave a partially written file.
- **Partial batch failure**: Each paper is processed independently. One failure does not abort the batch.

## Sync Behavior

- **New paper** (no existing file): Create new Markdown file in the appropriate category subfolder
- **Existing paper** (file already exists): **Skip by default**. The `--force` flag overwrites generated sections (Summary, Key Insights) while preserving the "My Notes" section. This protects user-written content.
- **Deleted from DB**: No action. Orphaned Obsidian notes are left in place — the user may have added valuable notes.
- **Category changed**: On `--force` sync, the file is moved to the new category subfolder.

## Vault Initialization

On first `sync` run, the system automatically creates the vault directory structure if it doesn't exist:
- Creates `papers/`, `digests/`, `insights/`, `sources/` directories
- Creates category subdirectories under `papers/` based on `config.yaml`
- Does NOT create an Obsidian `.obsidian/` config folder — the user initializes Obsidian separately by opening the vault directory in the app

## CLI Interface (Phase 1)

```bash
# Fetch from a source
auto-reading fetch --source alphaarxiv --topic "coding agent" --days 7

# Analyze unprocessed papers
auto-reading analyze --unprocessed

# Sync to Obsidian vault
auto-reading sync --vault ~/auto-reading-vault

# All-in-one
auto-reading run --source alphaarxiv --topic "coding agent" --days 7
```

## Project Structure

```
auto-reading/
├── pyproject.toml
├── config.yaml
├── src/
│   └── auto_reading/
│       ├── __init__.py
│       ├── cli.py              # CLI entry (typer)
│       ├── config.py           # Config loading
│       ├── models.py           # Data models (dataclass)
│       ├── db.py               # SQLite operations
│       ├── fetchers/
│       │   ├── __init__.py
│       │   ├── base.py         # Fetcher abstract base class
│       │   ├── alphaarxiv.py   # AlphaRxiv fetching
│       │   └── github.py       # GitHub trending/releases
│       ├── analyzer.py         # Claude API summarization/classification
│       ├── writer.py           # Obsidian Markdown generation
│       └── templates/
│           ├── paper_note.md   # Jinja2 template
│           └── weekly_digest.md
├── tests/
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_db.py
│   ├── test_fetchers.py
│   ├── test_analyzer.py
│   └── test_writer.py
└── mcp_server/                 # Phase 2
    ├── __init__.py
    └── server.py
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Package manager | **uv** | Fast, modern Python package management |
| CLI framework | **typer** | Type-hint driven, code-as-docs |
| HTTP client | **httpx** | Async support, modern API |
| Database | **SQLite** (built-in) | Zero dependency, sufficient for local storage |
| LLM | **anthropic SDK** | Direct Claude API calls |
| Templating | **Jinja2** | Flexible Markdown generation |
| Config | **PyYAML + Pydantic** | config.yaml parsing + validation |
| Testing | **pytest** | Python standard |

## Evolution Roadmap

### Phase 1 — MVP: On-Demand CLI

- Fetch: AlphaRxiv + GitHub
- Analyze: Claude API for summary, classification, scoring
- Sync: Write to Obsidian vault (category subfolders + tags)
- CLI-triggered, manual review

### Phase 2 — Conversational Interaction

- MCP Server wrapping core logic
- Claude Code integration for natural language queries
- Cross-paper insight aggregation and comparison
- "What's new in coding agent this week?"

### Phase 3 — Full Automation

- Cron-based scheduled fetching (daily/weekly)
- Auto-generated weekly digests in `digests/`
- High-relevance paper push notifications (optional)
- Trend analysis: topic heat changes, key author tracking

Each phase is independently usable — Phase 1 alone solves the manual tracking pain point.

## Configuration (config.yaml)

Configuration is validated at startup using **Pydantic**. Missing required fields cause a clear error message. Optional fields have sensible defaults.

```yaml
# Required
obsidian:
  vault_path: ~/auto-reading-vault    # Required, no default

# Optional with defaults
sources:
  alphaarxiv:
    enabled: true                      # default: true
    topics: ["coding agent", "code generation", "llm agent"]
  github:
    enabled: true                      # default: true
    topics: ["coding-agent", "ai-coding"]
    tracked_repos:                     # repos to watch for releases
      - "paul-gauthier/aider"
      - "OpenDevin/OpenDevin"
      - "princeton-nlp/SWE-agent"

categories:                            # default: list below
  - coding-agent
  - llm-reasoning
  - code-generation
  - tool-use
  - evaluation
  - infrastructure

claude:
  model: claude-sonnet-4-6            # default: claude-sonnet-4-6
  max_tokens: 4096                     # default: 4096

fetch:
  default_days: 7                      # default lookback window
  max_papers_per_run: 50               # cost safety cap
```

### Config Validation Rules

- `obsidian.vault_path`: Required. Must be a valid writable path (expanded from `~`).
- `categories`: At least one category must be defined.
- `claude.model`: Must be a valid Anthropic model ID.
- `fetch.max_papers_per_run`: Must be > 0. Caps Claude API costs per invocation.

## Logging

All modules log to stderr via Python `logging` at INFO level by default. `--verbose` flag switches to DEBUG. Log format:

```
2026-03-16 10:30:00 [INFO] fetcher.alphaarxiv: Fetched 23 papers for topic "coding agent"
2026-03-16 10:30:01 [INFO] db: 5 new papers, 18 duplicates skipped
2026-03-16 10:30:05 [WARN] analyzer: Claude API rate limited, retrying in 4s (attempt 2/3)
```
