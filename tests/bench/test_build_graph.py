"""Unit tests for srcs/build_graph.py (the success-rate chart)."""

import json
import pathlib

import pytest

from srcs.build_graph import LLMBenchmarkGraph


def _solution(runs: pathlib.Path, model: str, task: str,
              success: bool, steps: bool = True) -> pathlib.Path:
    """Write a solution file the way an agent would."""
    path = runs / f"{model}__{task}.json"
    path.write_text(json.dumps({
        "task_id": task,
        "success": success,
        "steps": [{"model_name": model}] if steps else [],
    }))
    return path


@pytest.fixture
def runs(tmp_path):
    directory = tmp_path / "runs"
    directory.mkdir()
    return directory


# --- reading the run files ---

def test_reads_one_entry_per_solution_file(runs):
    _solution(runs, "codestral", "a-1", success=True)
    _solution(runs, "gpt-oss", "a-1", success=False)

    data = LLMBenchmarkGraph(runs).raw_data

    assert sorted(data, key=lambda e: e["model"]) == [
        {"model": "codestral", "success": True, "task_id": "a-1"},
        {"model": "gpt-oss", "success": False, "task_id": "a-1"},
    ]


def test_the_runner_log_is_not_a_run(runs):
    """matrix_log.json sits in runs/ but is not a solution."""
    _solution(runs, "codestral", "a-1", success=True)
    (runs / "matrix_log.json").write_text(json.dumps([{"model": "noise"}]))

    assert [e["model"] for e in LLMBenchmarkGraph(runs).raw_data] == [
        "codestral"]


def test_a_run_without_a_step_is_skipped(runs, capsys):
    """No step means no model was ever recorded: nothing to attribute."""
    _solution(runs, "codestral", "a-1", success=True)
    _solution(runs, "dead", "a-1", success=False, steps=False)

    data = LLMBenchmarkGraph(runs).raw_data

    assert [e["model"] for e in data] == ["codestral"]
    assert "Skipping" in capsys.readouterr().out


def test_a_corrupt_run_file_is_reported(runs):
    (runs / "half.json").write_text('{"task_id":')

    with pytest.raises(ValueError, match="Invalid file"):
        LLMBenchmarkGraph(runs)


def test_a_missing_run_directory_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="No run directory"):
        LLMBenchmarkGraph(tmp_path / "never-created")


# --- counting, and the fairness guard ---

def test_counts_successes_per_model(runs):
    _solution(runs, "codestral", "a-1", success=True)
    _solution(runs, "codestral", "b-2", success=False)
    _solution(runs, "gpt-oss", "a-1", success=True)
    _solution(runs, "gpt-oss", "b-2", success=True)

    counts, total = LLMBenchmarkGraph(runs)._validate_and_process_data()

    assert dict(counts) == {"codestral": 1, "gpt-oss": 2}
    assert total == 2


def test_refuses_to_chart_models_that_ran_a_different_number_of_tasks(runs):
    """Comparing 1/1 against 1/2 on the same chart would mislead."""
    _solution(runs, "codestral", "a-1", success=True)
    _solution(runs, "gpt-oss", "a-1", success=True)
    _solution(runs, "gpt-oss", "b-2", success=True)

    with pytest.raises(ValueError, match="Invalid test"):
        LLMBenchmarkGraph(runs)._validate_and_process_data()


def test_refuses_to_chart_models_that_ran_different_tasks(runs):
    _solution(runs, "codestral", "a-1", success=True)
    _solution(runs, "gpt-oss", "b-2", success=True)

    with pytest.raises(ValueError, match="arn't the same"):
        LLMBenchmarkGraph(runs)._validate_and_process_data()


def test_nothing_to_chart_is_an_error(runs):
    with pytest.raises(ValueError, match="No data found"):
        LLMBenchmarkGraph(runs)._validate_and_process_data()
