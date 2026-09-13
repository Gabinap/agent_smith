"""Unit tests for srcs/bench_matrix.py (the benchmark matrix runner)."""

import json
import pathlib
import subprocess

import pytest

from srcs import bench_matrix

CATALOG = {
    "Mistral Studio": {
        "url": "https://api.mistral.ai/v1",
        "keys": ["MISTRAL_1"],
        "model": ["codestral-latest", "ministral-3b-latest"],
    },
    "Groq Console": {
        "url": "https://api.groq.com/openai/v1",
        "keys": ["GROQ_1"],
        "model": ["openai/gpt-oss-20b"],
    },
}


@pytest.fixture
def bench(monkeypatch, tmp_path):
    """Point the module at a throwaway repo laid out like the real one.

    ROOT has to move with the rest: run_cell() reports the output path
    relative to it, which only works if runs/ sits underneath.
    """
    cache = tmp_path / "cache"
    runs = tmp_path / "runs"
    logs = runs / "logs"
    for directory in (cache, runs, logs):
        directory.mkdir(parents=True)

    catalog_file = tmp_path / "providers.json"
    catalog_file.write_text(json.dumps(CATALOG))

    monkeypatch.setattr(bench_matrix, "ROOT", tmp_path)
    monkeypatch.setattr(bench_matrix, "CACHE", cache)
    monkeypatch.setattr(bench_matrix, "RUNS", runs)
    monkeypatch.setattr(bench_matrix, "RUN_LOGS", logs)
    monkeypatch.setattr(bench_matrix, "MATRIX_LOG", runs / "matrix_log.json")
    monkeypatch.setattr(bench_matrix, "CATALOG", catalog_file)
    return tmp_path


def _task(directory: pathlib.Path, instance: str) -> pathlib.Path:
    """Write a task file the way the moulinette dumps one."""
    path = directory / f"{instance}_task.json"
    path.write_text(json.dumps({"instance_id": instance, "repo": "x/y"}))
    return path


def _solution(path: pathlib.Path, error=None) -> pathlib.Path:
    """Write a solution file with the one field is_done() reads."""
    path.write_text(json.dumps({"task_id": "t", "error": error}))
    return path


# --- naming ---

def test_slug_flattens_the_provider_prefix():
    assert bench_matrix.slug("openai/gpt-oss-20b") == "openai-gpt-oss-20b"


def test_slug_leaves_a_plain_model_alone():
    assert bench_matrix.slug("codestral-latest") == "codestral-latest"


def test_instance_of_reads_the_id_from_the_task_file(bench):
    task = _task(bench / "cache", "django__django-11066")
    assert bench_matrix.instance_of(task) == "django__django-11066"


# --- catalog lookup ---

def test_model_to_url_maps_every_model_to_its_provider(bench):
    assert bench_matrix.model_to_url() == {
        "codestral-latest": "https://api.mistral.ai/v1",
        "ministral-3b-latest": "https://api.mistral.ai/v1",
        "openai/gpt-oss-20b": "https://api.groq.com/openai/v1",
    }


def test_resolve_models_defaults_to_the_whole_catalog(bench):
    known = bench_matrix.model_to_url()
    assert bench_matrix.resolve_models("", known) == list(known)


def test_resolve_models_keeps_the_requested_subset(bench):
    known = bench_matrix.model_to_url()
    wanted = "codestral-latest, openai/gpt-oss-20b"

    assert bench_matrix.resolve_models(wanted, known) == [
        "codestral-latest", "openai/gpt-oss-20b",
    ]


def test_resolve_models_rejects_a_typo_before_any_run(bench):
    """Hours of runs must not be wasted on a misspelled name."""
    known = bench_matrix.model_to_url()

    with pytest.raises(SystemExit, match="codestral-lastest"):
        bench_matrix.resolve_models("codestral-lastest", known)


# --- task lookup ---

def test_resolve_tasks_takes_the_files_it_is_given(bench):
    task = _task(bench / "cache", "a__a-1")
    assert bench_matrix.resolve_tasks([str(task)]) == [task]


def test_resolve_tasks_defaults_to_the_task_files_in_cache(bench):
    first = _task(bench / "cache", "a__a-1")
    second = _task(bench / "cache", "b__b-2")

    assert bench_matrix.resolve_tasks([]) == [first, second]


def test_resolve_tasks_ignores_a_non_task_json_in_cache(bench):
    task = _task(bench / "cache", "a__a-1")
    (bench / "cache" / "something_else.json").write_text("[]")

    assert bench_matrix.resolve_tasks([]) == [task]


