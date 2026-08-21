from rich.table import Table
from rich.console import Console, Group
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel

def display_llm_output(console: Console, llm_output_data: dict, py_code: str):
    table = Table(padding=1).grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Model:", llm_output_data.get("model_name"))
    table.add_row("Input tokens:", str(llm_output_data.get("input_tokens")))
    table.add_row("Output tokens:", str(llm_output_data.get("output_tokens")))
    table.add_row("Request time:", f"{llm_output_data.get('request_time')}s")

    content = Group(
        Text("Code:", style="bold white", end="\n\n"),
        Syntax(py_code, "python", theme="stata-dark", line_numbers=True),
        "\n",
        table
    )

    console.print(Panel(
        content,
        title="LLM answer",
        border_style="blue"
    ))
