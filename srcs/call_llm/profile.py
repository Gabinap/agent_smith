"""Resolve the LLM provider and model a run uses."""

import json
from pathlib import Path
from typing import Any

import questionary

PROVIDERS_FILE = Path(__file__).parent / "providers.json"
DEFAULT_KEYS = ["API_KEY"]

# no cell without data (BENCHMARK_REPORT.md).
DEFAULT_MODELS = {
    "MBPP": "ministral-8b-2512",
    "SWEBench": "ministral-14b-2512",
}


class Profile:
    """Resolve which LLM provider, model, and API keys to use."""

    def __init__(self, mode: str, provider_url: str, model_name: str,
                 choose: bool = False) -> None:
        """Load the catalog and settle the model, asking only if `choose`."""
        self.mode = mode
        self.providers = self._load_providers()
        self.provider_name = "Unknown"
        self.provider: dict[str, Any] = {}
        self.provider_url = provider_url
        self.model_name = model_name
        self.new = choose

        if choose:
            self.provider_name = self.provider_selection()
            self.provider = self.providers[self.provider_name]
            self.model_name = self.model_selection()
            self.provider_url = self.provider.get("url", "")
        elif model_name and provider_url:
            self.provider = self._provider_from_url(provider_url)
        else:
            self._fill_defaults()

        self.keys: list[str] = self.provider.get("keys", list(DEFAULT_KEYS))

    def _fill_defaults(self) -> None:
        """Complete what the command line left out, without asking.

        A provider URL alone keeps that provider, with the mode's default
        model if it serves it and its first model otherwise; a model alone
        gets the provider that catalogues it; neither gets the default.
        """
        if self.provider_url:
            self.provider = self._provider_from_url(self.provider_url)
        if not self.model_name:
            served: list[str] = self.provider.get("model", [])
            default = DEFAULT_MODELS.get(self.mode, "")
            self.model_name = (default if not served or default in served
                               else served[0])
        if not self.provider_url:
            for name, provider in self.providers.items():
                if self.model_name in provider.get("model", []):
                    self.provider_name, self.provider = name, provider
                    self.provider_url = provider.get("url", "")
                    break
        if not self.model_name or not self.provider_url:
            raise ValueError(
                "No model to run: pass --model-name and --provider-url, "
                f"or add {DEFAULT_MODELS.get(self.mode)!r} to "
                f"{PROVIDERS_FILE.name}")

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
