"""Obsidian CLI wrapper -- single entry point for all vault operations."""

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_MACOS_DEFAULT = "/Applications/Obsidian.app/Contents/MacOS/obsidian"


class CLINotFoundError(Exception):
    """Obsidian CLI not installed or not in PATH."""


class ObsidianNotRunningError(Exception):
    """Obsidian app is not running (CLI requires it)."""


class ObsidianCLI:
    """Obsidian CLI wrapper. Single entry point for all vault operations.

    Immutable after __init__ -- vault_name, vault_path, and _cli_path
    are set once and never change.
    """

    def __init__(self, vault_name: str | None = None) -> None:
        self._vault_name = vault_name
        self._cli_path = self._find_cli()
        self._vault_path = self._resolve_vault_path()

    @property
    def vault_name(self) -> str | None:
        return self._vault_name

    @property
    def vault_path(self) -> str:
        return self._vault_path

    # -- Internal -----------------------------------------------------------

    @staticmethod
    def _find_cli() -> str:
        env_path = os.environ.get("OBSIDIAN_CLI_PATH")
        if env_path:
            if not Path(env_path).exists():
                raise CLINotFoundError(
                    f"OBSIDIAN_CLI_PATH points to non-existent path: {env_path}"
                )
            return env_path

        which_path = shutil.which("obsidian")
        if which_path:
            return which_path

        if Path(_MACOS_DEFAULT).exists():
            return _MACOS_DEFAULT

        raise CLINotFoundError(
            "Obsidian CLI not found. Install it via Obsidian Settings -> General -> "
            "Command line interface, then register to PATH."
        )

    def _resolve_vault_path(self) -> str:
        out = self._run("vault", "info=path")
        return out.strip()

    def _run(self, *args: str, timeout: int = 30) -> str:
        cmd = [self._cli_path, *args]
        if self._vault_name:
            cmd.append(f"vault={self._vault_name}")

        logger.debug("CLI: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Obsidian CLI timed out after {timeout}s: {' '.join(cmd)}"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "connect" in stderr.lower() or "ipc" in stderr.lower():
                raise ObsidianNotRunningError(
                    "Obsidian app must be running to use the CLI. "
                    "Please start Obsidian."
                )
            raise RuntimeError(f"Obsidian CLI error: {stderr}")

        return result.stdout
