import questionary
import json


class Profile():

    def __init__(self, mode, provider_url, model_name):
        self.mode = mode
        self.providers = self._load_providers()
        self.provider_name = "Unknown"
        self.provider_url = provider_url
        self.model_name = model_name
        self.key_name = "API_KEY"
        if model_name == "" or provider_url == "":
            self.provider_name = self.provider_selection()
            self.provider = self.providers.get(self.provider_name)
            self.model_name = self.model_selection()
            self.provider_url = self.provider.get('url')
            self.key_name = self.provider.get('key')

    def provider_selection(self):
        selected = questionary.select(
            "Choose a Provider: ",
            choices=list(self.providers.keys())
        ).ask()
        if selected is None:
            raise ValueError("Cancelled")
        return selected

    def model_selection(self):

        selected = questionary.select(
            "Select a Model: ",
            choices=self.provider.get("model")
        ).ask()

        if selected is None:
            raise ValueError("Cancelled")
        return selected

    def _load_providers(self):
        with (open("call_llm/providers.json", "r") as file):
            return json.load(file)
