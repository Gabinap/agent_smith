import requests
import json
import os
from dotenv import load_dotenv


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
        self.api_key = self._get_from_env("API_KEY")

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
            file.write(json.dumps(response, indent=2))

    def call(self, input: str) -> dict:
        """Call the LLM throught the API.

        Args:
            input (str): Prompt input

        Returns:
            dict: LLM output
        """
        response = requests.post(
            url=self.api_url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            json={
                "model": self.model_name,
                "input": input
            }
        )
        response.raise_for_status()
        response = response.json()
        self.save_response("response.json", response)
        return {
            "input_tokens": response['usage']['total_input_tokens'],
            "output_tokens": response['usage']['total_output_tokens'],
            "model_name": self.model_name,
            "llm_output": response['steps'][-1]['content'][0]['text'],
        }
