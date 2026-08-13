"""Task inputs and sandbox configuration imposed by the assignment."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "MBPPTaskInput", "SWEBenchTaskInput", "TaskInput",
]


class MBPPTaskInput(BaseModel):
    """Hold one MBPP (Mostly Basic Python Problems) task definition."""

    task_id: int
    task_definition: str
    function_definition: str
    test_imports: list[str] = Field(default_factory=list)
    test_list: list[str] = Field(default_factory=list)


class SWEBenchTaskInput(BaseModel):
    """Hold one SWE-bench issue that the agent must fix with a git
    patch."""

    instance_id: str = Field(
        ...,
        description="SWE-bench instance identifier, e.g. "
        "'sympy__sympy-23534'.",
    )
    problem_statement: str = Field(
        ..., description="GitHub issue description of what must be "
        "fixed."
    )
    docker_image: str = Field(
        ..., description="Full Docker image name to pull for this "
        "instance."
    )
    eval_script: str = Field(
        ..., description="Bash script that evaluates the patch "
        "inside the container."
    )
    hints_text: str = Field(
        default="", description="Optional hints about the issue."
    )
    repo: str = Field(
        default="", description="Repository name, e.g. 'sympy/sympy'."
    )


TaskInput = MBPPTaskInput | SWEBenchTaskInput
"""Either an MBPP or a SWE-bench task, as returned by
BenchmarkAdapter.load_task."""
