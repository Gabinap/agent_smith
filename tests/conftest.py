"""Shared pytest fixtures for the test suite."""

import pytest

from srcs.backends.local import LocalExecBackend


@pytest.fixture
def backend(tmp_path) -> LocalExecBackend:
    """A LocalExecBackend rooted at a fresh, empty temp directory."""
    return LocalExecBackend(root=str(tmp_path / "root"))


@pytest.fixture
def sample_repo(backend: LocalExecBackend) -> LocalExecBackend:
    """A backend pre-populated with a tiny two-file Python codebase."""
    backend.write_file("foo.py", "def helper(x):\n    return x + 1\n")
    backend.write_file(
        "sub/bar.py",
        "from foo import helper\n\n\ndef use_it():\n    return helper(2)\n",
    )
    return backend
