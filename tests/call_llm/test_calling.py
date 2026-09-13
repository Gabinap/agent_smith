"""Unit tests for srcs/call_llm/calling.py (the LLM class)."""

import json
from unittest.mock import MagicMock

import httpx
import pytest
from openai import RateLimitError

from srcs.call_llm import calling
from srcs.call_llm.calling import LLM

SYSTEM = "you are a python agent"


class FakeMessage:
    """Stand-in for the OpenAI SDK's ChatCompletionMessage."""

    def __init__(self, content, reasoning=None):
        self.content = content
        if reasoning is not None:
            self.reasoning = reasoning


class FakeUsage:
    """Stand-in for the OpenAI SDK's CompletionUsage."""

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


def _rate_limit_error() -> RateLimitError:
    """Build a real 429 error, as the SDK would raise it."""
    request = httpx.Request("POST", "http://fake.invalid/v1")
    return RateLimitError(
        "429", response=httpx.Response(429, request=request), body=None,
    )


def _mock_client(content="ok") -> MagicMock:
    """A client whose create() returns one canned completion."""
    client = MagicMock()
    client.chat.completions.create.return_value = FakeCompletion(content)
    return client


@pytest.fixture
def llm(monkeypatch, tmp_path):
    """An LLM with two keys, a mocked client, and a temp cwd."""
    monkeypatch.setenv("KEY_1", "first-key")
    monkeypatch.setenv("KEY_2", "second-key")
    monkeypatch.chdir(tmp_path)
    instance = LLM(
        api_url="http://fake.invalid/v1",
        model_name="fake-model",
        env_keys=["KEY_1", "KEY_2"],
        system_content=SYSTEM,
    )
    instance.client = MagicMock()
    # the default is an absolute path under runs/: keep the suite out of it
    instance.log_file = str(tmp_path / "llm_responses.jsonl")
    return instance


def _set_response(llm, content, **kwargs):
    """Answer the next create() call, recording what it was sent.

    `llm.messages` is passed by reference and keeps growing after the
    call, so the sent conversation has to be copied on the way in.
    """
    sent = []
    completion = FakeCompletion(content, **kwargs)

    def _create(**call_kwargs):
        sent.append(list(call_kwargs["messages"]))
        return completion

    llm.client.chat.completions.create.side_effect = _create
    return sent


def _roles(messages):
    """The role of each message, dict or SDK object alike."""
    return [
        m["role"] if isinstance(m, dict) else "assistant" for m in messages
    ]


# --- construction and keys ---

