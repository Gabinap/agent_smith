"""Structural protocols implemented by concrete backends, clients,
and adapters."""

from __future__ import annotations

from typing import Protocol

from .internal import CommandResult, LLMResponse, McpSpec
from .tasks import SandboxConfig, TaskInput

__all__ = ["ExecBackend", "LLMClient", "BenchmarkAdapter"]


class ExecBackend(Protocol):
    """Run commands and read/write files, locally or inside a container."""

    def run(self, cmd: str, workdir: str, timeout: int) -> CommandResult:
        """Run a shell command and return its result."""
        ...

    def read_file(self, path: str) -> str:
        """Return the raw text content of a file."""
        ...

    def write_file(self, path: str, content: str) -> None:
        """Overwrite a file with the given content."""
        ...


class LLMClient(Protocol):
    """Send chat completions to an LLM provider."""

    def complete(
        self, system: str, messages: list[dict], stop: list[str]
    ) -> LLMResponse:
        """Request a completion and return the parsed response."""
        ...


class BenchmarkAdapter(Protocol):
    """Adapt the generic agent loop to one benchmark (MBPP or SWE-bench)."""

    def load_task(self, path: str) -> TaskInput:
        """Load a task definition from a JSON file."""
        ...

    def build_user_prompt(self, task: TaskInput) -> str:
        """Build the first user message describing the task."""
        ...

    def mcp_spec(self, task: TaskInput) -> McpSpec:
        """Describe which MCP server to connect to for this task."""
        ...

    def sandbox_config(self, task: TaskInput) -> SandboxConfig:
        """Build the sandbox configuration to use for this task."""
        ...

    def finalize(self, final_answer_value: str) -> str:
        """Turn the agent's final answer into the benchmark's
        solution format."""
        ...
