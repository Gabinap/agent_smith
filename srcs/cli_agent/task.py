from models.tasks import MBPPTaskInput, SWEBenchTaskInput
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def display_mbpp_task(console: Console, task: MBPPTaskInput):
    content = Group(
        Text(task.task_definition, style="bold orange1", end="\n\n", justify="center"),
        Text("Function definition:", style="bold white", end="\n\n"),
        Syntax(task.function_definition, "python", theme="stata-dark"),
        Text("\n\nTests to try:", style="bold white", end="\n\n"),
        Syntax("\n".join(task.test_list), "python", theme="stata-dark", line_numbers=True),
    )
    console.print(Panel(content, title=f"[bold]TASK #{task.task_id}", padding=1, style='orange1'))

def display_swebench_task(console: Console, task: SWEBenchTaskInput):
    content = Group(
        Text(task.problem_statement, style="bold orange1", end="\n\n", justify="center"),
        Text("Repository:", style="bold white", end="\n\n"),
        Syntax(task.repo, "python", theme="stata-dark"),
        Text("\n\nTests to try:", style="bold white", end="\n\n"),
        Syntax(task.eval_script, "python", theme="stata-dark", line_numbers=True),
    )
    console.print(Panel(content, title=f"[bold]TASK #{task.instance_id}", padding=1, style='orange1'))