def test_resolve_tasks_refuses_a_missing_file(bench):
    with pytest.raises(SystemExit, match="missing task file"):
        bench_matrix.resolve_tasks([str(bench / "cache" / "nope.json")])


def test_resolve_tasks_explains_how_to_dump_one_when_cache_is_empty(bench):
    with pytest.raises(SystemExit, match="moulinette_eval dump swebench"):
        bench_matrix.resolve_tasks([])


# --- resuming: is_done() decides what gets re-run ---

def test_a_cell_never_run_is_not_done(bench):
    assert bench_matrix.is_done(bench / "runs" / "absent.json") is False


def test_a_finished_cell_is_done_even_when_the_task_failed(bench):
    """Failing the task is a result: re-running would overwrite it."""
    path = _solution(bench / "runs" / "ok.json", error=None)
    assert bench_matrix.is_done(path) is True


def test_a_cell_whose_loop_died_is_not_done(bench):
    """Rate limit or crash: no usable data, that cell must run again."""
    path = _solution(bench / "runs" / "ko.json",
                     error="Every API key is rate limited")
    assert bench_matrix.is_done(path) is False


def test_a_truncated_solution_file_is_not_done(bench):
    path = bench / "runs" / "half.json"
    path.write_text('{"task_id": "t"')

    assert bench_matrix.is_done(path) is False


# --- the run log ---

def test_append_to_log_creates_the_file_on_the_first_cell(bench):
    bench_matrix.append_to_log({"model": "m", "exit_code": 0})

    written = json.loads((bench / "runs" / "matrix_log.json").read_text())
    assert written == [{"model": "m", "exit_code": 0}]


def test_append_to_log_keeps_what_earlier_cells_wrote(bench):
    bench_matrix.append_to_log({"model": "first"})
    bench_matrix.append_to_log({"model": "second"})

    written = json.loads((bench / "runs" / "matrix_log.json").read_text())
    assert [entry["model"] for entry in written] == ["first", "second"]


# --- running one cell ---

def _fake_run(returncode=0, stdout="", stderr="", writes=None):
    """Stand in for subprocess.run, optionally creating the output."""
    def _run(command, **kwargs):
        if writes is not None:
            pathlib.Path(command[command.index("--output") + 1]).write_text(
                writes)
        return subprocess.CompletedProcess(command, returncode,
                                           stdout=stdout, stderr=stderr)
    return _run


def test_run_cell_reports_a_cell_that_produced_a_solution(bench,
                                                          monkeypatch):
    task = _task(bench / "cache", "a__a-1")
    monkeypatch.setattr(subprocess, "run",
                        _fake_run(stdout="done", writes='{"error": null}'))

    record = bench_matrix.run_cell("codestral-latest", "http://x", task, 60)

    assert record["solution_written"] is True
    assert record["exit_code"] == 0
    assert record["task"] == "a__a-1"
    assert record["output"] == "runs/codestral-latest__a__a-1.json"
    assert record["stderr_tail"] == ""


def test_run_cell_records_a_crash_instead_of_raising(bench, monkeypatch):
    """A dead cell is data too: it feeds the availability column."""
    task = _task(bench / "cache", "a__a-1")
    monkeypatch.setattr(subprocess, "run",
                        _fake_run(returncode=1, stderr="boom"))

    record = bench_matrix.run_cell("codestral-latest", "http://x", task, 60)

    assert record["solution_written"] is False
    assert record["exit_code"] == 1
    assert "boom" in record["stderr_tail"]


def test_run_cell_records_a_timeout(bench, monkeypatch):
    task = _task(bench / "cache", "a__a-1")

    def _timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 60)

    monkeypatch.setattr(subprocess, "run", _timeout)

    record = bench_matrix.run_cell("codestral-latest", "http://x", task, 60)

    assert record["exit_code"] == -1
    assert "timed out" in record["stderr_tail"]


def test_run_cell_keeps_the_process_output_in_a_log(bench, monkeypatch):
    task = _task(bench / "cache", "a__a-1")
    monkeypatch.setattr(subprocess, "run",
                        _fake_run(stdout="panels", stderr="warning"))

    bench_matrix.run_cell("codestral-latest", "http://x", task, 60)

    log = bench / "runs" / "logs" / "codestral-latest__a__a-1.log"
    assert log.read_text() == "panelswarning"
