from agent_mbpp.agent import Mbpp
from pydantic import BaseModel
from typing import Literal, Optional
from rich.prompt import Prompt

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
    
    args = parser.parse_args()
    if args.model_name == "" or args.provider_url == "":
        selected = questionary.select(
            "Choose a Provider: ",
            choices=list(providers.keys())
        ).ask()
        if selected == None: return
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
                    env_key=provider.get("key")
                )
    else:
        agent = Mbpp(
            task_file=args.task_file,
            output_file=args.output,
            api_url=args.provider_url,
            model_name=args.model_name,
            env_key="API_KEY"
        )

    agent.solve_task()


if __name__ == "__main__":
    main()