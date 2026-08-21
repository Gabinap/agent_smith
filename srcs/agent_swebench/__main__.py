from agent_swebench.agent import SWEBench
from rich.console import Console
from .task_manager import Task
import cli_agent
from call_llm.profile import Profile
from .mcp_client import MCPClient

import asyncio
import argparse


def main() -> None:
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
    profile = Profile("SWEBench", args.provider_url, args.model_name)
    asyncio.run(launch_agent(profile, console, args))


async def launch_agent(profile, console, args):
    # try:
        task = Task(args.task_file).input
        mcp = MCPClient()
        agent = SWEBench(
            task=task,
            output_file=args.output,
            api_url=profile.provider_url,
            model_name=profile.model_name,
            env_key=profile.key_name,
            mcp=mcp,
            console=console
        )
        await agent.initialize_llm()

        cli_agent.display_header(console, profile)
        cli_agent.display_swebench_task(console, agent.task)
        agent.solve_task()
        # cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)

    # except Exception as e:
    #     console.print_exception(show_locals=True)
    #     console.print("[bold red] Error:", e)


if __name__ == "__main__":
    main()
