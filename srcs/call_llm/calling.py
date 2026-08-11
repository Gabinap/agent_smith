import requests
import json
import os
from dotenv import load_dotenv


class LLM:
    def __init__(self, api_url, model_name):
        self.api_url = api_url
        self.model_name = model_name
        self.api_key = self._get_from_env("API_KEY")

    def _get_from_env(self, name: str) -> str:
        load_dotenv()
        return os.getenv(name)

    def save_response(self, log_file, response):
        with (open(log_file, "w") as file):
            file.write(json.dumps(response, indent=2))

    def call(self, input) -> dict:
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

        print("STATUS:", response.status_code)
        print("BODY:", response.text)
        response.raise_for_status()
        response = response.json()
        self.save_response("response.json", response)
        return {
            "input_tokens": response['usage']['total_input_tokens'],
            "output_tokens": response['usage']['total_output_tokens'],
            "model_name": self.model_name,
            "llm_output": response['steps'][-1]['content'][0]['text'],
        }
