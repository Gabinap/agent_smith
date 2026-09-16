import json
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


def display_llm_output(console: Console, llm_output_data: dict[str, Any],
                       py_code: str) -> None:
    table = Table(padding=1).grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Model:", llm_output_data.get("model_name"))
    table.add_row("Input tokens:", str(llm_output_data.get("input_tokens")))
    table.add_row("Output tokens:", str(llm_output_data.get("output_tokens")))
    elapsed_ms = llm_output_data.get("request_time_ms") or 0
    table.add_row("Request time:", f"{elapsed_ms / 1000:.2f}s")

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


def display_llm_tool_call(console: Console, tool_call: Any) -> None:
    """Render one tool call.

    `tool_call` is the provider SDK's own object, not a dict: it is
    reached through `.function.name` / `.function.arguments`.
    """
    content = Group(
        Text("Tool called:", style="bold white", end="\n\n"),
        Syntax(str(tool_call.function.name), "python",
               theme="stata-dark", line_numbers=False),
        "\n",
        Text("Arguments:", style="bold white", end="\n\n"),
        Syntax(str(json.loads(tool_call.function.arguments)), "python",
               theme="stata-dark", line_numbers=False),
    )

    console.print(Panel(
            content,
            title="LLM answer",
            border_style="blue"
        ))
