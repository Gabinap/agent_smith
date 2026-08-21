"""Tests for M7 (srcs/agents/orchestrator.py), against the module's
own "fini quand": the loop resolves an MBPP-like task end to end
with FakeLLM/FakeSandbox, and the SolutionOutput is well-formed.
"""

import json

from orchestration.orchestrator import AgentLoop, AgentLoopConfig
from models import MBPPTaskInput
from tests.fakes import FakeLLM, FakeSandbox


class _FakeAdapter:
    """Minimal BenchmarkAdapter stand-in — only the two methods
    AgentLoop actually calls."""

    def build_user_prompt(self, task) -> str:
        return f"Solve: {task.task_definition}"

    def finalize(self, final_answer_value: str) -> str:
        return final_answer_value


def _task() -> MBPPTaskInput:
    return MBPPTaskInput(
        task_id=1,
        task_definition="Write add(a, b).",
        function_definition="def add(a, b):",
        test_imports=[],
        test_list=["assert add(2, 3) == 5"],
    )


def _config(**overrides) -> AgentLoopConfig:
    defaults = dict(
        max_iterations=10, max_input_tokens=6000,
        max_output_tokens=1500, max_time_seconds=120,
    )
    defaults.update(overrides)
    return AgentLoopConfig(**defaults)


def _script(tmp_path, entries) -> str:
    path = tmp_path / "script.json"
    path.write_text(json.dumps(entries))
    return str(path)


def test_solves_a_task_end_to_end(tmp_path):
    script = _script(tmp_path, [
        "```python\n"
        "final_answer('def add(a, b):\\n    return a + b')\n"
        "```"
    ])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(), _config(),
    )

    output = loop.run(_task())

    assert output.success is True
    assert output.task_id == "1"
    assert output.benchmark == "mbpp"
    assert "return a + b" in output.solution
    assert output.iterations == 1
    assert output.error is None


def test_max_iterations_reached_without_final_answer(tmp_path):
    script = _script(tmp_path, ["```python\nprint('still going')\n```"] * 3)
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(),
        _config(max_iterations=3),
    )

    output = loop.run(_task())

    assert output.success is False
    assert output.iterations == 3
    assert "max_iterations" in output.error


def test_no_code_block_produces_no_code_observation(tmp_path):
    script = _script(tmp_path, ["just some prose, no code fence at all"])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(),
        _config(max_iterations=1),
    )

    output = loop.run(_task())

    assert output.steps[0].sandbox_output.startswith("No code block found")


def test_malformed_fence_is_interpreted_and_flagged(tmp_path):
    # missing the "python" tag on the fence
    script = _script(tmp_path, ["```\nfinal_answer('ok')\n```"])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(), _config(),
    )

    output = loop.run(_task())

    assert output.success is True
    assert "note:" in output.steps[0].sandbox_output


def test_runtime_error_produces_tool_error_observation(tmp_path):
    script = _script(tmp_path, ["```python\n1 / 0\n```"])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(),
        _config(max_iterations=1),
    )

    output = loop.run(_task())

    assert "ZeroDivisionError" in output.steps[0].sandbox_output


def test_budget_exhausted_stops_before_next_call(tmp_path):
    # Checked *before* each call against spend so far, not a
    # prediction of the next call's cost — so with 100 tokens/call
    # and a 150 budget, iteration 2 still starts under budget (100 <
    # 150) and is allowed; only iteration 3 would be blocked. A 3rd
    # scripted entry is deliberately omitted: reaching it would mean
    # the cutoff failed to kick in.
    script = _script(tmp_path, [
        {"text": "```python\nprint('a')\n```", "input_tokens": 100,
         "output_tokens": 100},
        {"text": "```python\nprint('b')\n```", "input_tokens": 100,
         "output_tokens": 100},
    ])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(),
        _config(max_input_tokens=150, max_output_tokens=1500),
    )

    output = loop.run(_task())

    assert output.success is False
    assert output.iterations == 2
    assert "budget" in output.error


def test_long_output_is_truncated(tmp_path):
    script = _script(tmp_path, ["```python\nprint('x' * 50)\n```"])
    loop = AgentLoop(
        FakeLLM(script), FakeSandbox(), _FakeAdapter(),
        _config(max_iterations=1, max_observation_chars=10),
    )

    output = loop.run(_task())

    assert "truncated" in output.steps[0].sandbox_output
