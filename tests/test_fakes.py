"""Unit tests for the FakeLLM/FakeSandbox test doubles (tests/fakes.py)."""

import json

import pytest

from tests.fakes import FakeLLM, FakeSandbox


def test_fake_llm_replays_scripted_responses(tmp_path):
    script = tmp_path / "script.json"
    script.write_text(json.dumps(["first turn", "second turn"]))
    llm = FakeLLM(str(script))

    r1 = llm.complete("sys", [{"role": "user", "content": "hi"}], [])
    r2 = llm.complete("sys", [{"role": "user", "content": "hi"}], [])

    assert r1.text == "first turn"
    assert r2.text == "second turn"


def test_fake_llm_raises_once_exhausted(tmp_path):
    script = tmp_path / "script.json"
    script.write_text(json.dumps(["only turn"]))
    llm = FakeLLM(str(script))
    llm.complete("sys", [], [])

    with pytest.raises(IndexError):
        llm.complete("sys", [], [])


def test_fake_llm_honors_explicit_token_counts(tmp_path):
    script = tmp_path / "script.json"
    script.write_text(json.dumps(
        [{"text": "x", "input_tokens": 42, "output_tokens": 7}]
    ))
    llm = FakeLLM(str(script))

    r = llm.complete("sys", [], [])

    assert r.input_tokens == 42
    assert r.output_tokens == 7


def test_fake_sandbox_captures_stdout():
    sandbox = FakeSandbox()
    result = sandbox.execute("print('hi')")
    assert result.success is True
    assert result.output == "hi\n"
    assert result.finished is False


def test_fake_sandbox_final_answer_marks_finished():
    sandbox = FakeSandbox()
    result = sandbox.execute("final_answer('done')")
    assert result.finished is True
    assert result.final_answer == "done"


def test_fake_sandbox_reports_exceptions():
    sandbox = FakeSandbox()
    result = sandbox.execute("1 / 0")
    assert result.success is False
    assert "ZeroDivisionError" in result.error


def test_fake_sandbox_register_tool_is_callable_from_code():
    sandbox = FakeSandbox()
    sandbox.register_tool("shout", lambda s: s.upper())
    result = sandbox.execute("final_answer(shout('hi'))")
    assert result.final_answer == "HI"
