"""Configuration loading and validation."""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, field_validator

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

    try:
        return AppConfig(**raw)
    except ValidationError as e:
        # Re-raise as ValueError with full field paths for clearer errors
        paths = ", ".join(
            ".".join(str(p) for p in err["loc"]) for err in e.errors() if err["loc"]
        )
        raise ValueError(
            f"Invalid config — missing or invalid fields: {paths}"
        ) from e
