"""Integration tests for srcs/backends/docker.py (DockerExecBackend).

These exercise a real Docker daemon and real containers — they are
skipped automatically if no daemon is reachable, so the suite still
runs cleanly on a machine without Docker.
"""

import docker
import pytest

from srcs.backends.docker import DockerExecBackend
from srcs.mcp_server import tools

IMAGE = "alpine:latest"


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)


@pytest.fixture
def backend():
    with DockerExecBackend(IMAGE, root="/work") as b:
        yield b


# --- Lifecycle / cleanup ---
# V.4: "Explore codebases inside Docker containers, you are
# responsible to clean it after your program execution" — and
# exam_swebench.sh explicitly grades "container cleanup" as a pass
# criterion, so this is not optional polish.

def test_container_removed_after_context_manager_exits():
    client = docker.from_env()
    with DockerExecBackend(IMAGE, root="/work") as b:
        container_id = b.container.id
        assert client.containers.get(container_id).status in (
            "running", "created",
        )
    with pytest.raises(docker.errors.NotFound):
        client.containers.get(container_id)


def test_orphan_container_purged_on_next_startup():
    """A container left behind by a crashed previous run (same
    label, never cleaned up) must be purged when a new backend
    starts — the safety net beyond __exit__/atexit."""
    client = docker.from_env()
    orphan = client.containers.run(
        IMAGE, command="sleep infinity", detach=True,
        labels={"agent-smith": "true"},
    )
    with DockerExecBackend(IMAGE, root="/work"):
        pass
    with pytest.raises(docker.errors.NotFound):
        client.containers.get(orphan.id)


# --- run() ---

def test_run_basic_command(backend):
    result = backend.run("echo hello", workdir="/work", timeout=5)
    assert result.stdout == "hello\n"
    assert result.exit_code == 0
    assert result.timed_out is False


def test_run_shell_operators_are_interpreted(backend):
    # Regression check: exec_run doesn't run a shell by default, cmd
    # must be wrapped in sh -c for `&&`/pipes/etc. to work at all.
    result = backend.run("echo one && echo two", workdir="/work", timeout=5)
    assert result.stdout == "one\ntwo\n"
    assert result.exit_code == 0


def test_run_captures_stderr(backend):
    result = backend.run("echo err 1>&2", workdir="/work", timeout=5)
    assert "err" in result.stderr


def test_run_creates_missing_workdir(backend):
    # Regression check: exec with a workdir that doesn't exist yet
    # used to fail with a misleading exit_code 127.
    result = backend.run("pwd", workdir="/work/new/sub", timeout=5)
    assert result.stdout.strip() == "/work/new/sub"
    assert result.exit_code == 0


def test_run_timeout_is_detected(backend):
    # Regression check: detection must not rely on `timeout`'s own
    # exit code, since it differs between GNU coreutils and BusyBox.
    result = backend.run("sleep 3", workdir="/work", timeout=1)
    assert result.timed_out is True


def test_run_fast_command_is_not_flagged_as_timed_out(backend):
    result = backend.run("echo fast", workdir="/work", timeout=5)
    assert result.timed_out is False


# --- read_file / write_file ---

def test_write_then_read_relative_path(backend):
    backend.write_file("foo.txt", "hello\n")
    assert backend.read_file("foo.txt") == "hello\n"


def test_write_file_creates_missing_parent_directories(backend):
    # Regression check: put_archive 404s if the destination
    # directory doesn't already exist.
    backend.write_file("sub/dir/foo.txt", "nested\n")
    assert backend.read_file("sub/dir/foo.txt") == "nested\n"


def test_read_file_with_absolute_path_inside_root(backend):
    backend.write_file("foo.txt", "x\n")
    assert backend.read_file("/work/foo.txt") == "x\n"


def test_read_file_missing_raises_oserror(backend):
    with pytest.raises(OSError):
        backend.read_file("missing.txt")


def test_read_file_relative_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.read_file("../../etc/passwd")


def test_read_file_absolute_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.read_file("/etc/passwd")


def test_write_file_escape_is_blocked(backend):
    with pytest.raises(PermissionError):
        backend.write_file("/etc/passwd", "pwned")


# --- V.4: "Generate and submit valid patches using
# 'git -c core.fileMode=false diff'" — same tools.get_patch()
# contract as LocalExecBackend, exercised here through a real
# container instead of the host filesystem. ---

def test_get_patch_produces_a_valid_diff_through_docker(backend):
    # The only call here that downloads. What this test is about is
    # get_patch(), not apk: when the install cannot complete, say so and
    # skip rather than fail three lines below on a missing git binary.
    installed = backend.run(
        "apk add --no-cache git", workdir="/work", timeout=120)
    if installed.exit_code != 0 or installed.timed_out:
        pytest.skip(f"git could not be installed: {installed.stderr[-200:]}")
    backend.run(
        "git init -q && git -c user.email=t@t -c user.name=t "
        "commit -q --allow-empty -m init",
        workdir="/work", timeout=15,
    )
    backend.write_file("calc.py", "def add(a, b):\n    return a - b\n")
    backend.run(
        "git add -A && git -c user.email=t@t -c user.name=t "
        "commit -q -m 'add calc.py'",
        workdir="/work", timeout=15,
    )

    tools.edit_file(backend, "calc.py", "a - b", "a + b")
    patch = tools.get_patch(backend)

    assert "calc.py" in patch
    assert "+    return a + b" in patch
    assert "__pycache__" not in patch
