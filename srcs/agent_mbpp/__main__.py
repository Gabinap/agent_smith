"""CLI entry point for the MBPP agent: `python -m agent_mbpp`."""

from agent_mbpp.agent import Mbpp
from rich.console import Console

import cli_agent
from call_llm.profile import Profile

import argparse


def main() -> None:
    """Parse CLI args, run one MBPP task, and print the result."""
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
        profile = Profile("MBPP", args.provider_url, args.model_name)

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
    except Exception as e:
        # console.print_exception(show_locals=True)
        console.print("[bold red] Error:", e)


if __name__ == "__main__":
    main()
