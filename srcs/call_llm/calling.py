from openai import OpenAI
import os
from dotenv import load_dotenv
import time


class LLM:
    """
        The link between agent and api
    """
    def __init__(self, api_url: str, model_name: str):
        """Initialise the llm Api
        Args:
            api_url (str): Url of the providers
            model_name (str): name of the model
        """
        self.api_url = api_url
        self.model_name = model_name
        self._api_key = self._get_from_env("API_KEY")
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
                {"role": "system", "content": "You are an agent that solve python exercises"},
                {"role": "user", "content": input}
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

