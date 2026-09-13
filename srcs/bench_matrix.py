"""Run the benchmark matrix: each model against each SWE-bench task.

One cell of the matrix is one run, and one run leaves one solution.json
named after the pair that produced it. That naming is the whole point:
Q12 asks the corrector to pick a row of the report and open the file
behind it, which a single shared --output path makes impossible.

Usage (from the repo root):
    uv run srcs/bench_matrix.py --dry-run
    uv run srcs/bench_matrix.py --models codestral-latest,openai/gpt-oss-20b
    uv run srcs/bench_matrix.py --tasks cache/task_a.json cache/task_b.json
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time
from typing import Any

from paths import CACHE, MATRIX_LOG, ROOT, RUN_LOGS, RUNS

SRCS = ROOT / "srcs"
CATALOG = SRCS / "call_llm" / "providers.json"

DEFAULT_TIMEOUT_SECONDS = 1800


def model_to_url() -> dict[str, str]:
    """Map every catalogued model to the provider URL that serves it."""
    catalog = json.loads(CATALOG.read_text())
    return {
        model: provider["url"]
        for provider in catalog.values()
        for model in provider["model"]
    }


def slug(model: str) -> str:
    """Flatten a model id into a filename fragment ('a/b' -> 'a-b')."""
    return model.replace("/", "-")


def instance_of(task_file: pathlib.Path) -> str:
    """Return the SWE-bench instance id a task file describes."""
    return str(json.loads(task_file.read_text())["instance_id"])


def is_done(output: pathlib.Path) -> bool:
    """True when that cell already produced a result worth keeping.

    A solution.json whose `error` is set means the loop itself died —
    rate limit, crash — so the cell has no usable data and must run
    again. A run that merely failed the task did finish: re-running it
    would overwrite a legitimate result.
    """
    if not output.exists():
        return False
    try:
        return json.loads(output.read_text()).get("error") is None
    except (json.JSONDecodeError, OSError):
        return False


def run_cell(model: str, url: str, task: pathlib.Path,
             timeout: int) -> dict[str, Any]:
    """Run one (model, task) pair and report how it went.

    Never raises: a cell that crashes or times out is a result too —
    it feeds the availability column of the report.
    """
    instance = instance_of(task)
    name = f"{slug(model)}__{instance}"
    output = RUNS / f"{name}.json"
    log = RUN_LOGS / f"{name}.log"

    command = [
        sys.executable, "-m", "agent_swebench",
        "--task-file", str(task),
        "--output", str(output),
        "--model-name", model,
        "--provider-url", url,
    ]

    start = time.perf_counter()
    try:
        done = subprocess.run(
            command, cwd=SRCS, timeout=timeout,
            capture_output=True, text=True,
        )
        exit_code, tail = done.returncode, done.stderr[-2000:]
        log.write_text(done.stdout + done.stderr)
    except subprocess.TimeoutExpired:
        exit_code, tail = -1, f"timed out after {timeout}s"
        log.write_text(tail)

    return {
        "model": model,
        "provider_url": url,
        "task": instance,
        "output": str(output.relative_to(ROOT)),
        "solution_written": output.exists(),
        "exit_code": exit_code,
        "wall_seconds": round(time.perf_counter() - start, 1),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "stderr_tail": tail if exit_code != 0 else "",
    }


def append_to_log(record: dict[str, Any]) -> None:
    """Add one cell to matrix_log.json, written after every run.

    Written as we go rather than at the end: a matrix takes hours and
    may be interrupted, and what already ran must survive that.
    """
    history: list[dict[str, Any]] = []
    if MATRIX_LOG.exists() and MATRIX_LOG.stat().st_size:
        history = json.loads(MATRIX_LOG.read_text())
    history.append(record)
    MATRIX_LOG.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    """Read the matrix definition from the command line."""
    parser = argparse.ArgumentParser(prog="bench_matrix")
    parser.add_argument(
        "--models", default="",
        help="comma-separated model ids (default: the whole catalog)")
    parser.add_argument(
        "--tasks", nargs="*", default=[],
        help="task json files (default: every cache/*.json)")
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
        help="per-run limit in seconds")
    parser.add_argument(
        "--force", action="store_true",
        help="re-run cells whose solution.json already exists")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="list the matrix without running anything")
    return parser.parse_args()


def resolve_models(wanted: str, known: dict[str, str]) -> list[str]:
    """Return the models to run, rejecting any the catalog ignores."""
    if not wanted:
        return list(known)
    models = [m.strip() for m in wanted.split(",") if m.strip()]
    unknown = [m for m in models if m not in known]
    if unknown:
        raise SystemExit(
            f"unknown model(s): {', '.join(unknown)}\n"
            f"catalogued: {', '.join(known)}")
    return models


def resolve_tasks(wanted: list[str]) -> list[pathlib.Path]:
    """Return the task files to run against."""
    if wanted:
        paths = [pathlib.Path(t) for t in wanted]
    else:
        paths = sorted(CACHE.glob("*task*.json"))
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(f"missing task file(s): {missing}")
    if not paths:
        raise SystemExit(
            "no task file: dump one first, e.g.\n"
            "  cd moulinette && uv run moulinette_eval dump swebench "
            "--output ../cache/swebench_task.json")
    return paths


def main() -> None:
    """Run every (model, task) cell, skipping the ones already done."""
    args = parse_args()
    known = model_to_url()
    models = resolve_models(args.models, known)
    tasks = resolve_tasks(args.tasks)
    RUNS.mkdir(parents=True, exist_ok=True)
    RUN_LOGS.mkdir(parents=True, exist_ok=True)

    cells = [(m, t) for m in models for t in tasks]
    print(f"{len(models)} model(s) x {len(tasks)} task(s) "
          f"= {len(cells)} run(s)\n")

    for index, (model, task) in enumerate(cells, start=1):
        instance = instance_of(task)
        output = RUNS / f"{slug(model)}__{instance}.json"
        head = f"[{index}/{len(cells)}] {model} on {instance}"

        if args.dry_run:
            print(f"{head} -> {output.relative_to(ROOT)}")
            continue
        if is_done(output) and not args.force:
            print(f"{head}: already done, skipped")
            continue
        if output.exists():
            print(f"{head}: previous run errored, running again")

        print(f"{head}...", flush=True)
        record = run_cell(model, known[model], task, args.timeout)
        append_to_log(record)
        verdict = "ok" if record["solution_written"] else "NO DATA"
        print(f"    {verdict} in {record['wall_seconds']}s "
              f"(exit {record['exit_code']})")

    if not args.dry_run:
        print(f"\nlog: {MATRIX_LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
