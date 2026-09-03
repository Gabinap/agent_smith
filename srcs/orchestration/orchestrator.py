"""The generic Thought -> Code -> Observation agent loop, shared by
agent_mbpp and agent_swebench.

Design notes / known simplifications, flagged rather than hidden:

- There is no multi-format (python/XML/JSON/ReAct) extractor yet.
  `_default_extract` is a minimal python-block-only stand-in — swap
  it via the `extract` constructor param once a real one lands; the
  rest of the loop doesn't need to change.
- The real `LLM` class (call_llm/calling.py) doesn't implement the
  `complete(system, messages, stop) -> LLMResponse` shape this loop
  expects — it needs a small adapter before it can replace FakeLLM
  here. Not written yet; flagged, not silently worked around.
- `SandboxResult` (models/sandbox.py) has no structured error *kind*,
  just a free-text `error` string. Timeout/syntax-error detection
  below matches on that string's prefix — fragile, but it's the only
  signal the current contract provides.
- Token budget is enforced by checking spend accumulated so far
  *before* issuing the next call, not by predicting that call's own
  cost (no tokenizer available here) — never start a call once
  already at budget, rather than catching the overshoot after.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from models import (
    ExtractedAction,
    LLMResponse,
    MBPPTaskInput,
    Observation,
    SolutionOutput,
    StepMetrics,
    TaskInput,
)


class _SandboxLike(Protocol):
    """What AgentLoop needs from a sandbox — satisfied by both the
    real Sandbox and FakeSandbox."""

    def execute(self, code: str):
        """Run `code` and return a SandboxResult-shaped object."""
        ...

    def register_tool(self, name: str, func) -> None:
        """Add a callable to the exec namespace under `name`."""
        ...


class _LLMLike(Protocol):
    """What AgentLoop needs from an LLM client."""

    def complete(
        self, system: str, messages: list[dict], stop: list[str]
    ) -> LLMResponse:
        """Request a completion and return the parsed response."""
        ...


class _AdapterLike(Protocol):
    """What AgentLoop needs from a benchmark adapter."""

    def build_user_prompt(self, task: TaskInput) -> str:
        """Build the first user message describing the task."""
        ...

    def finalize(self, final_answer_value: str) -> str:
        """Turn the raw final_answer into the benchmark's solution
        format."""
        ...


def _default_extract(text: str) -> ExtractedAction:
    """Minimal python-code-fence extractor — a stand-in for a real
    multi-format (XML/JSON/ReAct) extractor. Swap via `extract=`
    once one exists."""
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if match:
        return ExtractedAction(
            code=match.group(1), source_format="python", warnings=[],
        )
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        return ExtractedAction(
            code=match.group(1), source_format="python",
            warnings=["missing 'python' language tag on code fence"],
        )
    return ExtractedAction(code="", source_format="python", warnings=[])


@dataclass
class _ActResult:
    """Outcome of running one extracted action through the sandbox."""

    observation: Observation
    sandbox_input: str
    finished: bool
    final_answer: str | None


def _task_id(task: TaskInput) -> str:
    """Return MBPP's task_id or SWE-bench's instance_id, as a string."""
    if isinstance(task, MBPPTaskInput):
        return str(task.task_id)
    return task.instance_id


def _benchmark_name(task: TaskInput) -> str:
    """Return "mbpp" or "swebench" depending on the task's type."""
    return "mbpp" if isinstance(task, MBPPTaskInput) else "swebench"


class AgentLoopConfig:
    """Limits for one AgentLoop run (iterations, token budget,
    wall-clock timeout)."""

    def __init__(
            self, max_iterations: int, max_input_tokens: int,
            max_output_tokens: int, max_time_seconds: float,
            max_observation_chars: int = 4000,
            stop_sequences: list[str] | None = None) -> None:
        """Store the run's limits; `stop_sequences` defaults to
        ["<end_code>"] if not given."""
        self.max_iterations = max_iterations
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.max_time_seconds = max_time_seconds
        self.max_observation_chars = max_observation_chars
        self.stop_sequences = stop_sequences or ["<end_code>"]


