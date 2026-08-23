from rich.console import Console, Group
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from models.sandbox import SandboxResult


def display_sandbox(console: Console, sandbox_data: SandboxResult, py_code: str):
    msg_error = "No Errors" if sandbox_data.error is None else sandbox_data.error
    py_code = "No Python code" if py_code is None else py_code
    sandbox_data.final_answer = "No final anwer" if sandbox_data.final_answer is None else sandbox_data.final_answer
    sandbox_cli = Group(
        Text("Input:", style="bold white", end="\n\n"),
        Syntax(py_code, "python", theme="stata-dark"),
        Text("\nOutput:", style="bold white", end="\n\n"),
        Syntax(sandbox_data.output, "python", theme="stata-dark"),
        Text("\nErrors:", style="bold white", end="\n\n"),
        Syntax(msg_error, "python", theme="stata-dark"),
        Text("\nFinal result:", style="bold white", end="\n\n"),
        Syntax(sandbox_data.final_answer, "python", theme="stata-dark", line_numbers=True),
    )
    console.print(Panel(sandbox_cli, title="[bold orange1]SANDBOX output", border_style="orange1"))
