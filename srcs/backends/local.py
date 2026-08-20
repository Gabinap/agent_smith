"""Local (host) implementation of ExecBackend — no Docker involved.

Used as MBPP's permanent backend (MBPP never touches Docker), and as
a stand-in for DockerExecBackend while writing/testing the 9
mandatory tools before M6 lands (see split_work.md, M0 "doublures").
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from srcs.models import CommandResult


class LocalExecBackend:
    """Run commands and read/write files on the host, confined to root.

    Any path resolving outside `root` is refused.
    """

    def __init__(self, root: str) -> None:
        """Resolve `root` and create it on the host if missing."""
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def run(self, cmd: str, workdir: str, timeout: int) -> CommandResult:
        """Run a shell command and return its result."""
        try:
            cwd = self._resolve(workdir)
        except PermissionError as e:
            return CommandResult(stdout="", stderr=str(e), exit_code=1)
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            return CommandResult(
                stdout=e.stdout or "", stderr=e.stderr or "",
                exit_code=-1, timed_out=True,
            )
        except OSError as e:
            return CommandResult(stdout="", stderr=str(e), exit_code=1)
        return CommandResult(
            stdout=result.stdout, stderr=result.stderr,
            exit_code=result.returncode,
        )

    def read_file(self, path: str) -> str:
        """Return the raw text content of a file."""
        return self._resolve(path).read_text()

    def write_file(self, path: str, content: str) -> None:
        """Overwrite a file with the given content."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def _resolve(self, path: str) -> Path:
        """Resolve `path` (absolute or relative to root) and validate it.

        Refuses anything that escapes `root` (e.g. via `../..` or an
        unrelated absolute path).
        """
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.resolve()
        if not candidate.is_relative_to(self.root):
            raise PermissionError(
                f"path escapes backend root {self.root}: {path}"
            )
        return candidate
