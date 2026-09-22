"""Turn the runs into the Markdown sections BENCHMARK_REPORT.md needs.

The solution files are the only authority: every number here is derived
from `runs/*.json`, which is also what the corrector opens to check a
row of the report against its data. The runner log and the raw provider
replies are read when present, and skipped when not.

Anything that cannot be derived prints an em dash rather than a guess —
a benchmark that invents its own numbers is worth less than one that
admits a gap.

Usage (from the repo root):
    uv run srcs/bench_report.py
    uv run srcs/bench_report.py --output BENCHMARK_REPORT_sections.md
"""

import argparse
import json
import pathlib
import re
import statistics
from typing import Any

from paths import RUN_LOGS, RUNS

NA = "—"
# No API call answers this fast: a mean below it means the run predates
# the fix that made request_time_ms milliseconds rather than seconds.
IMPOSSIBLE_LATENCY_MS = 50

# `+++ b/path` names the file a unified diff writes to.
PATCH_TARGET = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
# unittest's summary: "OK" or "FAILED (failures=2, errors=1)".
FAILED_COUNTS = re.compile(r"FAILED \(([^)]*)\)")
COUNT_IN_SUMMARY = re.compile(r"(?:failures|errors)=(\d+)")
# A step that ran the suite, as opposed to one that read or edited.
CALLS_TESTS = re.compile(r"\brun_tests\s*\(")
CALLS_READ_OR_EDIT = re.compile(r"\b(read_file|edit_file)\s*\(")


