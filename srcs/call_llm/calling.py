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
                "Authorization": f"Bearer {self.api_key}",
            },
            data=json.dumps({
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": input
                    }
                ],
                "reasoning": {"enabled": False
                              },
            })
        )
        if response.status_code != 200:
            raise ValueError(f"Call Error: {response.reason}")

        response = response.json()
        self.save_response("response.json", response)
        return {
            "input_tokens": response['usage']['prompt_tokens'],
            "output_tokens": response['usage']['completion_tokens'],
            "model_name": self.model_name,
            "llm_output": response['choices'][0]['message']['content'],
        }
