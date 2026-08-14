from openai import OpenAI
import os
from dotenv import load_dotenv
import time
import textwrap


class LLM:
    """
        The link between agent and api
    """
    def __init__(self, api_url: str, model_name: str, env_key: str):
        """Initialise the llm Api
        Args:
            api_url (str): Url of the providers
            model_name (str): name of the model
        """
        self.api_url = api_url
        self.model_name = model_name
        self._api_key = self._get_from_env(env_key)
        self.client = OpenAI(
            api_key=self._api_key,
            base_url=self.api_url
        )
        self._previous_interaction = None

    def _get_from_env(self, name: str) -> str:
        """Load the .env

        Args:
            name (str): key to get in the .env

        Returns:
            str: value of the key.
        """
        load_dotenv()
        return os.getenv(name)

    def save_response(self, log_file: str, response: str):
        """Save the LLM output in a Json file.

        Args:
            log_file (str): Json saving file.
            response (str): Api return
        """
        with (open(log_file, "w") as file):
            file.write(response)

    def call(self, input: str) -> dict:
        """Call the LLM throught the API.

        Args:
            input (str): Prompt input

        Returns:
            dict: LLM output
        """
        s = time.perf_counter()

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system",
                 "content": self._system_content()},
                {"role": "user",
                 "content": input}
            ]
        )
        e = time.perf_counter()
        response = completion.model_dump_json(indent=2)
        self._previous_interaction = response
        self.save_response("response.json", response)
        return {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
            "model_name": self.model_name,
            "llm_output": completion.choices[0].message.content,
            "request_time": f"{e-s:.3f}"
        }

    def _system_content(self) -> str:
        return textwrap.dedent("""
            You are a Python agent. You solve basics coding problems.
            Write in a ```python ... ``` block.

            Do not comment the code and go straight to the point.
            The sandbox injects a callable named `final_answer`,
            to validate the coding problem,
            You MUST pass only the function solution code as a
            **Python String** to this function.

            Here is the EXACT format your output must follow:

            ```python
            # 1. Write your function
            def your_function_name(args):
                return ...

            # 2. Add the tests
            assert your_function_name(test_arg) == expected_result

            # 3. Pass the exact code as a string to final_answer
            code_string = \"\"\"
            def your_function_name(args):
                return ...
            \"\"\"
            final_answer(code_string)
            """)
