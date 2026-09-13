"""CLI entry point for the MBPP agent: `python -m agent_mbpp`."""

import argparse

import cli_agent
from call_llm.profile import Profile
from rich.console import Console
from models import McpSpec
from sandbox.mcp_client import create_mcp_client
from agent_mbpp.agent import Mbpp
from .task_manager import Task

import sys
import os
import shlex
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    """Parse CLI args, run one MBPP task, and print the result."""
    console = Console()
    try:
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
        parser.add_argument(
            "--http",
            action="store_true",
        )

        args = parser.parse_args()
        task_file = Path(args.task_file).expanduser().resolve()
        args.task_file = str(task_file)
        profile = Profile("MBPP", args.provider_url, args.model_name)

        console.print("Starting MCP server")
        if args.http:
            spec = McpSpec(transport="http", url="http://localhost:8000")
        else:
            spec = McpSpec(
                transport="stdio",
                command=shlex.join(
                    [sys.executable, str(PROJECT_ROOT / "mcp_tools_mbpp.py")]
                ),
                env={**os.environ, "MBPP_TASK_FILE": str(task_file)},
            )
        mcp_client = create_mcp_client(spec)
        console.print(f"MCP {spec.transport} server Started")

        launch_agent(profile, console, args, mcp_client)
    except Exception as e:
        console.print("[bold red] Error:", e)


def launch_agent(profile, console, args, mcp_client):
    cli_agent.display_header(console, profile)
    task = Task(str(Path(args.task_file).expanduser().resolve())).input
    cli_agent.display_mbpp_task(console, task)
    agent = Mbpp(
        task=task,
        output_file=args.output,
        api_url=profile.provider_url,
        model_name=profile.model_name,
        env_key=profile.key_name,
        console=console,
        client=mcp_client
    )
    agent.solve_task()
    if profile.new:
        cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)


if __name__ == "__main__":
    main()
