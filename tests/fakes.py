"""Test doubles for the agent loop (M0/M7, see split_work.md).

FakeLLM replays scripted responses at zero network/token cost.
FakeSandbox runs code with zero security (bare exec()) for fast,
isolated orchestrator tests. Neither is meant for real LLM-generated
code — only for testing the loop's own logic in isolation.
"""

import contextlib
import io
import json

from srcs.models import LLMResponse, SandboxResult


class FakeLLM:
    """Implements LLMClient by replaying a scripted list of responses
    from a JSON file, in order. Raises IndexError once the script is
    exhausted — a test that runs out of scripted turns is a bug in
    the test, not something to paper over silently."""

    def __init__(self, script_file: str) -> None:
        with open(script_file) as f:
            self._script = json.load(f)
        self._index = 0

    def complete(
            self, system: str, messages: list[dict],
            stop: list[str]) -> LLMResponse:
        """Return the next scripted response as an LLMResponse."""
        if self._index >= len(self._script):
            raise IndexError(
                f"FakeLLM script exhausted after {self._index} turn(s)"
            )
        entry = self._script[self._index]
        self._index += 1
        entry = {"text": entry} if isinstance(entry, str) else entry
        text = entry["text"]
        return LLMResponse(
            text=text,
            input_tokens=entry.get(
                "input_tokens",
                sum(len(m["content"].split()) for m in messages),
            ),
            output_tokens=entry.get("output_tokens", len(text.split())),
            request_time_ms=entry.get("request_time_ms", 0.0),
            api_url="fake://local",
            model_name="fake-llm",
            retries=entry.get("retries", 0),
        )


class FakeSandbox:
    """Bare exec(), no security — implements the same execute()/
    register_tool() surface as the real Sandbox so it can be
    injected in its place for orchestrator tests."""

    def __init__(self) -> None:
        self.namespace: dict = {"final_answer": self._final_answer}
        self._final_answer_value = None
        self._finished = False

    def register_tool(self, name: str, func) -> None:
        """Add a callable to the exec namespace, like an MCP wrapper."""
        self.namespace[name] = func

    def _final_answer(self, answer):
        self._final_answer_value = answer
        self._finished = True
        return answer

    def execute(self, code: str) -> SandboxResult:
        """Run `code` with exec(), no restrictions whatsoever."""
        self._finished = False
        self._final_answer_value = None
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, self.namespace)
            return SandboxResult(
                success=True,
                output=buf.getvalue(),
                error=None,
                final_answer=self._final_answer_value,
                finished=self._finished,
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                output=buf.getvalue(),
                error=f"{type(e).__name__}: {e}",
                final_answer=self._final_answer_value,
                finished=False,
            )
