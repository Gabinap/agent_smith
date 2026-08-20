"""Unit tests for srcs/sandbox/sandbox.py (the Sandbox security
boundary)."""

import pytest

from srcs.models.sandbox import SandboxConfig
from srcs.sandbox.sandbox import Sandbox


@pytest.fixture
def sandbox():
    return Sandbox()


# --- Basic execution ---

def test_execute_runs_code_and_captures_print(sandbox):
    result = sandbox.execute("print('hello', 'world')")
    assert result.success is True
    assert result.output == "hello world\n"
    assert result.error is None


def test_print_does_not_reach_real_stdout(sandbox, capsys):
    sandbox.execute("print('should not reach the real terminal')")
    assert capsys.readouterr().out == ""


def test_uncaught_exception_returns_failure_not_crash(sandbox):
    result = sandbox.execute("1 / 0")
    assert result.success is False
    assert "ZeroDivisionError" in result.error


# --- Import allowlist ---

def test_allowed_import_succeeds(sandbox):
    result = sandbox.execute("import math\nprint(math.sqrt(16))")
    assert result.success is True
    assert result.output == "4.0\n"


def test_disallowed_import_is_blocked(sandbox):
    result = sandbox.execute("import os")
    assert result.success is False
    assert "SecurityError" in result.error


def test_wildcard_import_pattern_allows_submodules(sandbox):
    result = sandbox.execute("import collections.abc")
    assert result.success is True


def test_is_import_allowed_exact_and_wildcard(sandbox):
    assert sandbox._is_import_allowed("math") is True
    assert sandbox._is_import_allowed("collections.abc") is True
    assert sandbox._is_import_allowed("os") is False
    assert sandbox._is_import_allowed("subprocess") is False


# --- Restricted builtins ---

@pytest.mark.parametrize("name", ["eval", "exec", "input", "compile"])
def test_dangerous_builtins_are_removed(sandbox, name):
    result = sandbox.execute(f"{name}('x')")
    assert result.success is False
    assert "NameError" in result.error


# --- File access allowlist ---

def test_open_inside_allowed_directory_succeeds(tmp_path):
    config = SandboxConfig(allowed_directories=[str(tmp_path)])
    sandbox = Sandbox(config=config)
    target = tmp_path / "foo.txt"
    target.write_text("hi")
    result = sandbox.execute(
        f"f = open({str(target)!r}); print(f.read()); f.close()"
    )
    assert result.success is True
    assert result.output == "hi\n"


def test_open_outside_allowed_directory_is_blocked(tmp_path):
    config = SandboxConfig(allowed_directories=[str(tmp_path / "allowed")])
    sandbox = Sandbox(config=config)
    outside = tmp_path / "outside" / "secret.txt"
    result = sandbox.execute(f"open({str(outside)!r})")
    assert result.success is False
    assert "SecurityError" in result.error


def test_is_open_allowed(tmp_path):
    config = SandboxConfig(allowed_directories=[str(tmp_path)])
    sandbox = Sandbox(config=config)
    assert sandbox._is_open_allowed(str(tmp_path / "x.txt")) is True
    assert sandbox._is_open_allowed("/etc/passwd") is False


# --- Timeout ---

def test_infinite_loop_is_killed_by_timeout():
    config = SandboxConfig(max_execution_time_seconds=1)
    sandbox = Sandbox(config=config)
    result = sandbox.execute("while True:\n    pass")
    assert result.success is False
    assert "TimeoutError" in result.error


# --- final_answer() ---

def test_final_answer_sets_finished_and_value(sandbox):
    result = sandbox.execute('final_answer("done")')
    assert result.finished is True
    assert result.final_answer == "done"


def test_final_answer_coerces_non_string(sandbox):
    # Regression check: type hints alone don't stop exec()'d code from
    # passing a non-string, which used to crash SandboxResult validation.
    result = sandbox.execute("final_answer(42)")
    assert result.success is True
    assert result.final_answer == "42"


def test_final_answer_and_finished_do_not_leak_across_calls(sandbox):
    # Regression check: only stdout used to be reset between calls.
    sandbox.execute('final_answer("first")')
    result = sandbox.execute("x = 1")
    assert result.finished is False
    assert result.final_answer is None


def test_stdout_does_not_leak_across_calls(sandbox):
    sandbox.execute("print('first run')")
    result = sandbox.execute("x = 1")
    assert result.output == ""


# --- register_tool() ---

def test_register_tool_makes_function_callable(sandbox):
    sandbox.register_tool("greet", lambda name: f"hi {name}")
    result = sandbox.execute('print(greet("bob"))')
    assert result.success is True
    assert result.output == "hi bob\n"


# --- KeyboardInterrupt / SystemExit must propagate, never be caught ---

def test_keyboard_interrupt_propagates(sandbox):
    with pytest.raises(KeyboardInterrupt):
        sandbox.execute("raise KeyboardInterrupt()")


def test_system_exit_propagates(sandbox):
    with pytest.raises(SystemExit):
        sandbox.execute("raise SystemExit()")
