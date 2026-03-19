# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code Skills-based paper tracking and insight knowledge management system. All user interaction happens through Skills (`/start-my-day`, `/paper-search`, etc.) — there is no standalone CLI. Obsidian vault is the sole storage layer (no database).

## Vault Configuration

Obsidian vault operations use the **Obsidian CLI** (hard dependency — requires Obsidian app running):
- **Python scripts**: Use `ObsidianCLI` from `lib/obsidian_cli.py` — CLI knows the vault path automatically
- **Skills**: Still use `$VAULT_PATH` environment variable for direct file I/O via Claude Code tools
- **CLI path discovery**: `OBSIDIAN_CLI_PATH` env var → `which obsidian` → macOS default path
- **Multi-vault**: Set `OBSIDIAN_VAULT_NAME` env var to target a specific vault

Vault structure: `00_Config/`, `10_Daily/`, `20_Papers/<domain>/`, `30_Insights/<topic>/`, `40_Ideas/`

## Architecture

Three layers share work:

- **SKILL.md files** (`.claude/skills/`) orchestrate workflows in natural language — Claude reads these and executes step by step
- **Python lib** (`lib/`) handles data fetching, scoring, and vault I/O — called by entry scripts that SKILL.md invokes via bash
- **Obsidian CLI wrapper** (`lib/obsidian_cli.py`) wraps all Obsidian CLI commands as typed Python methods — `lib/vault.py` calls this, never `subprocess` directly

```
Skills (.claude/skills/)
  │  bash invocation
  ▼
Entry Scripts (start-my-day/scripts/, paper-import/scripts/, ...)
  │  import
  ▼
lib/vault.py          ← Business logic (scan, dedup, write, search)
  │  import
  ▼
lib/obsidian_cli.py   ← CLI wrapper (subprocess, JSON parsing)
  │  subprocess
  ▼
Obsidian CLI → Vault filesystem
```

Entry scripts live at `<skill-name>/scripts/*.py` and are always invoked from the project root:
```bash
python start-my-day/scripts/search_and_filter.py --config "$VAULT_PATH/00_Config/research_interests.yaml" --output /tmp/auto-reading/result.json
```

Scripts output JSON to `/tmp/auto-reading/`, which Claude then reads and processes (AI scoring, note generation, etc.).

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests (excludes integration tests)
pytest

# Run single test file
pytest tests/test_scoring.py -v

# Run with coverage
pytest --cov=lib --cov-report=term-missing

# Run integration tests (requires Obsidian running)
pytest -m integration -v

# Run a specific entry script (example)
python start-my-day/scripts/search_and_filter.py --config "$VAULT_PATH/00_Config/research_interests.yaml" --output /tmp/auto-reading/result.json --verbose
```

## Key Design Decisions

- **Obsidian CLI as sole vault interface**: All vault operations go through `lib/obsidian_cli.py` → Obsidian CLI. No direct filesystem access for vault I/O. Hard dependency — no fallback.
- **alphaXiv primary source**: Papers extracted via regex from TanStack Router SSR-embedded data in `alphaxiv.org/explore`. Falls back to arXiv API when unavailable.
- **Two-phase scoring**: Rule scoring (free, all papers) filters to Top 20, then Claude AI scores those 20 in-context. Final = rule * 0.6 + ai * 0.4.
- **Immutable data models**: `Paper` and `ScoredPaper` are frozen dataclasses. Never mutate — create new instances.
- **Vault as storage**: No database. Deduplication via CLI search + property reads on `20_Papers/` `arxiv_id` fields.
- **Language**: Mixed — English for paper titles/abstracts, Chinese for analysis and insights.

## Scoring Weights (configurable in research_interests.yaml)

`keyword_match: 0.4, recency: 0.2, popularity: 0.3, category_match: 0.1`

## Testing

- **170+ tests** covering lib/ (unit) and entry scripts (integration)
- **11 integration tests** requiring real Obsidian CLI (`pytest -m integration`)
- Target: 80%+ coverage

## Spec and Plan

- Design spec: `docs/superpowers/specs/2026-03-16-auto-reading-v2-design.md`
- Implementation plan: `docs/superpowers/plans/2026-03-16-auto-reading-v2-implementation.md`
- Idea system spec: `docs/superpowers/specs/2026-03-18-idea-system-design.md`
- Idea system plan: `docs/superpowers/plans/2026-03-18-idea-system-implementation.md`
- Obsidian CLI integration spec: `docs/superpowers/specs/2026-03-19-obsidian-cli-integration-design.md`
- Obsidian CLI integration plan: `docs/superpowers/plans/2026-03-19-obsidian-cli-integration-implementation.md`
