from rich.console import Console, Group
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from models.tasks import MBPPTaskInput


def display_task(console: Console, task: MBPPTaskInput):
    content = Group(
        Text(task.task_definition, style="bold orange1", end="\n\n", justify="center"),
        Text("Function definition:", style="bold white", end="\n\n"),
        Syntax(task.function_definition, "python", theme="stata-dark"),
        Text("\n\nTests to try:", style="bold white", end="\n\n"),
        Syntax("\n".join(task.test_list), "python", theme="stata-dark", line_numbers=True),
    )
    console.print(Panel(content, title=f"[bold]TASK #{task.task_id}", padding=1, style='orange1'))