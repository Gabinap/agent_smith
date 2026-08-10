import requests
import json
import os
from dotenv import load_dotenv


class LLM:
    def __init__(self, api_url, model_name):
        self.step = 0
        self.api_url = api_url
        self.model_name = model_name
        self.retries = 0
       
        self.api_key = self._get_from_env("API_KEY")
        pass
    
    def _get_from_env(self, name: str) -> str:
        load_dotenv()
        return  os.getenv(name)
    
    
    def save_response(self, log_file, response):
        with (open(log_file, "w") as file):
            file.write(json.dumps(response, indent=2))

    
    def call(self):
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
                    "content": "hello"
                    }
                ],
                "reasoning": {"enabled": True},
            })
        )
        print(response)
        response = response.json()
        self.save_response("response.json", response)


        print(response)
       
