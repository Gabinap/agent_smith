from srcs.agents.agent_mbpp import Mbpp


def main():
    agent = Mbpp(
        task_file="moulinette/task.json",
        api_url="https://generativelanguage.googleapis.com/v1/interactions",
        model_name="gemma-4-31b-it"
    )
    agent.solve_task()


if __name__ == "__main__":
    main()
