"""MCP server exposing the MBPP task's run_tests tool."""

import json
import sys
from typing import Literal

from mcp.server.fastmcp import FastMCP

from srcs.backends.local import LocalExecBackend
from srcs.mcp_server import tools
from srcs.mcp_server.task_file import find_task
from srcs.models import MBPPTaskInput

EVAL_SCRIPT_FILE = "_run_tests.py"

backend = LocalExecBackend(root="/tmp/agent")
# WARNING, not the SDK's INFO: over stdio this process shares the
# agent's stderr, and a line per tool call buries the agent's own output.
mcp = FastMCP("mbpp-tools", log_level="WARNING")
task: MBPPTaskInput


def _build_eval_script(code: str, test_list: list[str]) -> str:
    """Assemble the eval script: imports, the candidate `code`, then
    the given acceptance tests.

    Runs top to bottom; an assertion failure surfaces as a normal
    Python traceback on stderr with a non-zero exit code.
    """
    imports = "\n".join(task.test_imports)
    tests = "\n".join(test_list)
    return (
        f"{imports}\n"
        f"{code}\n"
        f"{tests}\n"
        "print('ALL TESTS PASSED')\n"
    )


@mcp.tool(
    description=(
        "Run a candidate solution against the given test assertions. "
        "Returns a JSON string with a `success` boolean (whether all "
        "assertions passed) and an `output` field (combined stdout/"
        "stderr)."
    )
)
def run_tests(code: str, test_list: list[str]) -> str:
    """Run `code` against `test_list` and report success as JSON."""
    backend.write_file(
        EVAL_SCRIPT_FILE, _build_eval_script(code, test_list),
    )
    cmd = f"{sys.executable} {EVAL_SCRIPT_FILE}"
    output = tools.run_tests(backend, cmd, workdir=str(backend.root))
    success = "ALL TESTS PASSED" in output
    return json.dumps({"success": success, "output": output})


def main() -> None:
    """Load the task and start serving (blocks until the client
    disconnects) kept out of module scope so importing this file
    never touches MBPP_TASK_FILE or starts the server."""
    global task
    with open(find_task("MBPP_TASK_FILE", "task_definition")) as f:
        task = MBPPTaskInput.model_validate_json(f.read())
    transport: Literal["stdio", "streamable-http"] = (
        "streamable-http" if "--http" in sys.argv else "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        print("Error:", e)
