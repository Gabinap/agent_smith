from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def display_exit(console: Console, llm_output_data: dict[str, Any],
                 system_prompt: str) -> None:
    exits = ['Show the think process', 'Show the prompt', 'Exit']
    while (True):
        selected = questionary.select(
            "Select an option",
            choices=exits,
        ).ask()
        if selected is None:
            return
        match exits.index(selected):
            case 0:
                console.print(Panel(
                    Text(llm_output_data.get('thought')
                         or "No thought recorded", style="italic"),
                    title="Thought",
                    title_align="left",
                    border_style="white"
                ))
            case 1:
                console.print(Panel(
                    Text(system_prompt, style="italic"),
                    title="Prompt",
                    title_align="left",
                    border_style="white"
                ))
            case 2:
                return
