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
