import argparse
import os
import shlex
import sys
from pathlib import Path

import cli_agent
from call_llm.profile import Profile
from models import McpSpec
from models.sandbox import SandboxConfig
from rich.console import Console
from sandbox.mcp_client import McpClient, create_mcp_client

from agent_swebench.agent import SWEBench

from .task_manager import Task


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    console = Console()
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--task-file",
            default=str(PROJECT_ROOT / "moulinette" / "task.json"),
        )
        parser.add_argument(
            "--output",
            default=str(PROJECT_ROOT / "runs" / "swebench_solution.json"),
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
        parser.add_argument(
            "--choose",
            action="store_true",
            help="pick the provider and model from a menu instead "
                 "of the SWEBench default",
        )

        args = parser.parse_args()
        task_file = Path(args.task_file).expanduser().resolve()
        args.task_file = str(task_file)
        profile = Profile("SWEBench", args.provider_url, args.model_name,
                          choose=args.choose)

        console.print("Starting MCP server")
        if args.http:
            spec = McpSpec(transport="http", url="http://localhost:8000")
        else:
            spec = McpSpec(
                transport="stdio",
                command=shlex.join(
                    [sys.executable,
                     str(PROJECT_ROOT / "mcp_tools_swebench.py")]
                ),
                env={**os.environ, "SWE_TASK_FILE": str(task_file)},
            )
        mcp_client = create_mcp_client(spec)
        console.print(f"MCP {spec.transport} server Started")

        launch_agent(profile, console, args, mcp_client)

    except Exception as e:
        console.print("[bold red] Error:", e)


def launch_agent(profile: Profile, console: Console,
                 args: argparse.Namespace,
                 mcp_client: McpClient | None) -> None:
    cli_agent.display_header(console, profile)
    task = Task(str(Path(args.task_file).expanduser().resolve())).input
    cli_agent.display_swebench_task(console, task)
    agent = SWEBench(
        task=task,
        output_file=args.output,
        api_url=profile.provider_url,
        model_name=profile.model_name,
        env_keys=profile.keys,
        console=console,
        client=mcp_client,
        max_iteration=30,
        max_time_seconds=840,
        max_input_tokens=300_000,
        max_output_tokens=10_000,
        sandbox_config=SandboxConfig.from_file(
            PROJECT_ROOT / "sandbox_swebench.json"),
    )
    agent.solve_task()
    if profile.new:
        cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)


if __name__ == "__main__":
    main()
