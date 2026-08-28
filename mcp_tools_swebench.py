"""MCP server exposing the SWE-bench task's tools."""

import os
import sys

from mcp.server.mcpserver import MCPServer

from srcs.backends.docker import DockerExecBackend
from srcs.mcp_server import tools
from srcs.models import SWEBenchTaskInput

task: SWEBenchTaskInput
backend: DockerExecBackend

mcp = MCPServer("swebench-tools")


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


def main() -> None:
    """Load the task, pull/start the Docker backend, and start
    serving (blocks until the client disconnects) — kept out of
    module scope so importing this file never touches SWE_TASK_FILE
    or pulls/starts a container."""
    global task, backend
    with open(os.environ["SWE_TASK_FILE"]) as f:
        task = SWEBenchTaskInput.model_validate_json(f.read())

    # /testbed is SWE-bench's conventional checkout path inside the
    # image — the repo is already there, pre-baked at the buggy
    # commit. Also matches SandboxConfig.allowed_directories' default.
    backend = DockerExecBackend(task.docker_image, root="/testbed")

    transport = "streamable-http" if "--http" in sys.argv else "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
