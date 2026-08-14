from agent_mbpp.agent import Mbpp
from pydantic import BaseModel
from typing import Literal, Optional
from rich.prompt import Prompt

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.align import Align
from rich.text import Text
from pyfiglet import figlet_format

from rich.columns import Columns
import argparse
import questionary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--task-file",
        default="../moulinette/task.json",
    )
    parser.add_argument(
        "--output",
        default="../mbpp_solution.json",
    )
    parser.add_argument(
        "--model-name",
        default="",
    )
    parser.add_argument(
        "--provider-url",
        default="",
    )

    providers = {
        "Google api" : {
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "key": "GOOGLE_API_KEY",
            "model": ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]
        },
        "Open Router" : {
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "key": "OPEN_ROUTER_KEY",
            "model": ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]
        }
    }
    console = Console()
    args = parser.parse_args()
    if args.model_name == "" or args.provider_url == "":
        selected = questionary.select(
            "Choose a Provider: ",
            choices=list(providers.keys())
        ).ask()
        if selected == None: return
        provider_name = selected
        provider = providers.get(selected)
        model = questionary.select(
            "Select a Model: ",
            choices=provider.get("model")
        ).ask()
        
        if model == None: return
        agent = Mbpp(
                    task_file=args.task_file,
                    output_file=args.output,
                    api_url=provider.get("url"),
                    model_name=model,
                    env_key=provider.get("key"),
                    console=console
                )
    else:
        agent = Mbpp(
            task_file=args.task_file,
            output_file=args.output,
            api_url=args.provider_url,
            model_name=args.model_name,
            env_key="API_KEY",
            console=console
        )


    titre = figlet_format("Agent Smith", font="slant")
    stats = [
        Panel("Mode: MBPP", style="bold"),
        Panel(f"Provider: {provider_name}", style="bold"),
        Panel(f"Model: {model}", style="bold"),
        ]
    console.print(
        Panel(
            Align.center(titre, style="blue")
            ,
            border_style="blue"
        )
    )
    console.print(Columns(stats, expand=True))
    task = Group(
        Text(agent.task.task_definition, style="bold yellow", end="\n\n", justify="center"),
        Text("Function definition:", style="bold white", end="\n\n"),
        Syntax(agent.task.function_definition, "python", theme="stata-dark"),
        Text("\n\nTests to try:", style="bold white", end="\n\n"),
        Syntax("\n".join(agent.task.test_list), "python", theme="stata-dark", line_numbers=True),
    )
    console.print(Panel(task, title=f"[bold yellow]TASK #{agent.task.task_id}", padding=1))
    agent.solve_task()

if __name__ == "__main__":
    main()