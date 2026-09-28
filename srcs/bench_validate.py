"""Ask the moulinette to judge every run, and cache its verdict.

A run's own `success` field says it produced a final answer, which is
not the same claim as having solved the task: on SWE-bench the two
disagreed on 22 of 77 cells, always in the flattering direction. Only
`moulinette_eval validate` settles correctness, so the report reads its
verdict from here rather than believing the run about itself.

The verdict is cached because obtaining it is expensive — one container
per SWE-bench cell — and because it must not move while a report is
being read. Re-running a cell invalidates its entry, so the cache also
records the run's timestamp: an entry older than its run is stale and
reported as such rather than silently trusted.

Usage (from the repo root):
    uv run srcs/bench_validate.py              # only what is missing
    uv run srcs/bench_validate.py --force      # judge everything again
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
from typing import Any

from paths import CACHE, ROOT, VALIDATION, iter_runs

MOULINETTE = ROOT / "moulinette"

# The moulinette prints its verdict one label per line; reading the
# labels is what keeps this script independent of its exit code, which
# a failed task and a crashed harness share.
VERDICTS = {
    "correctness": re.compile(r"^Correctness:\s*(\w+)", re.M),
    "metrics": re.compile(r"^Metrics:\s*(\w+)", re.M),
    "resolution": re.compile(r"^Resolution status:\s*(\w+)", re.M),
}


def task_file(run: dict[str, Any]) -> pathlib.Path:
    """The task file that run was solving.

    Derived from the run's own `task_id` rather than from its filename:
    a SWE-bench instance carries `__` inside its name, so splitting the
    filename on `__` truncates the task and validates the wrong cell.
    """
    return CACHE / str(run["benchmark"]) / f"{run['task_id']}.json"


def judge(run_path: pathlib.Path, run: dict[str, Any]) -> dict[str, Any]:
    """Run the moulinette on one cell and return what it said."""
    task = task_file(run)
    if not task.is_file():
        return {"error": f"task file missing: {task.relative_to(ROOT)}"}

    # Launched from the moulinette's own directory, where `uv run`
    # resolves its entry point: from the repo root the command is not
    # on the path, and the failure is silent enough to be read as an
    # unjudged cell rather than a broken call.
    done = subprocess.run(
        ["uv", "run", "moulinette_eval", "validate", run["benchmark"],
         str(task.resolve()), str(run_path.resolve())],
        cwd=MOULINETTE, capture_output=True, text=True,
    )
    if done.returncode != 0 and "Correctness:" not in done.stdout:
        return {"error": (done.stderr or done.stdout).strip()[-200:]}
    output = done.stdout + done.stderr
    found = {name: (m.group(1) if (m := pattern.search(output)) else None)
             for name, pattern in VERDICTS.items()}
    return {
        "correctness": found["correctness"],
        "metrics": found["metrics"],
        "resolution": found["resolution"],
        # Both must hold: a correct patch that overran its token or time
        # budget is a failed cell, and the moulinette says so too.
        "passed": found["correctness"] == "PASSED"
        and found["metrics"] == "VALID",
        "run_timestamp": run.get("timestamp"),
        "judged_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def load_cache(cache_file: pathlib.Path = VALIDATION) -> dict[str, Any]:
    """The verdicts recorded so far, empty when there are none."""
    if not cache_file.is_file():
        return {}
    try:
        return dict(json.loads(cache_file.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, TypeError):
        return {}


def is_fresh(entry: dict[str, Any], run: dict[str, Any]) -> bool:
    """True when `entry` judged this very run and not an older one."""
    return (bool(entry.get("correctness"))
            and entry.get("run_timestamp") == run.get("timestamp"))


def main() -> None:
    """Judge every run missing a fresh verdict, then write the cache.

    One verdict at a time. The moulinette stages each SWE-bench patch,
    eval script and test log at fixed paths under /tmp, so two verdicts
    in flight overwrite each other's files: a run gets graded on another
    run's patch or another task's test log. Judged four at a time, 52 of
    84 ablation cells came back failed that pass when judged alone.
    """
    parser = argparse.ArgumentParser(prog="bench_validate")
    parser.add_argument("--force", action="store_true",
                        help="judge every run again, ignoring the cache")
    # Both default to the campaign; the ablation keeps its earlier runs
    # outside runs/ and judges them into a cache of its own.
    parser.add_argument("--runs", type=pathlib.Path, default=None,
                        help="directory of runs to judge (default: runs/)")
    parser.add_argument("--cache", type=pathlib.Path, default=VALIDATION,
                        help="verdict cache to read and write")
    args = parser.parse_args()
    cache_file = args.cache.resolve()

    runs = iter_runs(args.runs.resolve() if args.runs else None)
    if not runs:
        raise SystemExit("no run to validate: launch the matrix first")

    cache = {} if args.force else load_cache(cache_file)
    todo = []
    for path in runs:
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        key = str(path.relative_to(ROOT))
        if not args.force and is_fresh(cache.get(key, {}), run):
            continue
        todo.append((key, path, run))

    print(f"{len(runs)} run(s), {len(todo)} to judge\n")
    for done, (key, path, run) in enumerate(todo, start=1):
        verdict = cache[key] = judge(path, run)
        label = ("PASSED" if verdict.get("passed")
                 else verdict.get("error")
                 or f"{verdict.get('correctness')}/{verdict.get('metrics')}")
        print(f"[{done}/{len(todo)}] {key}: {label}", flush=True)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    passed = sum(1 for v in cache.values() if v.get("passed"))
    print(f"\n{passed}/{len(cache)} cell(s) passed "
          f"-> {cache_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
