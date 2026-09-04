"""Interactive selection of an LLM provider and model."""

import json
from pathlib import Path
from typing import Any

import questionary

PROVIDERS_FILE = Path(__file__).parent / "providers.json"
DEFAULT_KEYS = ["API_KEY"]


class Profile:
    """Resolve which LLM provider, model, and API keys to use."""

    def __init__(self, mode: str, provider_url: str, model_name: str) -> None:
        """Load the catalog and prompt for whatever was not given."""
        self.mode = mode
        self.providers = self._load_providers()
        self.provider_name = "Unknown"
        self.provider: dict[str, Any] = {}
        self.provider_url = provider_url
        self.model_name = model_name

        if model_name == "" or provider_url == "":
            self.provider_name = self.provider_selection()
            self.provider = self.providers[self.provider_name]
            self.model_name = self.model_selection()
            self.provider_url = self.provider.get("url", "")
        else:
            self.provider = self._provider_from_url(provider_url)

        self.keys: list[str] = self.provider.get("keys", list(DEFAULT_KEYS))
        self.key_name = self.keys  # TODO: drop once the agents read .keys

    def provider_selection(self) -> str:
        """Prompt the user to pick a provider, return its name."""
        selected = questionary.select(
            "Choose a Provider: ",
            choices=list(self.providers.keys())
        ).ask()
        if selected is None:
            raise ValueError("Cancelled")
        return str(selected)

    def model_selection(self) -> str:
        """Prompt the user to pick a model, return its name."""
        models: list[str] = self.provider.get("model", [])
        selected = questionary.select(
            "Select a Model: ",
            choices=models
        ).ask()

        if selected is None:
            raise ValueError("Cancelled")
        return str(selected)

    def _provider_from_url(self, provider_url: str) -> dict[str, Any]:
        """Return the catalog entry serving `provider_url`, if any."""
        for name, provider in self.providers.items():
            if provider.get("url") == provider_url:
                self.provider_name = name
                return provider
        return {}

    @staticmethod
    def _load_providers() -> dict[str, dict[str, Any]]:
        """Load the provider catalog shipped next to this module."""
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as file:
            catalog: dict[str, dict[str, Any]] = json.load(file)
        return catalog
