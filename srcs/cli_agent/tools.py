from rich.console import Console, Group
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from models.sandbox import SandboxResult


def display_tool_result(console: Console, result: dict):
    sandbox_cli = Group(
        Text("Output:", style="bold white", end="\n\n"),
        Syntax(str(result.get('content')), "python", theme="stata-dark"),
        Text("\nErrors:", style="bold white", end="\n\n"),
        Syntax(str(result.get('isError')), "python", theme="stata-dark"),
    )
    console.print(Panel(sandbox_cli, title="[bold orange1]TOOL CALL", border_style="orange1"))
