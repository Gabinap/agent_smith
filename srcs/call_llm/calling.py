from openai import OpenAI, RateLimitError
import os
from dotenv import load_dotenv
import time
import textwrap


class LLM:
    """
        The link between agent and api
    """
    def __init__(self, api_url: str, model_name: str, env_key: str,
                 system_content: str):
        """Initialise the llm Api
        Args:
            api_url (str): Url of the providers
            model_name (str): name of the model
        """
        self.api_url = api_url
        self.model_name = model_name
        self._api_key = self._get_from_env(env_key)

        self.client = self._load_llm()

        self._previous_interaction = None
        self.sandbox_output = None
        self._system_content = system_content
        self.messages = [
                    {
                        "role": "system",
                        "content": self._system_content
                    },
                ]

    def _load_llm(self):
        try:
            return OpenAI(
                api_key=self._api_key,
                base_url=self.api_url,
                timeout=120.0
            )
        except Exception:
            raise ValueError("Failed to load LLM, invalid URL or API key")

    def _get_from_env(self, name: str) -> str:
        """Load the .env

        Args:
            name (str): key to get in the .env

        Returns:
            str: value of the key.
        """
        load_dotenv()
        return os.getenv(name)

    def save_response(self, log_file: str, completion: str):
        """Save the LLM output in a Json file.

        Args:
            log_file (str): Json saving file.
            response (str): Api return
        """
        response = completion.model_dump_json(indent=2)
        with (open(log_file, "w", encoding="utf-8") as file):
            file.write(response)

    def call(self, input: str) -> dict:
        """Call the LLM throught the API.

        Args:
            input (str): Prompt input

        Returns:
            dict: LLM output
        """
        if len(self.messages) <= 1:
            self.messages.append(
                {
                    "role": "user",
                    "content": input
                }
            )

        s = time.perf_counter()
        try:
            completion = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=self.messages,
                        )
        except RateLimitError:
            raise ValueError("Wait for rate limit")
        except Exception:
            raise ValueError("Invalid Providers fields, Api connection failed")
        e = time.perf_counter()

        response = completion.choices[0].message
        self.messages.append(response)

        self.save_response("response.json", completion)

        if getattr(response, "content", None):
            if "</think>" in response.content:
                response_split = response.content.split("</think>")
                thought = response_split[0]
                answer = response_split[-1]
            elif "</thought>" in response.content:
                response_split = response.content.split("</thought>")
                thought = response_split[0]
                answer = response_split[-1]
            else:
                thought = "No thought found"
                answer = response.content
        elif getattr(response, "reasoning", None):
            thought = response.reasoning
            answer = response.content
        else:
            thought = "No thought found"
            answer = response.content
        tool_call = False
        if getattr(response, "tool_calls", None):
            tool_call = True

        return {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
            "model_name": self.model_name,
            "thought": thought,
            "answer": answer,
            "request_time": f"{e-s:.3f}",
            "tool_calls": tool_call
        }

    def _sandbox_error(self):
        return textwrap.dedent(f"""
            The first code was wrong
            Errors: {self.sandbox_output.error}
            Final answer: {self.sandbox_output.final_answer}

            Adjust your code to solve the coding problem
            """)

