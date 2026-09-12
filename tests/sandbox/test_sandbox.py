"""Unit tests for srcs/sandbox/sandbox.py (the Sandbox security
boundary)."""

from types import ModuleType

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
    # eval/exec/compile are refused by the AST guard before running;
    # input is simply absent from the builtins.
    assert ("forbidden by sandbox policy" in result.error
            or "NameError" in result.error)


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


# --- Kernel-enforced resource limits (_limit_resource) ---

def test_memory_limit_turns_a_huge_allocation_into_an_error(sandbox):
    result = sandbox.execute("x = [0] * 10 ** 9")
    assert result.success is False
    assert "MemoryError" in result.error


def test_file_size_limit_stops_a_runaway_write(tmp_path):
    sandbox = Sandbox(
        config=SandboxConfig(allowed_directories=[str(tmp_path)]))
    target = tmp_path / "big.txt"

    result = sandbox.execute(
        f"f = open({str(target)!r}, 'w')\n"
        "f.write('x' * 11_000_000)\n"
        "f.close()\n"
    )

    assert result.success is False
    assert "too large" in result.error.lower()
    assert target.stat().st_size <= 10 * 1024 * 1024


def test_an_escaped_payload_still_cannot_spawn_a_shell(sandbox, tmp_path):
    """The namespace can be walked out of; the kernel limits still hold.

    Reaching os through a bound method's __globals__ is what the AST
    guard is meant to stop. Until it lands — and if it is ever bypassed
    — RLIMIT_NPROC must keep the shell from ever running.
    """
    marker = tmp_path / "pwned.txt"

    sandbox.execute(
        "os = final_answer.__globals__['os']\n"
        f"os.system('touch {marker}')\n"
    )

    assert not marker.exists()


def test_injected_callables_lead_to_no_module_or_capability(sandbox):
    """`injected.__globals__` is this module's globals: keep it a dead end.

    Sandboxed code reaches it through any injected callable, so nothing
    there may hand out a capability: no module, and no unrestricted
    open() or __import__() bound at module level.
    """
    reachable = sandbox._final_answer_tool.__globals__

    assert [k for k, v in reachable.items()
            if isinstance(v, ModuleType)] == []
    assert "_real_open" not in reachable
    assert "_real_import" not in reachable


# --- Layer 1: AST escape guard (_EscapeVisitor) ---

BLOCKED_PAYLOADS = {
    "subclasses": "().__class__.__bases__[0].__subclasses__()",
    "func_globals": "print(final_answer.__globals__)",
    "builtins_bare": "__builtins__['__import__']('os')",
    "import_bare": "__import__('os')",
    "eval_call": "eval('1+1')",
    "getattr_bypass": "getattr((), '__class__')",
    "format_dunder": '"{0.__class__}".format(())',
    "super_thisclass": (
        "class A:\n"
        "    def f(self):\n"
        "        return super().__thisclass__\n"
        "A().f()"
    ),
    "traceback_walk": (
        "try:\n"
        "    1 / 0\n"
        "except Exception as e:\n"
        "    print(e.__traceback__.tb_frame.f_globals)"
    ),
}


@pytest.mark.parametrize("code", BLOCKED_PAYLOADS.values(),
                         ids=BLOCKED_PAYLOADS.keys())
def test_escape_payloads_are_rejected(sandbox, code):
    result = sandbox.execute(code)
    assert result.success is False
    assert "forbidden by sandbox policy" in result.error


LEGITIMATE_CODE = {
    "class_with_init": (
        "class Point:\n"
        "    def __init__(self, x):\n"
        "        self.x = x\n"
        "print(Point(3).x)"
    ),
    "super_call": (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.v = 1\n"
        "class B(A):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "print(B().v)"
    ),
    "name_main_guard": (
        "def solve():\n"
        "    return 42\n"
        "if __name__ == '__main__':\n"
        "    print(solve())"
    ),
    "fstring": "x = 5\nprint(f'value is {x}')",
    "format_normal": "print('{} + {} = {}'.format(1, 2, 3))",
    "dunder_in_a_plain_string": "print('rename self.__class__ here')",
}


@pytest.mark.parametrize("code", LEGITIMATE_CODE.values(),
                         ids=LEGITIMATE_CODE.keys())
def test_legitimate_code_still_runs(sandbox, code):
    result = sandbox.execute(code)
    assert result.success is True, result.error
