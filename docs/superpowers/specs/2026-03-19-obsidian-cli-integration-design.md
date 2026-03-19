# Obsidian CLI Integration Design

## Context

The auto-reading system currently interacts with the Obsidian vault through direct filesystem operations (`pathlib`). `lib/vault.py` uses `rglob`, regex-based frontmatter parsing, and `Path.write_text()` for all vault I/O.

Obsidian now provides an official CLI (`obsidian.md/cli`) that exposes the full Obsidian feature set from the command line — including indexed search, property read/write, backlinks, and link graph queries. These capabilities exceed what raw filesystem access can offer.

This design replaces all filesystem-based vault operations with Obsidian CLI calls, and restructures the codebase to fully leverage CLI-native capabilities.

## Goals

1. Replace all direct filesystem vault operations with Obsidian CLI calls
2. Leverage CLI-native capabilities (indexed search, backlinks, property atomics) that were previously unavailable
3. Clean architecture: two-layer separation (CLI wrapper → business logic)
4. Maintain 80%+ test coverage with mock-based testing

## Non-Goals

- Backward compatibility / fallback to filesystem when CLI is unavailable (hard dependency)
- Obsidian plugin development
- Changing the JSON intermediate file mechanism between scripts and Skills

## Architecture

### Module Dependency Graph

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
Obsidian CLI (/Applications/Obsidian.app/Contents/MacOS/obsidian)
  │  in-memory index
  ▼
Vault filesystem (~/Documents/auto-reading-vault/)
```

### Layer 1: `lib/obsidian_cli.py` — CLI Wrapper

A low-level module that wraps all Obsidian CLI commands as typed Python methods. Upper layers never call `subprocess` directly.

```python
class ObsidianCLI:
    """Obsidian CLI wrapper. Single entry point for all vault operations."""

    def __init__(self, vault_name: str | None = None):
        """vault_name: CLI vault= parameter. None uses default vault."""

    # --- File operations ---
    def create_note(self, path: str, content: str, overwrite: bool = False) -> str
    def read_note(self, path: str) -> str
    def delete_note(self, path: str, permanent: bool = False) -> None

    # --- Property operations ---
    def get_property(self, path: str, name: str) -> str | None
    def set_property(self, path: str, name: str, value: str,
                     type: str = "text") -> None

    # --- Search ---
    def search(self, query: str, path: str | None = None,
               limit: int | None = None) -> list[str]
    def search_context(self, query: str, path: str | None = None,
                       limit: int | None = None) -> list[dict]

    # --- Link graph ---
    def backlinks(self, path: str) -> list[str]
    def outgoing_links(self, path: str) -> list[str]
    def unresolved_links(self) -> list[dict]

    # --- File listing ---
    def list_files(self, folder: str | None = None,
                   ext: str | None = None) -> list[str]
    def file_count(self, folder: str | None = None,
                   ext: str | None = None) -> int

    # --- Tags ---
    def tags(self, path: str | None = None) -> list[dict]

    # --- Vault info ---
    def vault_info(self) -> dict

    # --- Internal ---
    def _run(self, *args: str) -> str
```

**Design decisions:**

- Stateless after `__init__` — `vault_name` is immutable
- All JSON output from CLI is parsed in this layer
- `_run()` handles subprocess invocation, timeout (30s default, 60s for search), stderr parsing, and error translation

### Layer 2: `lib/vault.py` — Business Logic (Rewritten)

All functions take an `ObsidianCLI` instance instead of `Path`. Function signatures change to match CLI capabilities.

```python
def create_cli(vault_name: str | None = None) -> ObsidianCLI
def load_config(cli: ObsidianCLI, config_path: str) -> dict
def scan_papers(cli: ObsidianCLI) -> list[dict]
def build_dedup_set(cli: ObsidianCLI) -> set[str]
def write_paper_note(cli: ObsidianCLI, path: str, content: str) -> str
def get_paper_status(cli: ObsidianCLI, path: str) -> str
def set_paper_status(cli: ObsidianCLI, path: str, status: str) -> None

# New capabilities (CLI-native)
def get_paper_backlinks(cli: ObsidianCLI, path: str) -> list[str]
def get_paper_links(cli: ObsidianCLI, path: str) -> list[str]
def search_papers(cli: ObsidianCLI, query: str, limit: int = 20) -> list[dict]
def get_unresolved_links(cli: ObsidianCLI) -> list[dict]
```

**Signature changes:**

| Old | New | Reason |
|-----|-----|--------|
| `scan_papers(vault_path: Path)` | `scan_papers(cli: ObsidianCLI)` | CLI knows vault location |
| `build_dedup_set(scan_results)` | `build_dedup_set(cli: ObsidianCLI)` | Direct query, no intermediate |
| `write_note(vault_path, relative_path, content)` | `write_paper_note(cli, path, content)` | No vault_path needed |
| `load_config(config_path)` | `load_config(cli, config_path)` | config_path is vault-relative |

**Deleted code:**

- `_FRONTMATTER_RE` regex
- `parse_frontmatter()` — replaced by `cli.get_property()`
- `generate_wikilinks()` and `_replace_keywords()` — replaced by link graph strategy (see below)
- `parse_date_field()` — retained as pure utility

## Wikilink Strategy Change

The current `generate_wikilinks()` does regex-based keyword replacement. This is replaced by a Claude-native approach:

1. Skills inject available Insight note names (from `cli.list_files(folder="30_Insights")`) into Claude's prompt
2. Claude generates markdown with `[[wikilinks]]` inline, using contextual understanding to decide which concepts to link
3. After note creation, `cli.unresolved_links()` can surface broken links for review

This eliminates the keyword index maintenance and produces more accurate links.

## Entry Scripts Changes

All entry scripts change from `--vault /path` to `--vault-name name` (optional).

```bash
# Old
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --vault "$VAULT_PATH" --output /tmp/auto-reading/result.json

