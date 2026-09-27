"""MCP server exposing the SWE-bench task's tools."""

import os
import signal
import sys
from typing import Literal

from mcp.server.fastmcp import FastMCP

from srcs.backends.docker import DockerExecBackend
from srcs.mcp_server import tools
from srcs.mcp_server.task_file import find_task
from srcs.models import SWEBenchTaskInput

task: SWEBenchTaskInput
backend: DockerExecBackend

# WARNING, not the SDK's INFO: over stdio this process shares the
# agent's stderr, and a line per tool call buries the agent's own output.
mcp = FastMCP("swebench-tools", log_level="WARNING")


# --- Files tools ---

@mcp.tool()
def read_file(
        filepath: str, start_line: int = 1,
        end_line: int | None = None) -> str:
    """Read a file's content, cat -n style."""
    return tools.read_file(backend, filepath, start_line, end_line)


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace an exact string in a file with a new string."""
    return tools.edit_file(backend, filepath, old_str, new_str)


@mcp.tool()
def list_files(directory: str, pattern: str) -> str:
    """List files in a directory matching a glob pattern."""
    return tools.list_files(backend, directory, pattern)


# --- Search tools ---

@mcp.tool()
def search_code(pattern: str, file_pattern: str) -> str:
    """Perform a grep-like search in the codebase."""
    return tools.search_code(backend, pattern, file_pattern)


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    """Find the definition of a function or a class."""
    return tools.search_function_or_class_definition_in_code(
        backend, name,
    )


@mcp.tool()
def find_references(
        name: str, filepath: str | None = None,
        line: int | None = None) -> str:
    """Find all usages of a symbol (function or class)."""
    return tools.find_references(backend, name, filepath, line)


# --- Execute tools ---

@mcp.tool()
def run_tests() -> str:
    """Execute this instance's evaluation script."""
    return tools.run_tests(
        backend, task.eval_script, workdir=str(backend.root),
    )


@mcp.tool()
def get_patch() -> str:
    """Retrieve the unified git diff of all changes made so far."""
    return tools.get_patch(backend)


@mcp.tool()
def run_command(command: str, workdir: str) -> str:
    """Execute a shell command in the specified working directory."""
    return tools.run_command(backend, command, workdir)


def _handle_sigterm(signum: int, frame: object) -> None:
    """Turn SIGTERM into a normal interpreter shutdown, so the
    atexit-registered DockerExecBackend cleanup still runs instead
    of the container being left orphaned. The exam harness kills the
    agent's process tree with SIGTERM then SIGKILL on timeout — a
    raw SIGTERM has no default Python handler and would otherwise
    skip atexit entirely."""
    sys.exit(143)  # 128 + SIGTERM, conventional exit code


def main() -> None:
    """Load the task, pull/start the Docker backend, and start
    serving (blocks until the client disconnects) — kept out of
    module scope so importing this file never touches SWE_TASK_FILE
    or pulls/starts a container."""
    signal.signal(signal.SIGTERM, _handle_sigterm)

    global task, backend
    with open(find_task("SWE_TASK_FILE", "instance_id")) as f:
        task = SWEBenchTaskInput.model_validate_json(f.read())

    root = os.environ.get("TESTBED_PATH", "/testbed")
    backend = DockerExecBackend(task.docker_image, root=root)

    transport: Literal["stdio", "streamable-http"] = (
        "streamable-http" if "--http" in sys.argv else "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
