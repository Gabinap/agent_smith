import argparse
import shlex
import sys
from pathlib import Path

import cli_agent
from call_llm.profile import Profile
from rich.console import Console
from sandbox.mcp_client import create_mcp_client
from models import McpSpec

from agent_swebench.agent import SWEBench

from .task_manager import Task
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--task-file",
        default=str(PROJECT_ROOT / "moulinette" / "task.json"),
    )
    parser.add_argument(
        "--output",
        default="../swebench_solution.json",
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
    task_file = Path(args.task_file).expanduser().resolve()
    args.task_file = str(task_file)
    profile = Profile("SWEBench", args.provider_url, args.model_name)
    console.print("Starting MCP server")
    spec = McpSpec(
        transport="stdio",
        command=shlex.join(
            [sys.executable, str(PROJECT_ROOT / "mcp_tools_swebench.py")]
        ),
        env={**os.environ, "SWE_TASK_FILE": str(task_file)},
    )
    console.print("MCP server Started")
    # spec = McpSpec(transport="http", url="http://localhost:8000")
    client_mcp = create_mcp_client(spec)
    launch_agent(profile, console, args, client_mcp)


def launch_agent(profile, console, args, client_mcp):
    # try:
        task = Task(str(Path(args.task_file).expanduser().resolve())).input
        agent = SWEBench(
            task=task,
            output_file=args.output,
            api_url=profile.provider_url,
            model_name=profile.model_name,
            env_key=profile.key_name,
            console=console,
            client=client_mcp
        )

        cli_agent.display_header(console, profile)
        cli_agent.display_swebench_task(console, agent.task)
        agent.solve_task()
        # cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)

    # except Exception as e:
    #     console.print_exception(show_locals=True)
    #     console.print("[bold red] Error:", e)


if __name__ == "__main__":
    main()