def test_load_keys_keeps_only_the_names_defined_in_the_env(llm, monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert llm._load_keys(["KEY_1", "MISSING_KEY", "KEY_2"]) == [
        "first-key", "second-key",
    ]


def test_init_raises_value_error_when_no_key_is_defined(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(ValueError, match="MISSING_KEY"):
        LLM(
            api_url="http://fake.invalid/v1", model_name="m",
            env_keys=["MISSING_KEY"], system_content=SYSTEM,
        )


def test_init_starts_on_the_first_key(llm):
    assert llm._key_index == 0
    assert llm._api_keys == ["first-key", "second-key"]


def test_system_prompt_opens_the_conversation(llm):
    assert llm.messages == [{"role": "system", "content": SYSTEM}]


def test_next_key_rebuilds_the_client_on_the_second_key(llm):
    assert llm._next_key() is True
    assert llm._key_index == 1
    assert llm.client.api_key == "second-key"


def test_next_key_is_false_once_every_key_is_used(llm):
    llm._next_key()
    assert llm._next_key() is False
    assert llm._key_index == 1


# --- call(): rate limiting ---

def test_call_rotates_to_the_next_key_on_rate_limit(llm, monkeypatch):
    second = _mock_client("answer from the second key")
    monkeypatch.setattr(llm, "_load_llm", lambda: second)
    llm.client.chat.completions.create.side_effect = _rate_limit_error()

    result = llm.call("solve this")

    assert result["answer"] == "answer from the second key"
    assert result["retries"] == 1
    assert llm._key_index == 1
    assert llm.client is second


def test_call_counts_one_retry_per_rejected_attempt(llm, monkeypatch):
    llm._api_keys = ["first-key", "second-key", "third-key"]
    second = MagicMock()
    second.chat.completions.create.side_effect = _rate_limit_error()
    clients = iter([second, _mock_client("answer from the third key")])
    monkeypatch.setattr(llm, "_load_llm", lambda: next(clients))
    llm.client.chat.completions.create.side_effect = _rate_limit_error()

    result = llm.call("solve this")

    assert result["retries"] == 2
    assert result["answer"] == "answer from the third key"
    assert llm._key_index == 2


def test_call_counter_restarts_on_the_next_call(llm, monkeypatch):
    second = _mock_client("answer from the second key")
    monkeypatch.setattr(llm, "_load_llm", lambda: second)
    llm.client.chat.completions.create.side_effect = _rate_limit_error()
    assert llm.call("solve this")["retries"] == 1

    # the key index keeps moving forward, the retry counter does not
    assert llm.call("solve this")["retries"] == 0
    assert llm._key_index == 1


def test_call_raises_once_every_key_is_rate_limited(llm):
    llm._api_keys = ["only-key"]
    llm.client.chat.completions.create.side_effect = _rate_limit_error()
    with pytest.raises(ValueError, match="rate limited"):
        llm.call("solve this")


def test_call_reports_the_underlying_api_error(llm):
    llm.client.chat.completions.create.side_effect = RuntimeError("boom")
    with pytest.raises(ValueError, match="boom"):
        llm.call("solve this")


# --- call(): message construction ---

def test_call_first_call_has_system_and_user_only(llm):
    sent = _set_response(llm, "some code")
    llm.call("solve this")

    assert _roles(sent[0]) == ["system", "user"]
    assert sent[0][1]["content"] == "solve this"


def test_call_keeps_the_reply_in_the_conversation(llm):
    _set_response(llm, "first attempt")
    llm.call("solve this")
    sent = _set_response(llm, "second attempt")
    llm.call("ignored, the agent owns the conversation from now on")

    assert _roles(sent[0]) == ["system", "user", "assistant"]
    assert sent[0][2].content == "first attempt"


def test_call_forwards_what_the_agent_appended(llm):
    _set_response(llm, "first attempt")
    llm.call("solve this")

    llm.messages.append({"role": "user", "content": "AssertionError: nope"})
    sent = _set_response(llm, "second attempt")
    llm.call("solve this")

    assert _roles(sent[0]) == ["system", "user", "assistant", "user"]
    assert sent[0][3]["content"] == "AssertionError: nope"


# --- call(): thought/answer parsing ---

def test_call_parses_think_tag(llm):
    _set_response(llm, "reasoning here</think>final code")
    result = llm.call("x")
    assert result["thought"] == "reasoning here"
    assert result["answer"] == "final code"


def test_call_parses_thought_tag(llm):
    _set_response(llm, "reasoning here</thought>final code")
    result = llm.call("x")
    assert result["thought"] == "reasoning here"
    assert result["answer"] == "final code"


def test_call_parses_reasoning_attribute(llm):
    _set_response(llm, "final code", reasoning="separate reasoning")
    result = llm.call("x")
    assert result["thought"] == "separate reasoning"
    assert result["answer"] == "final code"


def test_call_no_marker_found(llm):
    _set_response(llm, "just the code, no markers")
    result = llm.call("x")
    assert result["thought"] == "No thought found"
    assert result["answer"] == "just the code, no markers"


# --- call(): returned metadata ---

def test_call_returns_token_counts_and_model_name(llm):
    _set_response(llm, "code", prompt_tokens=42, completion_tokens=7)
    result = llm.call("x")
    assert result["input_tokens"] == 42
    assert result["output_tokens"] == 7
    assert result["model_name"] == "fake-model"
    assert result["retries"] == 0
    assert result["tool_calls"] is None


def test_call_survives_a_provider_omitting_usage(llm):
    completion = FakeCompletion("code")
    completion.usage = None
    llm.client.chat.completions.create.return_value = completion

    result = llm.call("x")

    assert result["input_tokens"] is None
    assert result["output_tokens"] is None
    assert result["answer"] == "code"


# --- logging ---

def test_log_response_appends_one_json_line_per_call(llm, tmp_path):
    _set_response(llm, "first")
    llm.call("x")
    _set_response(llm, "second")
    llm.call("x")

    lines = (tmp_path / "llm_responses.jsonl").read_text().splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["model_name"] == "fake-model"
    assert entry["completion"]["content"] == "first"
    assert entry["timestamp"]


def test_log_response_is_skipped_without_a_log_file(llm, tmp_path):
    llm.log_file = None
    _set_response(llm, "code")
    llm.call("x")
    assert list(tmp_path.iterdir()) == []


def test_call_reports_the_request_time_in_milliseconds(llm, monkeypatch):
    """The field is named _ms and StepMetrics stores it as such."""
    _set_response(llm, "code")
    ticks = iter([10.0, 11.5])  # a 1.5 second call
    monkeypatch.setattr(calling.time, "perf_counter", lambda: next(ticks))

    result = llm.call("x")

    assert result["request_time_ms"] == 1500.0
