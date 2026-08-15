from agent_mbpp.agent import Mbpp
from pydantic import BaseModel
from typing import Literal, Optional
from rich.prompt import Prompt

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live

from rich.text import Text

import cli_agent
from cli_agent import Profile

import argparse



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

    
    console = Console()
    args = parser.parse_args()
    try:
        profile = Profile("MBPP",args.provider_url, args.model_name)
    except Exception:
        return
        
    agent = Mbpp(
        task_file=args.task_file,
        output_file=args.output,
        api_url=profile.provider_url,
        model_name=profile.model_name,
        env_key=profile.key_name,
        console=console
    )

    cli_agent.display_header(console, profile)
    cli_agent.display_task(console, agent.task)
    agent.solve_task()
    cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)

if __name__ == "__main__":
    main()