"""MCP tool implementations: file, search, and execute operations."""

import re
import shlex

from srcs.models import ExecBackend

# Fast, read-only tools
FAST_TOOL_TIMEOUT_SECONDS = 15
# Tools that can spawn a process
EXEC_TOOL_TIMEOUT_SECONDS = 300


def _resolve_root(backend: ExecBackend) -> str:
    """Return the absolute path of the current search root (".")."""
    return backend.run(
        "pwd", workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS,
    ).stdout.strip()


def _definition_regex(name: str) -> str:
    """Regex matching a def/async def/class declaration of `name`."""
    return rf"^\s*(async\s+def|def|class)\s+{re.escape(name)}\b"


def _format_matches(raw_output: str, root: str) -> str:
    """Turn `grep -n` output into the mandatory match-line format.

    Input is "path:line:content" per line, with path relative to
    `root`. Output is "/absolute/path:<line> <content>".
    """
    lines = []
    for entry in raw_output.splitlines():
        path, line_number, content = entry.split(":", 2)
        abs_path = f"{root}/{path.removeprefix('./')}"
        lines.append(f"{abs_path}:{line_number} {content}")
    return "\n".join(lines)


# Files tools

def read_file(
    backend: ExecBackend, filepath: str,
    start_line: int = 1, end_line: int | None = None,
) -> str:
    """Read file lines, cat -n style: "<line_number>: <line_content>".

    Args:
        backend: Execution backend.
        filepath: File to read.
        start_line: First line, 1-indexed (default: 1).
        end_line: Last line, inclusive. None reads to EOF.
    Returns:
        Formatted lines, or "error: ..." if unreadable or out of
        range.
    """
    try:
        lines = backend.read_file(filepath).splitlines()
    except OSError as e:
        return f"error: cannot read {filepath}: {e}"
    if start_line < 1 or (end_line is not None and end_line < start_line):
        return "error: invalid line range"
    end = end_line or len(lines)
    return "\n".join(
        f"{i}: {line}"
        for i, line in enumerate(lines[start_line - 1:end], start=start_line)
    )


# TODO: old str not foud (trouver un truc qui reseembl ?)
def edit_file(
        backend: ExecBackend, filepath: str, old_str: str, new_str: str
        ) -> str:
    """Replace one exact occurrence of `old_str` with `new_str`.

    Args:
        backend: Execution backend.
        filepath: File to edit.
        old_str: Exact text to replace, must be unique in the file.
        new_str: Replacement text.
    Returns:
        "ok: <filepath> updated", or "error: ..." if not found or
        ambiguous (multiple occurrences).
    """
    try:
        content = backend.read_file(filepath)
    except OSError as e:
        return f"error: cannot read {filepath}: {e}"

    count = content.count(old_str)
    if count == 0:
        return f"error: old_str not found in {filepath}"
    if count > 1:
        return (
            f"error: old_str found {count} times in {filepath}, "
            "must be unique — include more surrounding context"
        )

    backend.write_file(filepath, content.replace(old_str, new_str, 1))
    return f"ok: {filepath} updated"


def list_files(backend: ExecBackend, directory: str, pattern: str) \
        -> str:
    """List entries directly inside `directory` matching `pattern`.

    Listing is non-recursive.

    Args:
        backend: Execution backend.
        directory: Directory to list.
        pattern: Glob filenames must match (e.g. '*.py', '*').
    Returns:
        One matching path per line, or "error: ..." if directory is
        invalid.
    """
    cmd = (
        f"find {shlex.quote(directory)} -maxdepth 1 "
        f"-name {shlex.quote(pattern)}"
    )
    result = backend.run(
        cmd, workdir=directory, timeout=FAST_TOOL_TIMEOUT_SECONDS,
    )
    if result.exit_code != 0:
        return f"error: {result.stderr}"
    return result.stdout


# Search tools

# TODO: maybe delete by default all files starting with a dot.
def search_code(backend: ExecBackend, pattern: str, file_pattern: str) \
        -> str:
    """Recursively grep the codebase for a regex pattern.

    Args:
        backend: Execution backend.
        pattern: Regex to search for (grep -E syntax).
        file_pattern: Glob restricting which files to search.
    Returns:
        One match per line: "/absolute/path:<line_number> <content>".
    """
    cmd = (
        f"grep -rn --include={shlex.quote(file_pattern)} "
        f"{shlex.quote(pattern)} ."
    )
    raw = backend.run(
        cmd, workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS,
    )
    if raw.exit_code not in (0, 1):
        return f"error: {raw.stderr}"
    return _format_matches(raw.stdout, _resolve_root(backend))


