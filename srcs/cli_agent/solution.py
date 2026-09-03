from models.metrics import SolutionOutput
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def display_solution(console:Console, output: SolutionOutput):
    content = Group(
            Text.from_markup(f"[bold]Total input tokens:[/bold] {output.total_input_tokens}"),
            Text.from_markup(f"[bold]Total output tokens:[/bold] {output.total_output_tokens}"),
            Text.from_markup(f"[bold]Total request time:[/bold] {output.total_time_seconds}s"),
            Text("\nSolution:", style="bold white", end="\n\n"),
            Syntax(output.solution, "python", theme="stata-dark"),
        )
    console.print(Panel(content, title="[bold green3]Solution output", border_style="green3"))