def load_runs(runs_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Return every solution file in `runs_dir`, oldest name first."""
    runs = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"<!-- skipped {path.name}: not valid json -->")
            continue
        if not run.get("steps"):
            print(f"<!-- skipped {path.name}: no step to read -->")
            continue
        run["_file"] = str(path.relative_to(runs_dir.parent))
        run["_model"] = run["steps"][0].get("model_name", "unknown")
        runs.append(run)
    return runs


# --- intermediary metrics ---

def first_touch_step(run: dict[str, Any]) -> int | None:
    """Step where the agent first read or edited the patched file.

    Searching for the path alone would count the grep that merely found
    it; the subject asks when the agent *reads or edits* it.
    """
    targets = PATCH_TARGET.findall(run.get("solution") or "")
    if not targets:
        return None
    for step in run["steps"]:
        code = step.get("sandbox_input") or ""
        if not CALLS_READ_OR_EDIT.search(code):
            continue
        if any(target in code for target in targets):
            return int(step["step"])
    return None


def failures_in(output: str) -> int | None:
    """Failure count reported by a test run, None if it did not run."""
    summary = FAILED_COUNTS.search(output)
    if summary:
        return sum(int(n) for n in COUNT_IN_SUMMARY.findall(summary.group(1)))
    if re.search(r"^OK\b", output, re.MULTILINE):
        return 0
    return None


def test_results(run: dict[str, Any]) -> list[tuple[int, int]]:
    """(step, failure count) for each step that ran the suite."""
    measured = []
    for step in run["steps"]:
        if not CALLS_TESTS.search(step.get("sandbox_input") or ""):
            continue
        count = failures_in(step.get("sandbox_output") or "")
        if count is not None:
            measured.append((int(step["step"]), count))
    return measured


def first_pass_step(run: dict[str, Any]) -> int | None:
    """Step where the suite first came back green."""
    for step, failures in test_results(run):
        if failures == 0:
            return step
    return None


def first_drop_step(run: dict[str, Any]) -> int | None:
    """Step where failures first fell below the first measurement."""
    measured = test_results(run)
    if len(measured) < 2:
        return None
    baseline = measured[0][1]
    for step, failures in measured[1:]:
        if failures < baseline:
            return step
    return None


def gap_to_answer(run: dict[str, Any]) -> int | None:
    """Iterations spent between a green suite and final_answer."""
    green = first_pass_step(run)
    if green is None:
        return None
    return int(run["iterations"]) - green


# --- sections ---

def results_table(runs: list[dict[str, Any]]) -> str:
    """Per (model, task): outcome, cost, and the file behind the row."""
    rows = [
        "| Model | Task | Result | Iterations | Tokens in | Tokens out "
        "| Wall time | Stopped because | Evidence |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for run in runs:
        rows.append(
            f"| {run['_model']} | {run['task_id']} "
            f"| {'pass' if run['success'] else 'fail'} "
            f"| {run['iterations']} "
            f"| {run['total_input_tokens']:,} "
            f"| {run['total_output_tokens']:,} "
            f"| {run['total_time_seconds']:.1f}s "
            f"| {run.get('stop_reason', NA)} "
            f"| `{run['_file']}` |"
        )
    return "\n".join(rows)


def slug(model: str) -> str:
    """Flatten a model id the way the runner names its files."""
    return model.replace("/", "-")


def availability() -> dict[str, tuple[int, int]]:
    """Per model slug, cells that produced data over cells attempted.

    The runner writes one log per cell it starts, the agent one
    solution per cell that finished: comparing the two counts needs no
    separate journal, and a model whose every cell died still shows up
    — with its attempts, and no data.
    """
    attempted: dict[str, int] = {}
    for log in RUN_LOGS.glob("*.log"):
        name = log.stem.split("__", 1)[0]
        attempted[name] = attempted.get(name, 0) + 1

    produced: dict[str, int] = {}
    for run in RUNS.glob("*.json"):
        name = run.stem.split("__", 1)[0]
        produced[name] = produced.get(name, 0) + 1

    return {name: (produced.get(name, 0), count)
            for name, count in attempted.items()}


def reliability_table(runs: list[dict[str, Any]]) -> str:
    """Per model: latency, retries, and cells that produced data."""
    by_model: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_model.setdefault(run["_model"], []).append(run)

    served = availability()

    rows = [
        "| Model | Runs | Avg response | Retries | Cells with data |",
        "|---|---:|---:|---:|---:|",
    ]
    suspect = False
    for model, model_runs in sorted(by_model.items()):
        latencies = [
            step["request_time_ms"]
            for run in model_runs for step in run["steps"]
            if step.get("request_time_ms")
        ]
        retries = sum(
            step.get("retries", 0)
            for run in model_runs for step in run["steps"]
        )
        ok, attempted = served.get(
            slug(model), (len(model_runs), len(model_runs)))
        mean = statistics.mean(latencies) if latencies else 0.0
        flag = ""
        if latencies and mean < IMPOSSIBLE_LATENCY_MS:
            flag, suspect = " ⚠", True
        rows.append(
            f"| {model} | {len(model_runs)} "
            f"| {mean:.0f} ms{flag} "
            f"| {retries} "
            f"| {ok}/{attempted} |"
        )
    # A model whose every cell died has no run to group, so it would
    # vanish from the table — which is exactly the finding to report.
    silent = set(served) - {slug(model) for model in by_model}
    for name in sorted(silent):
        rows.append(
            f"| {name} | 0 | {NA} | {NA} "
            f"| 0/{served[name][1]} |"
        )

    if suspect:
        rows.append(
            "\n⚠ Impossibly fast: those runs were produced before "
            "`request_time_ms` was reported in milliseconds, and hold "
            "seconds. Re-run them before quoting a latency."
        )
    return "\n".join(rows)


def metrics_table(runs: list[dict[str, Any]]) -> str:
    """The three intermediary metrics the subject asks for."""
    rows = [
        "| Model | Task | Patched file first read/edited "
        "| Suite first green | Iterations from green to answer "
        "| Failures first dropped |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for run in runs:
        touch = first_touch_step(run)
        green = first_pass_step(run)
        gap = gap_to_answer(run)
        drop = first_drop_step(run)
        rows.append(
            f"| {run['_model']} | {run['task_id']} "
            f"| {f'step {touch}' if touch else NA} "
            f"| {f'step {green}' if green else NA} "
            f"| {gap if gap is not None else NA} "
            f"| {f'step {drop}' if drop else NA} |"
        )
    return "\n".join(rows)


def setup_section(runs: list[dict[str, Any]]) -> str:
    """Models and tasks actually covered, counted from the runs."""
    models = sorted({run["_model"] for run in runs})
    tasks = sorted({run["task_id"] for run in runs})
    return (
        f"- **{len(models)} model(s)**: {', '.join(models)}\n"
        f"- **{len(tasks)} task(s)**: {', '.join(tasks)}\n"
        f"- **{len(runs)} run(s)** with usable data"
    )


def report(runs: list[dict[str, Any]]) -> str:
    """Assemble every section, in the order the grid reads them."""
    return "\n\n".join([
        "## Setup", setup_section(runs),
        "## Results", results_table(runs),
        "## Provider reliability", reliability_table(runs),
        "## Intermediary metrics", metrics_table(runs),
        "> Read from `runs/*.json`. An em dash means the run does not "
        "contain what the metric needs — a task solved without ever "
        "running the suite has no green step to report.",
    ])


def main() -> None:
    """Print the sections, or write them to a file."""
    parser = argparse.ArgumentParser(prog="bench_report")
    parser.add_argument(
        "--runs", type=pathlib.Path, default=RUNS,
        help="directory holding the solution files")
    parser.add_argument(
        "--output", type=pathlib.Path,
        help="write the Markdown here instead of stdout")
    args = parser.parse_args()

    if not args.runs.is_dir():
        raise SystemExit(f"no run directory: {args.runs}")
    runs = load_runs(args.runs)
    if not runs:
        raise SystemExit(
            f"no usable run in {args.runs}: launch the matrix first, "
            "e.g. make bench")

    text = report(runs)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"{len(runs)} run(s) -> {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
