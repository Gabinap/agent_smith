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
import ast
import importlib
import json
import pathlib
import platform
import re
import statistics
import subprocess
import sys
from typing import Any

from paths import ROOT, RUNS, VALIDATION, iter_runs

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


def load_verdicts() -> dict[str, dict[str, Any]]:
    """The moulinette's verdict per run, keyed by repo-relative path.

    Absent when `make validate` has not run: the report then says so in
    every Result cell rather than falling back on the run's own
    `success`, which is the flattering answer this column exists to
    stop quoting.
    """
    if not VALIDATION.is_file():
        return {}
    try:
        return dict(json.loads(VALIDATION.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, TypeError):
        return {}


def load_runs(runs_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Return every solution file under `runs_dir`, oldest name first."""
    verdicts = load_verdicts()
    runs = []
    for path in iter_runs(runs_dir):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"<!-- skipped {path.name}: not valid json -->")
            continue
        if not run.get("steps"):
            print(f"<!-- skipped {path.name}: no step to read -->")
            continue
        run["_file"] = str(path.relative_to(ROOT))
        run["_model"] = run["steps"][0].get("model_name", "unknown")
        # A verdict judged against an older run is not this run's
        # verdict: the entry is dropped rather than reused.
        entry = verdicts.get(run["_file"], {})
        if entry.get("run_timestamp") != run.get("timestamp"):
            entry = {}
        run["_verdict"] = entry
        runs.append(run)
    return runs


def outcome(run: dict[str, Any]) -> str:
    """How the moulinette judged that cell, in one word."""
    verdict = run.get("_verdict") or {}
    if not verdict.get("correctness"):
        return "not judged"
    if verdict.get("passed"):
        return "pass"
    if verdict.get("metrics") == "INVALID":
        return "fail (budget)"
    return "fail"


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

def results_table(runs: list[dict[str, Any]], benchmark: str) -> str:
    """Per (model, task) of one benchmark: outcome, cost, evidence.

    One table per benchmark rather than one of both: the two have
    different budgets, so a single table invites comparing a 6,000-token
    MBPP cell against a 300,000-token SWE-bench one.
    """
    rows = [
        "| Model | Task | Result | Iterations | Tokens in | Tokens out "
        "| Wall time | Stopped because | Evidence |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for run in sorted((r for r in runs if r["benchmark"] == benchmark),
                      key=lambda r: (r["_model"], r["task_id"])):
        rows.append(
            f"| {run['_model']} | {run['task_id']} "
            f"| {outcome(run)} "
            f"| {run['iterations']} "
            f"| {run['total_input_tokens']:,} "
            f"| {run['total_output_tokens']:,} "
            f"| {run['total_time_seconds']:.1f}s "
            f"| {run.get('stop_reason', NA)} "
            f"| [`{pathlib.Path(run['_file']).name}`]"
            f"({run['_file']}) |"
        )
    return "\n".join(rows)


def scoreboard(runs: list[dict[str, Any]]) -> str:
    """One row per model: what it solved on each benchmark.

    The table the reader wants first, and the one the 187-row detail
    tables cannot be skimmed for.
    """
    counts = {
        b: {t for r in runs if r["benchmark"] == b for t in [r["task_id"]]}
        for b in ("swebench", "mbpp")
    }
    rows = [
        f"| Model | SWE-bench (/{len(counts['swebench'])}) "
        f"| MBPP (/{len(counts['mbpp'])}) | Total | Cells with no data |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in sorted({run["_model"] for run in runs}):
        mine = [r for r in runs if r["_model"] == model]
        line = []
        for b in ("swebench", "mbpp"):
            ok = sum(1 for r in mine
                     if r["benchmark"] == b and outcome(r) == "pass")
            line.append(ok)
        dead = sum(1 for r in mine if r.get("error"))
        rows.append(
            f"| {model} | {line[0]} | {line[1]} "
            f"| **{sum(line)}** | {dead or NA} |"
        )
    total = sum(1 for r in runs if outcome(r) == "pass")
    rows.append(f"| **all models** | | | **{total} / {len(runs)}** | "
                f"{sum(1 for r in runs if r.get('error'))} |")
    return "\n".join(rows)


def availability(runs: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    """Per model, cells that produced data over cells attempted.

    Counted from the runs themselves rather than from the runner's logs:
    a log survives a model leaving the catalogue, so comparing the two
    counts once reported more data than attempts.
    """
    attempted: dict[str, int] = {}
    produced: dict[str, int] = {}
    for run in runs:
        model = run["_model"]
        attempted[model] = attempted.get(model, 0) + 1
        if not run.get("error"):
            produced[model] = produced.get(model, 0) + 1
    return {model: (produced.get(model, 0), count)
            for model, count in attempted.items()}


def reliability_table(runs: list[dict[str, Any]]) -> str:
    """Per model: latency, retries, and cells that produced data."""
    by_model: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_model.setdefault(run["_model"], []).append(run)

    served = availability(runs)

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
            model, (len(model_runs), len(model_runs)))
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
    if suspect:
        rows.append(
            "\n⚠ Impossibly fast: those runs were produced before "
            "`request_time_ms` was reported in milliseconds, and hold "
            "seconds. Re-run them before quoting a latency."
        )
    return "\n".join(rows)


def metrics_table(runs: list[dict[str, Any]]) -> str:
    """The three intermediary metrics the subject asks for.

    SWE-bench only: every one of them reads a unified diff or a test
    suite run, so the 110 MBPP cells contributed 110 rows of em dashes.
    """
    rows = [
        "| Model | Task | Patched file first read/edited "
        "| Suite first green | Iterations from green to answer "
        "| Failures first dropped |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for run in sorted((r for r in runs if r["benchmark"] == "swebench"),
                      key=lambda r: (r["_model"], r["task_id"])):
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


def commit() -> str:
    """The commit the campaign ran at, or a note that it is unknown."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


BUDGET_KEYS = ("max_iteration", "max_input_tokens",
               "max_output_tokens", "max_time_seconds")


def budgets_of(entry_point: pathlib.Path) -> dict[str, int]:
    """The caps that entry point passes to its agent.

    Parsed from the module that launches a run, not from the agent's
    constructor defaults: the two differ — MBPP's signature says 60
    seconds where its `__main__` passes 100 — and the one that governs a
    run is the one written here.
    """
    tree = ast.parse(entry_point.read_text(encoding="utf-8"))
    found: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if (keyword.arg in BUDGET_KEYS
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, int)):
                found[keyword.arg] = keyword.value.value
    return found


def budget_rows() -> str:
    """One row per benchmark: the limits a re-run has to match."""
    limits = []
    for name, package in (("MBPP", "agent_mbpp"),
                          ("SWE-bench", "agent_swebench")):
        caps = budgets_of(ROOT / "srcs" / package / "__main__.py")
        temperature = importlib.import_module(f"{package}.agent").TEMPERATURE
        limits.append(
            f"| {name} | {caps.get('max_iteration', NA)} "
            f"| {caps.get('max_input_tokens', 0):,} "
            f"| {caps.get('max_output_tokens', 0):,} "
            f"| {caps.get('max_time_seconds', NA)}s "
            f"| {temperature} |")
    return "\n".join([
        "| Benchmark | Iterations | Tokens in | Tokens out | Time "
        "| Temperature |",
        "|---|---:|---:|---:|---:|---:|",
        *limits,
    ])


def reproduce_section(runs: list[dict[str, Any]]) -> str:
    """Everything needed to run this campaign again elsewhere."""
    models = sorted({run["_model"] for run in runs})
    stamps = sorted(run["timestamp"] for run in runs if run.get("timestamp"))
    swe = sorted({r["task_id"] for r in runs if r["benchmark"] == "swebench"})
    mbpp = sorted({r["task_id"] for r in runs if r["benchmark"] == "mbpp"},
                  key=lambda t: int(t.split("-")[-1]))
    judged = sum(1 for r in runs if r.get("_verdict", {}).get("correctness"))
    return "\n".join([
        f"- **Commit**: `{commit()}` — "
        f"**Python**: {sys.version.split()[0]} — "
        f"**platform**: {platform.system()} {platform.machine()}",
        f"- **Campaign**: {len(runs)} cells, "
        f"{len(models)} models x ({len(swe)} SWE-bench + {len(mbpp)} MBPP) "
        f"tasks, run between {stamps[0][:16] if stamps else NA} and "
        f"{stamps[-1][:16] if stamps else NA}",
        f"- **Verdicts**: {judged}/{len(runs)} cells judged by "
        "`moulinette_eval validate`; the Result column is its verdict, "
        "never the run's own `success` field",
        "- **Models** (provider and key names in "
        "`srcs/call_llm/providers.json`, secrets in `.env`): "
        + ", ".join(f"`{m}`" for m in models),
        f"- **SWE-bench tasks**: {', '.join(f'`{t}`' for t in swe)}",
        f"- **MBPP tasks**: {', '.join(t.split('-')[-1] for t in mbpp)} "
        "(every 25th id of the sorted test split)",
        "",
        "Budgets the agents enforce, and the sampling temperature:",
        "",
        budget_rows(),
        "",
        "```sh",
        "make install                                  # deps and venv",
        "uv run srcs/bench_matrix.py --benchmark mbpp      # 110 cells",
        "uv run srcs/bench_matrix.py --benchmark swebench  #  77 cells",
        "uv run srcs/bench_validate.py                 # moulinette verdicts",
        "make report                                   # this file",
        "```",
        "",
        "> Two caveats for anyone re-running this. The free tiers cap "
        "daily requests, so a cell can die on a quota rather than on the "
        "model — those cells carry an `error` and are counted in *Cells "
        "with no data*, not as failures. And temperature 0 is not a "
        "guarantee: the same id, same prompt, returned two different "
        "answers in three calls on one provider, so counts can move by a "
        "cell or two between campaigns.",
    ])


def report(runs: list[dict[str, Any]]) -> str:
    """Assemble every section, in the order a reader needs them."""
    return "\n\n".join([
        "# Benchmark report",
        "## How to reproduce", reproduce_section(runs),
        "## Summary", scoreboard(runs),
        "> `pass` means the moulinette returned both `Correctness: "
        "PASSED` and `Metrics: VALID`. `fail (budget)` means the answer "
        "was correct but a budget was overrun, which the moulinette "
        "counts as a failure.",
        "## SWE-bench results", results_table(runs, "swebench"),
        "## MBPP results", results_table(runs, "mbpp"),
        "## Provider reliability", reliability_table(runs),
        "## Intermediary metrics", metrics_table(runs),
        "> SWE-bench only: these metrics read a unified diff and a test "
        "suite, which an MBPP cell has neither of. An em dash means the "
        "run does not contain what the metric needs — a task solved "
        "without ever running the suite has no green step to report.",
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
