"""Unit tests for srcs/mcp_server/tools.py — the M5 mandatory tools."""

import re
import subprocess

from srcs.mcp_server import tools


# --- M5 "fini quand": compare against the real cat -n / grep -rn ---

def test_read_file_matches_cat_n(sample_repo):
    real = subprocess.run(
        ["/usr/bin/cat", "-n", "foo.py"],
        cwd=sample_repo.root, capture_output=True, text=True,
    ).stdout
    # /usr/bin/cat -n right-pads/aligns "<n>\t<content>"; tools.read_file
    # uses the subject's literal "<n>: <content>" — normalize both.
    expected = "\n".join(
        f"{n.strip()}: {content}"
        for n, content in (line.split("\t", 1) for line in real.splitlines())
    )
    assert tools.read_file(sample_repo, "foo.py") == expected


def test_search_code_matches_grep_rn(sample_repo):
    raw = subprocess.run(
        ["grep", "-rn", "--include=*.py", "helper", "."],
        cwd=sample_repo.root, capture_output=True, text=True,
    ).stdout
    root = str(sample_repo.root)
    expected = set()
    for entry in raw.splitlines():
        path, lineno, content = entry.split(":", 2)
        expected.add(f"{root}/{path.removeprefix('./')}:{lineno} {content}")

    got = set(tools.search_code(sample_repo, "helper", "*.py").splitlines())
    assert got == expected


# --- Files tools ---

def test_read_file_start_end_line(sample_repo):
    assert (
        tools.read_file(sample_repo, "foo.py", start_line=2, end_line=2)
        == "2:     return x + 1"
    )


def test_read_file_missing_file_returns_error(backend):
    assert tools.read_file(backend, "missing.py").startswith("error:")


def test_read_file_invalid_range_returns_error(sample_repo):
    assert tools.read_file(
        sample_repo, "foo.py", start_line=0,
    ).startswith("error:")


def test_edit_file_replaces_unique_occurrence(sample_repo):
    result = tools.edit_file(sample_repo, "foo.py", "x + 1", "x + 2")
    assert result.startswith("ok:")
    assert "x + 2" in sample_repo.read_file("foo.py")


def test_edit_file_not_found_returns_error(sample_repo):
    result = tools.edit_file(sample_repo, "foo.py", "not_there", "x")
    assert "not found" in result


def test_edit_file_ambiguous_returns_error(backend):
    backend.write_file("dup.py", "x = 1\nx = 1\n")
    result = tools.edit_file(backend, "dup.py", "x = 1", "x = 2")
    assert "must be unique" in result


def test_list_files_matches_pattern(sample_repo):
    result = tools.list_files(sample_repo, str(sample_repo.root), "*.py")
    assert result.strip().endswith("foo.py")


def test_list_files_nonexistent_directory_is_error(backend):
    result = tools.list_files(backend, str(backend.root / "nope"), "*")
    assert result.startswith("error:")


# --- Search tools ---

def test_search_function_or_class_definition_in_code(sample_repo):
    result = tools.search_function_or_class_definition_in_code(
        sample_repo, "helper",
    )
    assert result.endswith("foo.py:1 def helper(x):")


def test_search_function_or_class_definition_finds_async_def(backend):
    backend.write_file("a.py", "async def fetch(x):\n    return x\n")
    result = tools.search_function_or_class_definition_in_code(
        backend, "fetch",
    )
    assert "async def fetch(x):" in result


def test_find_references_excludes_own_definition(sample_repo):
    result = tools.find_references(sample_repo, "helper")
    assert "def helper(x):" not in result
    assert "helper(2)" in result


def test_find_references_filepath_line_excludes_given_site(backend):
    backend.write_file("c.py", "CONST = 1\nprint(CONST)\n")

    unfiltered = tools.find_references(backend, "CONST")
    assert len(unfiltered.splitlines()) == 2

    filtered = tools.find_references(
        backend, "CONST", filepath="c.py", line=1,
    )
    assert len(filtered.splitlines()) == 1
    assert "print(CONST)" in filtered


def test_find_references_invalid_line_returns_error(backend):
    result = tools.find_references(backend, "x", line=0)
    assert result.startswith("error:")


# --- Execute tools ---

def test_run_tests_success_has_empty_output(backend):
    assert tools.run_tests(backend, "true", workdir=str(backend.root)) == ""


def test_run_tests_captures_stdout_and_stderr(backend):
    result = tools.run_tests(
        backend, "echo out; echo err 1>&2", workdir=str(backend.root),
    )
    assert "out" in result
    assert "err" in result


def test_get_patch_error_when_not_a_git_repo(backend):
    assert tools.get_patch(backend).startswith("error:")


def test_get_patch_includes_new_untracked_file(backend):
    _git_init(backend)
    backend.write_file("new.py", "x = 1\n")
    patch = tools.get_patch(backend)
    assert "new.py" in patch
    assert "+x = 1" in patch


def test_get_patch_empty_when_no_changes(backend):
    _git_init(backend)
    assert tools.get_patch(backend) == ""


def test_get_patch_excludes_pycache_noise(backend):
    _git_init(backend)
    backend.write_file("calc.py", "def add(a, b):\n    return a - b\n")
    backend.run(
        "git add -A && git -c user.email=t@t -c user.name=t "
        "commit -q -m 'add calc.py'",
        workdir=str(backend.root), timeout=15,
    )
    # Running code from the repo generates __pycache__/*.pyc noise.
    backend.run(
        "python3 -c 'from calc import add'",
        workdir=str(backend.root), timeout=15,
    )
    tools.edit_file(backend, "calc.py", "a - b", "a + b")
    patch = tools.get_patch(backend)
    assert "__pycache__" not in patch
    assert "calc.py" in patch


def test_run_command_reports_exit_code(backend):
    result = tools.run_command(backend, "exit 3", str(backend.root))
    assert "exit_code: 3" in result


# --- Private helpers ---

def test_format_matches_builds_absolute_path():
    raw = "./foo.py:3:def helper():"
    expected = "/root/foo.py:3 def helper():"
    assert tools._format_matches(raw, "/root") == expected


def test_definition_regex_matches_def_async_def_and_class():
    pattern = tools._definition_regex("helper")
    assert re.match(pattern, "def helper(x):")
    assert re.match(pattern, "async def helper(x):")
    assert re.match(pattern, "class helper:")
    assert not re.match(pattern, "def helper_other(x):")


def _git_init(backend) -> None:
    root = str(backend.root)
    backend.run("git init -q", workdir=root, timeout=15)
    backend.run(
        "git -c user.email=t@t -c user.name=t "
        "commit --allow-empty -q -m init",
        workdir=root, timeout=15,
    )
