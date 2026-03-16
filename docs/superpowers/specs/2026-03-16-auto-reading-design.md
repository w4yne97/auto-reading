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

### Paper (SQLite)

```python
Paper:
  id: str                  # arXiv ID or unique hash
  title: str
  authors: list[str]
  abstract: str
  source: str              # "alphaarxiv" | "github" | ...
  source_url: str
  published_at: date
  fetched_at: datetime
  tags: list[str]          # ["coding-agent", "code-generation", ...]
  category: str            # primary category (folder name)
  status: str              # "unread" | "reading" | "read" | "archived"
  summary: str | None      # Claude-generated summary
  insights: list[str]      # Claude-extracted insights
  relevance_score: float   # 0-1, Claude-assessed relevance
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
category: core
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
- API-based fetching of trending/latest papers
- Filter by topic keywords (coding agent, code generation, etc.)
- Deduplication by arXiv ID

### GitHub
- Trending repositories in relevant topics
- Release notes from key projects (e.g., aider, cursor, continue, etc.)
- Deduplication by repo URL + version

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

1. **Deduplication**: Based on arXiv ID or URL hash; no duplicate fetching
2. **Classification by Claude**: Given a configurable category list, Claude selects primary category + multiple tags from abstract
3. **Configurable categories**: Stored in `config.yaml`, user can add/remove at any time
4. **Incremental processing**: Only analyze newly fetched, unprocessed papers

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
| Config | **PyYAML** | config.yaml parsing |
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

```yaml
sources:
  alphaarxiv:
    enabled: true
    topics: ["coding agent", "code generation", "llm agent"]
  github:
    enabled: true
    topics: ["coding-agent", "ai-coding"]

categories:
  - coding-agent
  - llm-reasoning
  - code-generation
  - tool-use
  - evaluation
  - infrastructure

obsidian:
  vault_path: ~/auto-reading-vault

claude:
  model: claude-sonnet-4-6
  max_tokens: 4096
```
