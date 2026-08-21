"""Unit tests for srcs/call_llm/profile.py (the Profile class)."""

from unittest.mock import MagicMock

import pytest

from srcs.call_llm import profile as profile_module
from srcs.call_llm.profile import Profile


@pytest.fixture(autouse=True)
def _run_from_srcs(monkeypatch):
    # _load_providers() opens the relative path "call_llm/providers.json",
    # which only resolves when the cwd is srcs/.
    monkeypatch.chdir("srcs")


def test_skips_prompts_when_model_and_url_given():
    p = Profile(mode="cli", provider_url="http://x", model_name="m")
    assert p.provider_url == "http://x"
    assert p.model_name == "m"
    assert p.provider_name == "Unknown"


def test_prompts_when_model_or_url_missing(monkeypatch):
    fake_select = MagicMock()
    fake_select.return_value.ask.side_effect = [
        "Open Router",                  # provider_selection()
        "qwen/qwen3.5-flash-02-23",     # model_selection()
    ]
    monkeypatch.setattr(profile_module.questionary, "select", fake_select)

    p = Profile(mode="cli", provider_url="", model_name="")

    assert p.provider_name == "Open Router"
    assert p.model_name == "qwen/qwen3.5-flash-02-23"
    assert p.provider_url == "https://openrouter.ai/api/v1"
    assert p.key_name == "OPEN_ROUTER_KEY"


def test_provider_selection_raises_on_cancel(monkeypatch):
    fake_select = MagicMock()
    fake_select.return_value.ask.return_value = None
    monkeypatch.setattr(profile_module.questionary, "select", fake_select)

    p = Profile.__new__(Profile)
    p.providers = {"A": {}, "B": {}}
    with pytest.raises(ValueError):
        p.provider_selection()


def test_model_selection_raises_on_cancel(monkeypatch):
    fake_select = MagicMock()
    fake_select.return_value.ask.return_value = None
    monkeypatch.setattr(profile_module.questionary, "select", fake_select)

    p = Profile.__new__(Profile)
    p.provider = {"model": ["a", "b"]}
    with pytest.raises(ValueError):
        p.model_selection()


def test_load_providers_reads_the_json_file():
    p = Profile.__new__(Profile)
    providers = p._load_providers()
    assert "Open Router" in providers
    assert providers["Open Router"]["key"] == "OPEN_ROUTER_KEY"
