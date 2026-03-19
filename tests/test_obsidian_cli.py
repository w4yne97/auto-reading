"""Tests for ObsidianCLI wrapper."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from lib.obsidian_cli import (
    ObsidianCLI,
    CLINotFoundError,
    ObsidianNotRunningError,
)


class TestCLIDiscovery:
    def test_finds_cli_from_env_var(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/custom/obsidian"}), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/custom/obsidian"

    def test_finds_cli_from_which(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value="/usr/local/bin/obsidian"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/usr/local/bin/obsidian"

    def test_finds_cli_macos_default(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert "Obsidian.app" in cli._cli_path

    def test_raises_cli_not_found(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(CLINotFoundError):
                ObsidianCLI()


class TestRun:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_run_builds_command(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("search", "query=test", timeout=30)
            args = mock_run.call_args[0][0]
            assert args == ["/usr/bin/obsidian", "search", "query=test"]

    def test_run_with_vault_name(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI(vault_name="my-vault")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("files")
            args = mock_run.call_args[0][0]
            assert "vault=my-vault" in args

    def test_run_timeout_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["obsidian"], timeout=30
            )
            with pytest.raises(TimeoutError):
                cli._run("search", "query=slow")

    def test_run_nonzero_exit_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: file not found"
            )
            with pytest.raises(RuntimeError, match="file not found"):
                cli._run("read", 'path="missing.md"')

    def test_run_obsidian_not_running_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: connect ECONNREFUSED"
            )
            with pytest.raises(ObsidianNotRunningError):
                cli._run("vault")
