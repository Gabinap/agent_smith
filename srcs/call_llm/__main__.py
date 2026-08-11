from calling import LLM


def main():
    llm = LLM(
        api_url="https://generativelanguage.googleapis.com/v1/interactions",
        model_name="gemma-4-31b-it",
    )
    response = llm.call("hello how are you")
    print(response)


if __name__ == "__main__":
    main()
