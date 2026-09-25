"""Where every runtime artifact lives, resolved from the repo root.

A relative path lands wherever the caller happened to be: the agents
run from srcs/, the scripts from the repo root, so "cache/x.json" meant
two different files. Everything here is absolute and anchored on this
file, so a writer and a reader always mean the same place.

Two directories, two roles: cache/ holds what goes in (the tasks the
moulinette dumps), runs/ holds everything a run puts out.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

CACHE = ROOT / "cache"

RUNS = ROOT / "runs"
RUN_LOGS = RUNS / "logs"

# One directory per model, so opening the tree shows a model's whole
# record at once; MBPP sits one level deeper because the two benchmarks
# share that directory and seventeen files in one pile read as noise.
MBPP_SUBDIR = "mbpp_task"

# The moulinette's verdict for each run, cached because it is the only
# honest measure of correctness and re-deriving it costs a container per
# SWE-bench cell. `make validate` writes it, the report reads it.
VALIDATION = RUNS / "validation.json"


def run_path(model_slug: str, instance: str, benchmark: str) -> pathlib.Path:
    """Where the solution of that (model, task) cell belongs.

    The writer and every reader call this rather than building the path
    themselves: a layout known in four places drifts, and a reader that
    globs the wrong depth reports an empty campaign instead of failing.
    """
    directory = RUNS / model_slug
    if benchmark == "mbpp":
        directory /= MBPP_SUBDIR
    return directory / f"{model_slug}__{instance}.json"


def iter_runs(runs_dir: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Every solution file under `runs_dir`, at any depth, sorted."""
    root = runs_dir if runs_dir is not None else RUNS
    return sorted(path for path in root.rglob("*.json")
                  if RUN_LOGS not in path.parents
                  and path.name != VALIDATION.name)
