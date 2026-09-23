from models.sandbox import SandboxResult
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def display_sandbox(console: Console, sandbox_data: SandboxResult,
                    py_code: str) -> None:
    msg_error = ("No Errors" if sandbox_data.error is None
                 else sandbox_data.error)
    py_code = "No Python code" if py_code is None else py_code
    final_answer = sandbox_data.final_answer or "No final answer"
    sandbox_cli = Group(
        Text("Input:", style="bold white", end="\n\n"),
        Syntax(py_code, "python", theme="stata-dark"),
        Text("\nOutput:", style="bold white", end="\n\n"),
        Syntax(sandbox_data.output, "python", theme="stata-dark"),
        Text("\nErrors:", style="bold white", end="\n\n"),
        Syntax(msg_error, "python", theme="stata-dark"),
        Text("\nFinal result:", style="bold white", end="\n\n"),
        Syntax(final_answer, "python", theme="stata-dark",
               line_numbers=True),
    )
    console.print(Panel(sandbox_cli, title="[bold orange1]SANDBOX output",
                        border_style="orange1"))


def display_sandbox_tests(console: Console, output: str,
                          result: str) -> None:

    sandbox_cli = Group(
        Text("\nOutput:", style="bold white", end="\n\n"),
        Syntax(output, "python", theme="stata-dark"),
        Text("\nResult:", style="bold white", end="\n\n"),
        Syntax(result, "python", theme="stata-dark"),
    )
    console.print(Panel(sandbox_cli,
                        title="[bold orange_red1]SANDBOX Run tests",
                        border_style="orange_red1"))
