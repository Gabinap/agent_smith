
import pathlib

from pydantic import BaseModel, ConfigDict, Field


class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions.
    Uses allowlist approach: only imports in authorized_imports are allowed.
    Everything else is blocked by default.
    """
    authorized_imports: list[str] = Field(default_factory=lambda: [
        "math", "math.*",
        "collections", "collections.*",
        "itertools", "re", "json",
        "typing", "typing.*",
        "functools", "operator",
        "heapq", "bisect", "copy",
        "string", "random",
        "datetime", "datetime.*",
        "array", "cmath",
    ])
    allowed_directories: list[str] = Field(default_factory=lambda: [
        "/testbed", "/tmp/agent"
    ])
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512

    @classmethod
    def from_file(cls, path: pathlib.Path) -> "SandboxConfig":
        """Read a policy template, falling back to these defaults.

        A missing or malformed template degrades to the built-in
        policy rather than stopping a run: the defaults above are
        already safe, so the worst case is a less tailored sandbox,
        never an open one.
        """
        if not path.is_file():
            return cls()
        try:
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return cls()


class SandboxResult(BaseModel):
    model_config = ConfigDict(extra='ignore')
    success: bool
    output: str
    error: str | None
    final_answer: str | None = None
    finished: bool
