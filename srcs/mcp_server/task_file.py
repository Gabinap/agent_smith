"""Find the task file an MCP server should serve.

The agents hand it over through the environment. The sandbox CLI does
not: `uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py"` is one of
the commands the subject gives, and it carries no task. Falling back to
cache/ makes that command work instead of dying on a KeyError before
the server has even started.
"""

import json
import os
import pathlib

from srcs.paths import CACHE


def find_task(env_var: str, marker: str) -> pathlib.Path:
    """Return the task file to serve: the env var, else one in cache/.

    `marker` is the field that identifies the benchmark — `task_id`
    for MBPP, `instance_id` for SWE-bench — so a cache holding both
    kinds still hands each server its own. Matching on content rather
    than on a filename means a task keeps working whatever it is
    called.
    """
    configured = os.environ.get(env_var)
    if configured:
        path = pathlib.Path(configured)
        if not path.is_file():
            raise SystemExit(f"{env_var} points at a missing file: {path}")
        return path

    for candidate in sorted(CACHE.glob("*.json")):
        try:
            content = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(content, dict) and marker in content:
            return candidate

    raise SystemExit(
        f"no task to serve: set {env_var}, or dump one into {CACHE} "
        f"(the file must carry a {marker!r} field)")
