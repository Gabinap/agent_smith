"""Finding the task an MCP server should serve.

The agents pass it through the environment; the sandbox CLI does not,
and one of the subject's commands runs a server with no task at all.
"""

import json

import pytest

from srcs.mcp_server import task_file

MBPP = {"task_id": 446, "task_definition": "sort a list"}
SWEBENCH = {"instance_id": "django__django-11066", "repo": "django/django"}


@pytest.fixture
def cache(monkeypatch, tmp_path):
    """Redirect the lookup at a throwaway cache directory."""
    monkeypatch.setattr(task_file, "CACHE", tmp_path)
    monkeypatch.delenv("MBPP_TASK_FILE", raising=False)
    monkeypatch.delenv("SWE_TASK_FILE", raising=False)
    return tmp_path


def _write(directory, name, content):
    path = directory / name
    path.write_text(json.dumps(content))
    return path


# --- the environment wins ---

def test_the_env_var_is_used_when_set(cache, monkeypatch):
    chosen = _write(cache, "elsewhere.json", MBPP)
    monkeypatch.setenv("MBPP_TASK_FILE", str(chosen))

    assert task_file.find_task("MBPP_TASK_FILE", "task_id") == chosen


def test_an_env_var_pointing_nowhere_says_so(cache, monkeypatch):
    monkeypatch.setenv("MBPP_TASK_FILE", str(cache / "absent.json"))

    with pytest.raises(SystemExit, match="points at a missing file"):
        task_file.find_task("MBPP_TASK_FILE", "task_id")


# --- falling back to the cache ---

def test_each_server_picks_its_own_kind(cache):
    """cache/ can hold both: the marker field tells them apart."""
    mbpp = _write(cache, "a.json", MBPP)
    swebench = _write(cache, "b.json", SWEBENCH)

    assert task_file.find_task("MBPP_TASK_FILE", "task_id") == mbpp
    assert task_file.find_task(
        "SWE_TASK_FILE", "instance_id") == swebench


def test_the_filename_does_not_matter(cache):
    """Matching on content keeps a renamed dump working."""
    odd = _write(cache, "whatever-i-called-it.json", MBPP)

    assert task_file.find_task("MBPP_TASK_FILE", "task_id") == odd


def test_a_corrupt_file_in_cache_is_skipped(cache):
    (cache / "half.json").write_text('{"task_id":')
    good = _write(cache, "zzz.json", MBPP)

    assert task_file.find_task("MBPP_TASK_FILE", "task_id") == good


def test_an_empty_cache_explains_both_ways_out(cache):
    with pytest.raises(SystemExit) as raised:
        task_file.find_task("MBPP_TASK_FILE", "task_id")

    message = str(raised.value)
    assert "MBPP_TASK_FILE" in message
    assert "task_id" in message


def test_a_cache_holding_only_the_other_kind_is_not_served(cache):
    _write(cache, "swe.json", SWEBENCH)

    with pytest.raises(SystemExit):
        task_file.find_task("MBPP_TASK_FILE", "task_id")
