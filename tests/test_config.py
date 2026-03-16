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
    config_file.write_text(yaml.dump({"obsidian": {"vault_path": str(tmp_path / "vault")}, "categories": ["coding-agent", "tool-use"]}))
    config = load_config(config_file)
    assert config.obsidian.vault_path == tmp_path / "vault"
    assert "coding-agent" in config.categories


def test_config_defaults(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"obsidian": {"vault_path": str(tmp_path / "vault")}}))
    config = load_config(config_file)
    assert config.claude.model == "claude-sonnet-4-6"
    assert config.claude.max_tokens == 4096
    assert config.fetch.default_days == 7
    assert config.fetch.max_papers_per_run == 50
    assert config.sources.alphaarxiv.enabled is True


def test_config_missing_vault_path(tmp_path):
    config_file = tmp_path / "config.yaml"
    # Missing obsidian section entirely
    config_file.write_text(yaml.dump({"categories": ["coding-agent"]}))
    with pytest.raises(ValueError, match="obsidian"):
        load_config(config_file)


def test_config_missing_vault_path_in_obsidian(tmp_path):
    config_file = tmp_path / "config.yaml"
    # obsidian section present but vault_path missing
    config_file.write_text(yaml.dump({"obsidian": {}, "categories": ["coding-agent"]}))
    with pytest.raises(ValueError, match="vault_path"):
        load_config(config_file)


def test_config_empty_categories(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"obsidian": {"vault_path": str(tmp_path / "vault")}, "categories": []}))
    with pytest.raises(ValueError, match="categories"):
        load_config(config_file)


def test_config_max_papers_must_be_positive(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"obsidian": {"vault_path": str(tmp_path / "vault")}, "fetch": {"max_papers_per_run": 0}}))
    with pytest.raises(ValueError, match="max_papers_per_run"):
        load_config(config_file)


def test_config_expands_tilde(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"obsidian": {"vault_path": "~/my-vault"}}))
    config = load_config(config_file)
    assert "~" not in str(config.obsidian.vault_path)


def test_config_file_not_found():
    from pathlib import Path
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))
