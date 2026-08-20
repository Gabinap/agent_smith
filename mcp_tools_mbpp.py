import os
import sys

from mcp.server.mcpserver import MCPServer

from srcs.backends.local import LocalExecBackend
from srcs.mcp_server import tools
from srcs.models import MBPPTaskInput

# Contract with the (not yet built) MBPP agent / M8.a: MBPP_TASK_FILE
# must be set, and the LLM writes its own solution to SOLUTION_FILE
# itself (direct sandboxed I/O) — run_tests() only reads what's there.
SOLUTION_FILE = "solution.py"
EVAL_SCRIPT_FILE = "_run_tests.py"

backend = LocalExecBackend(root="/tmp/agent")

with open(os.environ["MBPP_TASK_FILE"]) as f:
    task = MBPPTaskInput.model_validate_json(f.read())

mcp = MCPServer("mbpp-tools")


def _build_eval_script() -> str:
    """Assemble one script: task imports + current solution.py +
    the task's acceptance tests, run top to bottom. An assertion
    failure or missing solution.py surfaces as a normal Python
    traceback on stderr with a non-zero exit code."""
    imports = "\n".join(task.test_imports)
    tests = "\n".join(task.test_list)
    return (
        f"{imports}\n"
        f"exec(open({SOLUTION_FILE!r}).read())\n"
        f"{tests}\n"
        "print('ALL TESTS PASSED')\n"
    )


@mcp.tool(
    description=(
        f"Run the MBPP acceptance tests against {SOLUTION_FILE} "
        "(write your candidate function there yourself first, e.g. "
        "via open()). Returns \"ALL TESTS PASSED\" on success, or a "
        "Python traceback pointing at the failing assertion otherwise."
    )
)
def run_tests() -> str:
    """MCP-facing text is set via description= above (references
    SOLUTION_FILE directly, stays in sync if it's ever renamed)."""
    backend.write_file(EVAL_SCRIPT_FILE, _build_eval_script())
    cmd = f"{sys.executable} {EVAL_SCRIPT_FILE}"
    return tools.run_tests(backend, cmd, workdir=str(backend.root))


transport = "streamable-http" if "--http" in sys.argv else "stdio"
mcp.run(transport=transport)
