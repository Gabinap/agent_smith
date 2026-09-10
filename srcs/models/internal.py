"""Internal data contracts, not imposed by the subject."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "CommandResult",
    "ExecutionResult",
    "ExtractedAction",
    "McpSpec",
    "Observation",
]


class ExtractedAction(BaseModel):
    """Hold the Python code extracted from a raw LLM response."""

    code: str
    source_format: Literal["python", "xml", "json", "react"]
    warnings: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Hold the outcome of one sandbox execution."""

    stdout: str
    stderr: str
    error: str | None = None
    final_answer: str | None = None
    timed_out: bool = False
    truncated: bool = False


class Observation(BaseModel):
    """Hold the feedback text sent back to the LLM after an execution."""

    text: str
    kind: Literal[
        "ok", "no_code", "malformed", "timeout", "truncated",
        "syntax_error", "tool_error",
    ]


class CommandResult(BaseModel):
    """Hold the raw result of a shell command run by an ExecBackend."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


class McpSpec(BaseModel):
    """Describe how to reach the MCP server relevant to a given task."""

    transport: Literal["stdio", "http"]
    env: dict[str, str] | None = Field(
        default=None, description="Environment variables for stdio transport."
    )
    command: str | None = Field(
        default=None, description="Shell command for stdio transport."
    )
    url: str | None = Field(
        default=None, description="Server URL for HTTP transport."
    )
