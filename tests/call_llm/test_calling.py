"""Unit tests for srcs/call_llm/calling.py (the LLM class)."""

import json
from unittest.mock import MagicMock

import pytest

from srcs.call_llm.calling import LLM


class FakeMessage:
    """Stand-in for the OpenAI SDK's ChatCompletionMessage."""

    def __init__(self, content, reasoning=None):
        self.content = content
        if reasoning is not None:
            self.reasoning = reasoning


class FakeUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=5):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeCompletion:
    """Stand-in for the OpenAI SDK's ChatCompletion response."""

    def __init__(
            self, content, reasoning=None,
            prompt_tokens=10, completion_tokens=5):
        self.choices = [MagicMock(message=FakeMessage(content, reasoning))]
        self.usage = FakeUsage(prompt_tokens, completion_tokens)

    def model_dump_json(self, indent=2):
        return json.dumps({"content": self.choices[0].message.content})


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv("TEST_LLM_API_KEY", "dummy-key")
    instance = LLM(
        api_url="http://fake.invalid/v1",
        model_name="fake-model",
        env_key="TEST_LLM_API_KEY",
    )
    instance.client = MagicMock()
    return instance


def _set_response(llm, content, **kwargs):
    llm.client.chat.completions.create.return_value = FakeCompletion(
        content, **kwargs
    )


# --- construction ---

def test_get_from_env_reads_the_given_key(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "secret-value")
    assert LLM._get_from_env(None, "SOME_KEY") == "secret-value"


def test_init_raises_value_error_without_api_key(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(ValueError):
        LLM(
            api_url="http://fake.invalid/v1", model_name="m",
            env_key="MISSING_KEY",
        )


# --- call(): message construction ---

def test_call_first_call_has_system_and_user_only(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "some code")
    llm.call("solve this")

    create = llm.client.chat.completions.create
    messages = create.call_args.kwargs["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[1]["content"] == "solve this"


def test_call_retry_appends_assistant_and_user(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "first attempt")
    llm.call("solve this")

    llm.sandbox_output = MagicMock(error="AssertionError", final_answer=None)
    _set_response(llm, "second attempt")
    llm.call("solve this")

    create = llm.client.chat.completions.create
    messages = create.call_args.kwargs["messages"]
    assert [m["role"] for m in messages] == \
        ["system", "user", "assistant", "user"]
    assert messages[2]["content"] == "first attempt"
    assert "AssertionError" in messages[3]["content"]


# --- call(): thought/answer parsing ---

def test_call_parses_think_tag(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "reasoning here</think>final code")
    result = llm.call("x")
    assert result["thought"] == "reasoning here"
    assert result["answer"] == "final code"


def test_call_parses_thought_tag(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "reasoning here</thought>final code")
    result = llm.call("x")
    assert result["thought"] == "reasoning here"
    assert result["answer"] == "final code"


def test_call_parses_reasoning_attribute(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "final code", reasoning="separate reasoning")
    result = llm.call("x")
    assert result["thought"] == "separate reasoning"
    assert result["answer"] == "final code"


def test_call_no_marker_found(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "just the code, no markers")
    result = llm.call("x")
    assert result["thought"] == "No thought found"
    assert result["answer"] == "just the code, no markers"


# --- call(): returned metadata ---

def test_call_returns_token_counts_and_model_name(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "code", prompt_tokens=42, completion_tokens=7)
    result = llm.call("x")
    assert result["input_tokens"] == 42
    assert result["output_tokens"] == 7
    assert result["model_name"] == "fake-model"


def test_call_saves_response_to_response_json(llm, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_response(llm, "code")
    llm.call("x")
    saved = json.loads((tmp_path / "response.json").read_text())
    assert saved["content"] == "code"


# --- prompt helpers ---

def test_system_content_mentions_final_answer(llm):
    assert "final_answer" in llm._system_content()


def test_sandbox_error_includes_error_and_final_answer(llm):
    llm.sandbox_output = MagicMock(
        error="NameError: x is not defined", final_answer="bad code",
    )
    message = llm._sandbox_error()
    assert "NameError: x is not defined" in message
    assert "bad code" in message