# New
python start-my-day/scripts/search_and_filter.py \
  --config "00_Config/research_interests.yaml" \
  --output /tmp/auto-reading/result.json
```

**Per-script changes:**

| Script | Changes |
|--------|---------|
| `start-my-day/scripts/search_and_filter.py` | Args + dedup via `build_dedup_set(cli)` |
| `paper-analyze/scripts/generate_note.py` | Args only (arXiv fetch unchanged) |
| `paper-import/scripts/resolve_and_fetch.py` | Args + dedup + write via CLI |
| `weekly-digest/scripts/generate_digest.py` | Args + scan via CLI |
| `insight-update/scripts/scan_recent_papers.py` | Args + scan via CLI |

Skills (`.claude/skills/*.md`) update bash invocations to new parameter format.

## Error Handling

### Custom Exceptions

```python
class CLINotFoundError(Exception):
    """Obsidian CLI not installed or not in PATH"""

class ObsidianNotRunningError(Exception):
    """Obsidian app is not running (CLI requires it)"""
```

### CLI Path Discovery

Priority order:
1. `OBSIDIAN_CLI_PATH` environment variable (override)
2. `which obsidian` (in PATH)
3. `/Applications/Obsidian.app/Contents/MacOS/obsidian` (macOS default)

If none found → `CLINotFoundError` with install instructions.

### Edge Cases

| Scenario | Handling |
|----------|----------|
| File not found | `get_property` returns None, `read_note` raises |
| Property missing | `get_property` returns None |
| Search no results | Returns `[]` |
| Wrong vault name | `__init__` detects, raises `ValueError` |
| Filenames with spaces/CJK | `_run` correctly quotes args |
| `create_note` target exists | Raises by default, `overwrite=True` to replace |
| Concurrent writes | CLI serializes through Obsidian process |

## Testing Strategy

### Layer 1: CLI Wrapper Unit Tests (mock subprocess)

```python
# tests/test_obsidian_cli.py
# Verify command construction and output parsing

def test_search_builds_correct_command(mock_run): ...
def test_search_parses_json_output(mock_run): ...
def test_get_property_returns_none_on_missing(mock_run): ...
def test_cli_not_found_raises(mock_which): ...
```

### Layer 2: Business Logic Tests (mock ObsidianCLI)

```python
# tests/test_vault.py
# Verify business logic with mocked CLI

def test_build_dedup_set(mock_cli): ...
def test_scan_papers_skips_without_arxiv_id(mock_cli): ...
def test_write_paper_note_returns_path(mock_cli): ...
```

### Layer 3: Integration Tests (optional, real CLI)

```python
# tests/integration/test_cli_integration.py
@pytest.mark.integration
def test_real_vault_search(): ...
```

**Old tests:** All tests in `tests/test_vault.py` touching `parse_frontmatter`, `scan_papers`, `generate_wikilinks` are rewritten. Tests for `lib/scoring.py` and other non-vault modules are unaffected.

**Coverage target:** 80%+ maintained.

## File Change Summary

### New Files

- `lib/obsidian_cli.py` (~200-300 lines)
- `tests/test_obsidian_cli.py`
- `tests/integration/test_cli_integration.py`

### Rewritten Files

- `lib/vault.py`
- `tests/test_vault.py`

### Modified Files

- `start-my-day/scripts/search_and_filter.py`
- `paper-analyze/scripts/generate_note.py`
- `paper-import/scripts/resolve_and_fetch.py`
- `weekly-digest/scripts/generate_digest.py`
- `insight-update/scripts/scan_recent_papers.py`
- `.claude/skills/*.md` (bash invocation params)
- `CLAUDE.md` (architecture docs)

### Unchanged

- `lib/scoring.py`, `lib/models.py`, `lib/arxiv_client.py`, `lib/alphaxiv_client.py`
- JSON intermediate file mechanism (`/tmp/auto-reading/`)
- Scoring weights and two-phase scoring logic

## Environment Variable Changes

| Old | New | Notes |
|-----|-----|-------|
| `VAULT_PATH` (required) | Removed | CLI knows vault path |
| — | `OBSIDIAN_CLI_PATH` (optional) | Override CLI path discovery |
| — | `OBSIDIAN_VAULT_NAME` (optional) | Select vault in multi-vault setups |
