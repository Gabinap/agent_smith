from calling import LLM

def main():
    call = LLM(
        api_url="https://openrouter.ai/api/v1/chat/completions",
        model_name="qwen/qwen3.5-flash-02-23"
    )
    response = call.call("hello what is your name")
    print(response)


if __name__ == "__main__":
    main()
