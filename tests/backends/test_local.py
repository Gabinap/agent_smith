"""Unit tests for srcs/backends/local.py (LocalExecBackend)."""

import pytest


def test_write_then_read_relative_path(backend):
    backend.write_file("foo.py", "print('hi')\n")
    assert backend.read_file("foo.py") == "print('hi')\n"


def test_write_file_creates_parent_directories(backend):
    backend.write_file("sub/dir/foo.py", "x = 1\n")
    assert backend.read_file("sub/dir/foo.py") == "x = 1\n"


def test_read_file_missing_raises_oserror(backend):
    with pytest.raises(OSError):
        backend.read_file("missing.py")


def test_read_file_with_absolute_path_inside_root(backend):
    backend.write_file("foo.py", "x = 1\n")
    abs_path = str(backend.root / "foo.py")
    assert backend.read_file(abs_path) == "x = 1\n"


def test_read_file_relative_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.read_file("../../etc/passwd")


def test_read_file_absolute_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.read_file("/etc/passwd")


def test_write_file_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.write_file("/etc/passwd", "pwned")


def test_run_executes_in_given_workdir(backend):
    backend.write_file("marker.txt", "hello\n")
    result = backend.run(
        "cat marker.txt", workdir=str(backend.root), timeout=5,
    )
    assert result.stdout == "hello\n"
    assert result.exit_code == 0


def test_run_captures_stderr_and_nonzero_exit(backend):
    result = backend.run(
        "ls no_such_file", workdir=str(backend.root), timeout=5,
    )
    assert result.exit_code != 0
    assert result.stderr != ""


def test_run_escape_workdir_returns_error_result(backend):
    result = backend.run("pwd", workdir="/etc", timeout=5)
    assert result.exit_code != 0
    assert "escapes backend root" in result.stderr


def test_run_timeout(backend):
    result = backend.run("sleep 2", workdir=str(backend.root), timeout=1)
    assert result.timed_out is True
    assert result.exit_code == -1
