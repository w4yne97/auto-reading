# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code Skills-based paper tracking and insight knowledge management system. All user interaction happens through Skills (`/start-my-day`, `/paper-search`, etc.) — there is no standalone CLI. Obsidian vault is the sole storage layer (no database).

## Architecture

Two layers share work:

- **SKILL.md files** (`.claude/skills/`) orchestrate workflows in natural language — Claude reads these and executes step by step
- **Python lib** (`lib/`) handles data fetching, scoring, and vault I/O — called by entry scripts that SKILL.md invokes via bash

Entry scripts live at `<skill-name>/scripts/*.py` and are always invoked from the project root:
```bash
python start-my-day/scripts/search_and_filter.py --config "$VAULT_PATH/00_Config/research_interests.yaml" --vault "$VAULT_PATH" --output /tmp/auto-reading/result.json
```

Scripts output JSON to `/tmp/auto-reading/`, which Claude then reads and processes (AI scoring, note generation, etc.).

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests
pytest

# Run single test file
pytest tests/test_scoring.py -v

# Run with coverage
pytest --cov=lib --cov-report=term-missing

# Run a specific entry script (example)
python start-my-day/scripts/search_and_filter.py --config config.example.yaml --vault /tmp/test-vault --output /tmp/auto-reading/result.json --verbose
```

## Key Design Decisions

- **alphaXiv primary source**: SSR JSON extracted via `json.JSONDecoder.raw_decode()` (not regex) from `alphaxiv.org/explore`. Falls back to arXiv API when unavailable.
- **Two-phase scoring**: Rule scoring (free, all papers) filters to Top 20, then Claude AI scores those 20 in-context. Final = rule * 0.6 + ai * 0.4.
- **Immutable data models**: `Paper` and `ScoredPaper` are frozen dataclasses. Never mutate — create new instances.
- **Vault as storage**: No database. Deduplication by scanning `20_Papers/` frontmatter `arxiv_id` fields. Tolerates missing/renamed fields from older notes.
- **Language**: Mixed — English for paper titles/abstracts, Chinese for analysis and insights.

## Scoring Weights (configurable in research_interests.yaml)

`keyword_match: 0.4, recency: 0.2, popularity: 0.3, category_match: 0.1`

## Testing

- **75 tests** covering lib/ (unit) and entry scripts (integration)
- Target: 80%+ coverage (currently 96%)
- CI: GitHub Actions runs on push/PR for Python 3.12 and 3.13

## Spec and Plan

- Design spec: `docs/superpowers/specs/2026-03-16-auto-reading-v2-design.md`
- Implementation plan: `docs/superpowers/plans/2026-03-16-auto-reading-v2-implementation.md`
- Reference code: `reference/evil-read-arxiv/` (arXiv XML parsing, vault scanning patterns)
