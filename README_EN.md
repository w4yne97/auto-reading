# Auto-Reading

**English** | [中文](./README.md)

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skills-powered research paper tracking, insight knowledge management, and research idea generation system.

Discover papers from [alphaXiv](https://alphaxiv.org) and arXiv, score them with rule + AI hybrid ranking, generate structured notes in your Obsidian vault, build an evolving **topic -> sub-topic** insight knowledge graph, and mine research ideas from accumulated knowledge.

## How It Works

All interaction happens through Claude Code slash commands. There is no standalone CLI — Claude reads SKILL.md files and orchestrates Python scripts behind the scenes.

```
You ──► /start-my-day  ──► Claude fetches & scores papers ──► Daily note in vault
You ──► /paper-import  ──► Claude resolves & imports papers ──► Paper notes + insight linking
You ──► /insight-init  ──► Claude builds knowledge topic  ──► Evolving insight graph
You ──► /idea-generate ──► Claude analyzes gaps & crosses ──► Research idea notes
```

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.12+
- [Obsidian](https://obsidian.md) (for browsing generated notes)

## Install

```bash
git clone https://github.com/w4yne97/auto-reading.git
cd auto-reading
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## Quick Start

```bash
cd auto-reading && claude
```

### 1. Initialize

```
/reading-config
```

Claude walks you through setting up your vault path, research domains, keywords, and scoring weights.

### 2. Daily Papers

```
/start-my-day
```

Fetches trending papers from alphaXiv + arXiv, scores them (rule + AI), and generates a daily recommendation note.

### 3. Import Existing Papers

```
/paper-import 2406.12345 "https://arxiv.org/abs/1706.03762" "Attention Is All You Need" /path/to/paper.pdf
```

Batch import papers you've already read. Accepts arxiv IDs, URLs, titles, or PDFs. After import, choose to link them to insight topics.

### 4. Build Knowledge

```
/insight-init RL for Coding Agent
```

Create a knowledge topic, then grow it over time with `/insight-update`, `/insight-absorb`, and `/insight-connect`.

## Commands

### Paper Discovery

| Command | Description |
|---------|-------------|
| `/start-my-day [date]` | Daily recommendations (alphaXiv + arXiv -> score -> Top 10) |
| `/paper-search <keywords>` | Search arXiv by keywords |
| `/paper-analyze <arxiv_id>` | Deep analysis of a single paper |
| `/paper-import <items...>` | Batch import existing papers (IDs, URLs, titles, PDFs) |
| `/weekly-digest` | Weekly summary of the past 7 days |

### Insight Knowledge Graph

| Command | Description |
|---------|-------------|
| `/insight-init <topic>` | Create a new knowledge topic with sub-topics |
| `/insight-update <topic>` | Merge recent papers into a topic |
| `/insight-absorb <topic/sub-topic> <source>` | Deep-absorb a paper into a sub-topic |
| `/insight-review <topic>` | Review current state and open questions |
| `/insight-connect <topicA> [topicB]` | Discover cross-topic connections |

### Research Ideas

| Command | Description |
|---------|-------------|
| `/idea-generate` | Mine research opportunities from Insight knowledge (gaps + cross-pollination) |
| `/idea-generate --from-spark "desc"` | Deep-dive into a specific spark discovered in daily workflow |
| `/idea-develop <idea-name>` | Progress an idea (spark -> exploring -> validated) |
| `/idea-review` | Global dashboard: ranking, stale warnings, action suggestions |
| `/idea-review <idea-name>` | Single idea deep review: novelty, feasibility, completeness |

> `/start-my-day` and `/insight-update` automatically run lightweight Idea Spark checks — if a new paper could solve a known open question, a prompt appears at the end of the note.

### Configuration

| Command | Description |
|---------|-------------|
| `/reading-config` | View and modify research interest config |

## Vault Structure

```
obsidian-vault/
├── 00_Config/
│   └── research_interests.yaml     # Research domains, keywords, weights
├── 10_Daily/
│   └── 2026-03-17-paper-recs.md    # Daily recommendation
├── 20_Papers/
│   ├── coding-agent/               # Papers organized by domain
│   │   └── Paper-Title.md
│   └── rl-for-code/
├── 30_Insights/
│   └── RL-for-Coding-Agent/        # Insight knowledge topics
│       ├── _index.md               #   Topic overview + sub-topic list
│       ├── Algorithm-Selection.md   #   Sub-topic: method comparison
│       └── Reward-Design.md         #   Sub-topic: reward design
├── 40_Ideas/
│   ├── _dashboard.md               # Idea portfolio dashboard
│   ├── gap-reward-long-horizon.md   # Gap-sourced idea
│   └── cross-grpo-tool-use.md      # Cross-pollination idea
└── 40_Digests/
    └── 2026-W12-weekly-digest.md   # Weekly digest
```

## Scoring System

Two-phase scoring minimizes API cost while maximizing relevance.

**Phase 1 — Rule Scoring (free, all papers)**

| Dimension | Weight | How |
|-----------|--------|-----|
| Keyword match | 40% | Title (1.5x) + abstract (0.8x) keyword hits |
| Recency | 20% | 7d=10, 30d=7, 90d=4, older=1 |
| Popularity | 30% | alphaXiv votes + visits |
| Category match | 10% | arXiv category hit = 10, miss = 0 |

**Phase 2 — AI Scoring (Top 20 only)**

Claude evaluates research quality and relevance in-context. Final score = rule x 0.6 + AI x 0.4.

## Architecture

```
Claude Code (user interaction)
  │
  ▼
SKILL.md Orchestration (.claude/skills/)
  │ calls Python scripts
  ▼
Entry Scripts (<skill>/scripts/*.py)
  │ imports lib/
  ▼
Shared Library (lib/)
  ├── sources/alphaxiv.py   — alphaXiv trending extraction
  ├── sources/arxiv_api.py  — arXiv API search + batch fetch
  ├── resolver.py           — Input resolution (ID/URL/title/PDF)
  ├── scoring.py            — Rule-based scoring engine
  ├── vault.py              — Vault I/O, config, dedup, wikilinks
  └── models.py             — Paper, ScoredPaper (frozen dataclasses)
  │
  ▼
Obsidian Vault (Markdown + YAML frontmatter)
```

SKILL.md files are natural-language workflow definitions that Claude follows step by step. Python handles data fetching, scoring, and vault I/O. Claude handles AI analysis, note generation, and user interaction.

## Configuration

```yaml
vault_path: ~/obsidian-vault
language: "mixed"  # English titles, localized analysis

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation", "code repair"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5
  "rl-for-code":
    keywords: ["RLHF", "reinforcement learning", "reward model"]
    arxiv_categories: ["cs.LG", "cs.AI"]
    priority: 4

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

## Development

```bash
# Run all tests (130 tests, ~0.5s)
pytest

# With coverage (target: 80%, current: 96%)
pytest --cov=lib --cov-report=term-missing

# Single module
pytest tests/test_resolver.py -v
```

CI runs on every push/PR via GitHub Actions (Python 3.12 + 3.13).

## License

MIT
