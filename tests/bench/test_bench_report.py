"""Unit tests for srcs/bench_report.py (the metrics extractor).

The report is only worth what these derivations are worth: they are the
numbers a corrector checks against the solution files behind them.
"""

import json

import pytest

from srcs import bench_report

PATCH = (
    "diff --git a/django/contrib/x.py b/django/contrib/x.py\n"
    "--- a/django/contrib/x.py\n"
    "+++ b/django/contrib/x.py\n"
    "@@ -1 +1 @@\n"
    "-a\n+b\n"
)

GREEN = "Ran 4 tests in 0.3s\n\nOK\n"
RED_TWO = "Ran 4 tests in 0.3s\n\nFAILED (failures=2)\n"
RED_THREE = "Ran 4 tests in 0.3s\n\nFAILED (failures=2, errors=1)\n"


def _step(number, code="", output=""):
    return {
        "step": number, "sandbox_input": code, "sandbox_output": output,
        "request_time_ms": 1200.0, "retries": 0, "model_name": "m",
    }


def _run(steps, solution=PATCH, success=True):
    return {
        "task_id": "t-1", "success": success, "solution": solution,
        "iterations": len(steps), "total_requests": len(steps),
        "total_input_tokens": 10, "total_output_tokens": 2,
        "total_time_seconds": 1.0, "steps": steps, "_model": "m",
        "_file": "runs/m__t-1.json",
    }


# --- where the agent first touched the file it ended up patching ---

def test_a_grep_that_merely_mentions_the_file_does_not_count():
    """The metric is "reads or edits", not "names in passing"."""
    run = _run([
        _step(1, 'search_code(pattern="x", '
                 'file_pattern="django/contrib/x.py")'),
        _step(2, 'read_file(filepath="django/contrib/x.py")'),
    ])

    assert bench_report.first_touch_step(run) == 2


def test_an_edit_counts_as_touching():
    run = _run([
        _step(1, 'list_files(directory=".", pattern="*")'),
        _step(2, 'edit_file(filepath="django/contrib/x.py", old_str="a")'),
    ])

    assert bench_report.first_touch_step(run) == 2


def test_reading_another_file_does_not_count():
    run = _run([_step(1, 'read_file(filepath="somewhere/else.py")')])

    assert bench_report.first_touch_step(run) is None


def test_no_patch_means_nothing_to_look_for():
    run = _run([_step(1, 'read_file(filepath="x.py")')], solution="")

    assert bench_report.first_touch_step(run) is None


# --- reading a test summary ---

@pytest.mark.parametrize("output, expected", [
    (GREEN, 0),
    (RED_TWO, 2),
    (RED_THREE, 3),
    ("nothing ran here", None),
])
def test_failures_are_read_from_the_unittest_summary(output, expected):
    assert bench_report.failures_in(output) == expected


def test_only_steps_that_ran_the_suite_are_measured():
    run = _run([
        _step(1, 'read_file(filepath="x.py")', GREEN),  # output says OK...
        _step(2, "result = run_tests()", RED_TWO),
    ])

    # ...but that step never called run_tests, so it is not a measurement
    assert bench_report.test_results(run) == [(2, 2)]


# --- green suite, and the distance to final_answer ---

def test_first_green_step_is_reported():
    run = _run([
        _step(1, "run_tests()", RED_TWO),
        _step(2, "run_tests()", GREEN),
        _step(3, "final_answer(get_patch())"),
    ])

    assert bench_report.first_pass_step(run) == 2
    assert bench_report.gap_to_answer(run) == 1


def test_a_suite_that_never_passes_has_no_green_step():
    run = _run([_step(1, "run_tests()", RED_TWO)])

    assert bench_report.first_pass_step(run) is None
    assert bench_report.gap_to_answer(run) is None


# --- failures falling below the baseline ---

def test_the_drop_is_measured_against_the_first_run():
    run = _run([
        _step(1, "run_tests()", RED_THREE),
        _step(2, "run_tests()", RED_THREE),
        _step(3, "run_tests()", RED_TWO),
    ])

    assert bench_report.first_drop_step(run) == 3


def test_a_single_measurement_has_no_baseline_to_drop_from():
    run = _run([_step(1, "run_tests()", GREEN)])

    assert bench_report.first_drop_step(run) is None


# --- loading ---

def test_the_runner_log_and_stepless_runs_are_skipped(tmp_path, capsys):
    (tmp_path / "matrix_log.json").write_text("[]")
    (tmp_path / "empty.json").write_text(json.dumps(_run([])))
    (tmp_path / "ok.json").write_text(json.dumps(_run([_step(1)])))

    runs = bench_report.load_runs(tmp_path)

    assert [run["task_id"] for run in runs] == ["t-1"]
    assert "no step to read" in capsys.readouterr().out


def test_a_corrupt_run_is_skipped_not_fatal(tmp_path, capsys):
    (tmp_path / "half.json").write_text('{"task_id":')
    (tmp_path / "ok.json").write_text(json.dumps(_run([_step(1)])))

    assert len(bench_report.load_runs(tmp_path)) == 1
    assert "not valid json" in capsys.readouterr().out


# --- the assembled report ---

def test_an_impossible_latency_is_flagged(tmp_path):
    """Runs predating the millisecond fix hold seconds: never quote them."""
    run = _run([_step(1)])
    run["steps"][0]["request_time_ms"] = 1.4

    table = bench_report.reliability_table([run])

    assert "⚠" in table
    assert "hold\nseconds" in table or "seconds" in table


def test_a_plausible_latency_is_not_flagged():
    table = bench_report.reliability_table([_run([_step(1)])])

    assert "⚠" not in table


def test_the_report_carries_the_file_behind_each_row():
    """Q12 part B: a row must lead back to the data that produced it."""
    text = bench_report.report([_run([_step(1)])])

    assert "runs/m__t-1.json" in text