class AgentLoop:
    """AgentLoop(llm, sandbox, adapter, config).run(task) ->
    SolutionOutput — generic over the benchmark; agent_mbpp and
    agent_swebench only supply the adapter and the limits."""

    def __init__(
            self, llm: _LLMLike, sandbox: _SandboxLike,
            adapter: _AdapterLike, config: AgentLoopConfig,
            system_prompt: str = "",
            extract: Callable[[str], ExtractedAction] = _default_extract,
            ) -> None:
        """Wire the loop's dependencies; nothing runs until run()
        is called."""
        self.llm = llm
        self.sandbox = sandbox
        self.adapter = adapter
        self.config = config
        self.system_prompt = system_prompt
        self.extract = extract

    def run(self, task: TaskInput) -> SolutionOutput:
        """Run the loop to completion (final_answer, a limit hit, or
        an unrecoverable error) and return the SolutionOutput."""
        start = datetime.now()
        messages: list[dict] = [
            {"role": "user", "content": self.adapter.build_user_prompt(task)}
        ]
        steps: list[StepMetrics] = []
        total_in = total_out = 0
        error: str | None = None
        solution = ""
        success = False

        for step in range(1, self.config.max_iterations + 1):
            if self._budget_exhausted(total_in, total_out):
                error = "token budget exhausted before next call"
                break

            response = self.llm.complete(
                self.system_prompt, messages, self.config.stop_sequences,
            )
            total_in += response.input_tokens
            total_out += response.output_tokens
            messages.append({"role": "assistant", "content": response.text})

            action = self.extract(response.text)
            act_result = self._act(action)
            observation = act_result.observation
            messages.append(
                {"role": "user", "content": observation.text}
            )

            steps.append(StepMetrics(
                step=step,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                request_time_ms=response.request_time_ms,
                api_url=response.api_url,
                model_name=response.model_name,
                llm_output=response.text,
                sandbox_input=act_result.sandbox_input,
                sandbox_output=observation.text,
                retries=response.retries,
            ))

            if act_result.finished:
                success = True
                solution = self.adapter.finalize(act_result.final_answer)
                break
        else:
            error = f"max_iterations ({self.config.max_iterations}) reached"

        if (
            datetime.now() - start
        ).total_seconds() > self.config.max_time_seconds:
            success = False
            error = error or "global timeout exceeded"

        return SolutionOutput(
            task_id=_task_id(task),
            benchmark=_benchmark_name(task),
            success=success,
            solution=solution,
            iterations=len(steps),
            total_requests=len(steps),
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_time_seconds=(datetime.now() - start).total_seconds(),
            steps=steps,
            system_prompt=self.system_prompt,
            error=error,
        )

    def _budget_exhausted(self, total_in: int, total_out: int) -> bool:
        """True once spend so far has reached either token limit."""
        return (
            total_in >= self.config.max_input_tokens
            or total_out >= self.config.max_output_tokens
        )

    def _act(self, action: ExtractedAction) -> _ActResult:
        """Execute the extracted code (if any) and turn the result
        into an unambiguous Observation covering every outcome: no
        code found, a malformed-but-recovered block, a timeout, a
        syntax error, a generic failure, ordinary output, or output
        truncated by size."""
        if not action.code:
            return _ActResult(
                observation=Observation(
                    text="No code block found in your response. "
                         "Write your code inside a ```python ... ``` "
                         "block.",
                    kind="no_code",
                ),
                sandbox_input="", finished=False, final_answer=None,
            )

        result = self.sandbox.execute(action.code)
        error = result.error or ""
        if "TimeoutError" in error:
            kind = "timeout"
            text = (
                f"Execution timed out. Partial output:\n{result.output}"
            )
        elif "SyntaxError" in error:
            kind = "syntax_error"
            text = f"Your edit introduced a syntax error:\n{error}"
        elif not result.success:
            kind = "tool_error"
            text = f"Execution failed:\n{error}"
        else:
            kind = "ok"
            text = result.output

        if action.warnings:
            kind = "malformed" if kind == "ok" else kind
            text = (
                f"(note: {'; '.join(action.warnings)}, "
                f"interpreted as Python anyway)\n{text}"
            )

        truncated = len(text) > self.config.max_observation_chars
        if truncated:
            kind = "truncated" if kind == "ok" else kind
            text = text[: self.config.max_observation_chars] + (
                "\n[...output truncated...]"
            )

        return _ActResult(
            observation=Observation(text=text, kind=kind),
            sandbox_input=action.code,
            finished=bool(result.finished),
            final_answer=result.final_answer,
        )
