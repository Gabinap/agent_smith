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

from paths import CACHE, ROOT, RUN_LOGS, RUNS

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


# What tells the two benchmarks apart: the field that identifies one of
# its task files, and the agent that solves it. Each benchmark's set
# lives in cache/<name>/, so the directory is the declaration — a task
# dumped elsewhere for a one-off run never joins the matrix.
# The MBPP marker is `task_definition`, not `task_id`: a solution.json
# carries a task_id too.
BENCHMARKS = {
    "swebench": ("instance_id", "agent_swebench"),
    "mbpp": ("task_definition", "agent_mbpp"),
}

# The task set every benchmarked model faces, so a row of the report
# compares models on identical ground.
#
# SWE-bench: the moulinette's exam pool (EXAM_POOL in
# moulinette/moulinette/swebench/interact.py), which `moulinette_eval
# select` draws the exam's 3 tasks from and nowhere else — plus one
# task outside it, so the report also shows the agent on ground the
# exam cannot serve. Seven tasks is Q13's five-star threshold.
#
# MBPP has no such pool: the exam draws 5 tasks at random from the
# whole test split (257 tasks, ids 11 to 479). These are every 25th id
# of that split once sorted — a spread sample rather than a lucky
# cluster, and a selection rule the report states in one line.
TASK_SETS = {
    "swebench": [
        "django__django-11066",
        "pydata__xarray-4629",
        "scikit-learn__scikit-learn-13439",
        "sympy__sympy-13480",
        "sympy__sympy-18189",
        "sympy__sympy-14711",
        "django__django-17029",
    ],
    "mbpp": ["11", "75", "103", "135", "227", "257", "285", "390",
             "418", "444"],
}

MOULINETTE = ROOT / "moulinette"


def instance_of(task_file: pathlib.Path) -> str:
    """Return the id a task file describes, benchmark included.

    MBPP numbers its tasks, SWE-bench names them: the prefix keeps a
    cell name unambiguous, and keeps runs/ readable when both
    benchmarks have been run.
    """
    task = json.loads(task_file.read_text())
    if "instance_id" in task:
        return str(task["instance_id"])
    return f"mbpp-{task['task_id']}"


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
             timeout: int, agent: str = "agent_swebench") -> dict[str, Any]:
    """Run one (model, task) pair and report how it went.

    Never raises: a cell that crashes or times out is a result too —
    it feeds the availability column of the report.
    """
    instance = instance_of(task)
    name = f"{slug(model)}__{instance}"
    output = RUNS / f"{name}.json"
    log = RUN_LOGS / f"{name}.log"

    command = [
        sys.executable, "-m", agent,
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


def parse_args() -> argparse.Namespace:
    """Read the matrix definition from the command line."""
    parser = argparse.ArgumentParser(prog="bench_matrix")
    parser.add_argument(
        "--models", default="",
        help="comma-separated model ids (default: the whole catalog)")
    parser.add_argument(
        "--benchmark", choices=sorted(BENCHMARKS), default="swebench",
        help="which agent and which tasks to run (default: swebench)")
    parser.add_argument(
        "--tasks", nargs="*", default=[],
        help="task json files (default: that benchmark's tasks in cache/)")
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


def is_swebench_task(path: pathlib.Path, marker: str = "instance_id") -> bool:
    """True when `path` is a task file of that benchmark.

    Matching on the filename is not enough: cache/ holds both
    benchmarks' tasks, and reading `instance_id` off an MBPP one
    raises a KeyError that kills the whole matrix.
    """
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(content, dict) and marker in content


def dump_missing_tasks(benchmark: str, marker: str) -> None:
    """Dump the benchmark's task set, skipping what is already there.

    The runner owns this rather than a separate command: the set is
    what it runs against, and a matrix that silently ran on six tasks
    because the seventh was never dumped is worse than a slow start.
    """
    directory = CACHE / benchmark
    directory.mkdir(parents=True, exist_ok=True)

    for task_id in TASK_SETS[benchmark]:
        path = directory / f"{task_id}.json"
        if is_swebench_task(path, marker):
            continue
        print(f"dumping {benchmark} task {task_id}...", flush=True)
        done = subprocess.run(
            ["uv", "run", "moulinette_eval", "dump", benchmark,
             "--task-id", task_id, "--output", str(path)],
            cwd=MOULINETTE, capture_output=True, text=True,
        )
        if not is_swebench_task(path, marker):
            tail = (done.stderr or done.stdout).strip()
            raise SystemExit(
                f"could not dump {benchmark} task {task_id}\n"
                f"{tail[-300:]}")


def resolve_tasks(wanted: list[str], marker: str = "instance_id",
                  benchmark: str = "swebench") -> list[pathlib.Path]:
    """Return the task files to run against.

    Without `--tasks`, the benchmark's own directory is the set:
    cache/swebench/ or cache/mbpp/, whatever `make tasks` dumped there.
    """
    directory = CACHE / benchmark
    if wanted:
        # Absolute, because the agent is launched with cwd=srcs/: a
        # relative path given here would resolve under srcs/ instead.
        paths = [pathlib.Path(t).resolve() for t in wanted]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            raise SystemExit(f"missing task file(s): {missing}")
        wrong_kind = [p for p in paths if not is_swebench_task(p, marker)]
        if wrong_kind:
            raise SystemExit(
                f"task file(s) of the wrong benchmark: {wrong_kind}\n"
                f"a task file must carry a {marker!r} field")
    else:
        # One cell per instance, not per file: the same task dumped
        # twice under two names would otherwise run twice and write to
        # the same solution path.
        seen: dict[str, pathlib.Path] = {}
        for path in sorted(directory.glob("*.json")):
            if is_swebench_task(path, marker):
                seen.setdefault(instance_of(path), path)
        paths = list(seen.values())
    if not paths:
        raise SystemExit(
            f"no {benchmark} task in {directory}: dump the set first\n"
            "  make tasks")
    return paths


def main() -> None:
    """Run every (model, task) cell, skipping the ones already done."""
    args = parse_args()
    known = model_to_url()
    models = resolve_models(args.models, known)
    marker, agent = BENCHMARKS[args.benchmark]
    if not args.tasks:
        dump_missing_tasks(args.benchmark, marker)
    tasks = resolve_tasks(args.tasks, marker, args.benchmark)
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
        record = run_cell(model, known[model], task, args.timeout, agent)
        verdict = "ok" if record["solution_written"] else "NO DATA"
        print(f"    {verdict} in {record['wall_seconds']}s "
              f"(exit {record['exit_code']})")

    if not args.dry_run:
        print(f"\nlogs: {RUN_LOGS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
