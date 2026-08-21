from agent_swebench.agent import SWEBench
from rich.console import Console
from .task_manager import Task
import cli_agent
from call_llm.profile import Profile

import asyncio

from mcp import Client

import argparse



async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        tool_list = await client.list_tools()
        tool_names = [tool.name for tool in tool_list.tools]
        print("\nConnected to server with tools:", tool_names)
        result = await client.call_tool("list_files", {"directory": ".", "pattern": "."})
        print(result)


asyncio.run(main())

# def main():
#     parser = argparse.ArgumentParser()

#     parser.add_argument(
#         "--task-file",
#         default="../moulinette/task.json",
#     )
#     parser.add_argument(
#         "--output",
#         default="../mbpp_solution.json",
#     )
#     parser.add_argument(
#         "--model-name",
#         default="",
#     )
#     parser.add_argument(
#         "--provider-url",
#         default="",
#     )

#     console = Console()
#     args = parser.parse_args()

#     try:


#         # profile = Profile("SWEBench", args.provider_url, args.model_name)
#         task = Task(args.task_file).input
#
#         print("status:", container.status)
#         print(container.exec_run(cmd="ls"))
#         print(container.logs())


#         # container.
#         # agent = SWEBench(
#         #     task=task,
#         #     output_file=args.output,
#         #     api_url=profile.provider_url,
#         #     model_name=profile.model_name,
#         #     env_key=profile.key_name,
#         #     console=console
#         # )

#         # cli_agent.display_header(console, profile)
#         # cli_agent.display_task(console, agent.task)
#         # # agent.solve_task()
#         # cli_agent.display_exit(console, agent.llm_output_data, agent.prompt)
#     except Exception as e:
#         # console.print_exception(show_locals=True)
#         console.print("[bold red] Error:", e)


if __name__ == "__main__":
    main()
