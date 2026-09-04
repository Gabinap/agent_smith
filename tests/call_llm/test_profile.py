"""Unit tests for srcs/call_llm/profile.py (the Profile class)."""

from unittest.mock import MagicMock

import pytest

from srcs.call_llm import profile as profile_module
from srcs.call_llm.profile import Profile

OPEN_ROUTER_URL = "https://openrouter.ai/api/v1"


@pytest.fixture
def pick(monkeypatch):
    """Answer the questionary prompts with the given choices."""
    def _pick(*answers):
        fake_select = MagicMock()
        fake_select.return_value.ask.side_effect = answers
        monkeypatch.setattr(profile_module.questionary, "select", fake_select)
        return fake_select
    return _pick


# --- the interactive path ---

def test_prompts_when_model_or_url_missing(pick):
    pick("Open Router", "qwen/qwen3.5-flash-02-23")

    p = Profile(mode="cli", provider_url="", model_name="")

    assert p.provider_name == "Open Router"
    assert p.model_name == "qwen/qwen3.5-flash-02-23"
    assert p.provider_url == OPEN_ROUTER_URL
    assert p.keys == ["OPEN_ROUTER_KEY_1", "OPEN_ROUTER_KEY_2"]


def test_provider_selection_raises_on_cancel(pick):
    pick(None)
    p = Profile.__new__(Profile)
    p.providers = {"A": {}, "B": {}}
    with pytest.raises(ValueError):
        p.provider_selection()


def test_model_selection_raises_on_cancel(pick):
    pick(None)
    p = Profile.__new__(Profile)
    p.provider = {"model": ["a", "b"]}
    with pytest.raises(ValueError):
        p.model_selection()


# --- the "everything given on the CLI" path ---

def test_skips_prompts_when_model_and_url_given():
    p = Profile(mode="cli", provider_url=OPEN_ROUTER_URL, model_name="m")

    assert p.provider_url == OPEN_ROUTER_URL
    assert p.model_name == "m"
    assert p.provider_name == "Open Router"
    assert p.keys == ["OPEN_ROUTER_KEY_1", "OPEN_ROUTER_KEY_2"]


def test_unknown_url_falls_back_to_the_default_key():
    p = Profile(mode="cli", provider_url="http://x", model_name="m")

    assert p.provider_name == "Unknown"
    assert p.keys == profile_module.DEFAULT_KEYS


# --- the catalog ---

def test_key_name_still_mirrors_keys():
    p = Profile(mode="cli", provider_url=OPEN_ROUTER_URL, model_name="m")
    assert p.key_name == p.keys


def test_load_providers_reads_the_json_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the path must not depend on the cwd
    providers = Profile._load_providers()

    assert "Open Router" in providers
    for name, provider in providers.items():
        assert isinstance(provider["keys"], list), name
        assert provider["url"] and provider["model"], name