def search_function_or_class_definition_in_code(
        backend: ExecBackend, name: str) -> str:
    """Find where a function or class named `name` is defined.

    Args:
        backend: Execution backend.
        name: Exact function/class name (not a regex).
    Returns:
        One match per line: "/absolute/path:<line_number> <content>".
    """
    cmd = (
        f"grep -rEn --include='*.py' "
        f"{shlex.quote(_definition_regex(name))} ."
    )
    raw = backend.run(
        cmd, workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS,
    )
    if raw.exit_code not in (0, 1):
        return f"error: {raw.stderr}"
    return _format_matches(raw.stdout, _resolve_root(backend))


def find_references(
        backend: ExecBackend, name: str, filepath: str | None = None,
        line: int | None = None) -> str:
    """Find usages of `name` across the whole codebase.

    Its own definition is excluded automatically; `filepath`/`line`
    are only a fallback for definition styles this can't auto-detect.

    Args:
        backend: Execution backend.
        name: Symbol name to search for (not a regex).
        filepath: Known definition site, to also exclude it.
        line: Known definition line, paired with `filepath`.
    Returns:
        One match per line: "/absolute/path:<line_number> <content>".
    """
    if line is not None and line < 1:
        return "error: line number must be >= 1"
    definition_pattern = _definition_regex(name)
    cmd = f"grep -rFn --include='*.py' {shlex.quote(name)} ."
    raw = backend.run(cmd, workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS)
    if raw.exit_code not in (0, 1):
        return f"error: {raw.stderr}"

    root = _resolve_root(backend)
    known_site = (
        filepath.removeprefix("./") if filepath is not None else None
    )
    result = []
    for entry in raw.stdout.splitlines():
        path, line_number, content = entry.split(":", 2)
        rel_path = path.removeprefix("./")
        if re.match(definition_pattern, content):
            continue
        if rel_path == known_site and line is not None \
                and int(line_number) == line:
            continue
        result.append(f"{root}/{rel_path}:{line_number} {content}")

    return "\n".join(result)


# Execute tools

def run_tests(
        backend: ExecBackend, eval_script: str, workdir: str,
        timeout: int = EXEC_TOOL_TIMEOUT_SECONDS) -> str:
    """Run this task's evaluation script.

    Args:
        backend: Execution backend.
        eval_script: Bash script running the test/eval suite.
        workdir: Directory to run it from.
        timeout: Max seconds (test override; MCP wrapper uses default).
    Returns:
        Combined stdout and stderr, unmodified.
    """
    result = backend.run(eval_script, workdir=workdir, timeout=timeout,
                         bash=True)
    return f"{result.stdout}  {result.stderr} exit_code:{result.exit_code}"


def get_patch(backend: ExecBackend) -> str:
    """Stage all changes and return the unified diff against HEAD.

    Args:
        backend: Execution backend.
    Returns:
        Diff from `git -c core.fileMode=false diff --cached`, or
        "error: ..." if git itself failed (never mixed into the diff).
    """
    # Running code from the repo (e.g. via run_tests/run_command)
    # generates __pycache__/*.pyc — pure build noise that must never
    # leak into a submitted patch. Delete it before staging.
    backend.run(
        "find . -type d -name __pycache__ -exec rm -rf {} + ; "
        "find . -name '*.pyc' -delete",
        workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS,
    )
    add_result = backend.run(
        "git add -A", workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS
    )
    if add_result.exit_code != 0:
        return f"error: git add failed: {add_result.stderr}"
    diff_result = backend.run(
        "git -c core.fileMode=false diff --cached",
        workdir=".", timeout=FAST_TOOL_TIMEOUT_SECONDS,
    )
    if diff_result.exit_code != 0:
        return f"error: git diff failed: {diff_result.stderr}"
    return diff_result.stdout


def run_command(
        backend: ExecBackend, command: str, workdir: str,
        timeout: int = EXEC_TOOL_TIMEOUT_SECONDS) -> str:
    """Run an arbitrary shell command.

    Args:
        backend: Execution backend.
        command: Shell command to run.
        workdir: Directory to run it from.
        timeout: Max seconds (test override; MCP wrapper uses default).
    Returns:
        Text block with "stdout:", "stderr:", "exit_code:" sections.
    """
    result = backend.run(command, workdir=workdir, timeout=timeout)
    return (
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
        f"exit_code: {result.exit_code}"
    )
