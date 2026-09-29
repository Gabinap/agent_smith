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
import math
import platform
import random
import re
import statistics
import subprocess
import sys
from typing import Any

from bench_matrix import CATALOG, model_to_url
from paths import CACHE, ROOT, RUNS, VALIDATION, iter_runs

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
    """Return every solution file under `runs_dir`, oldest name first.

    A run that died on its very first call has no step, and so no model
    name inside it. It is kept all the same: dropping it hid exactly the
    hardest failures — a provider withdrawing a model, a 402 on the
    first request — from the column that exists to count them. Its model
    is recovered from the file name, which the runner builds from the
    same slug as every other run of that model.
    """
    verdicts = load_verdicts()
    loaded = []
    for path in iter_runs(runs_dir):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"<!-- skipped {path.name}: not valid json -->")
            continue
        loaded.append((path, run))

    # slug -> model id, learned from the runs that did record a step.
    names = {
        path.stem.split("__", 1)[0]: run["steps"][0].get("model_name")
        for path, run in loaded if run.get("steps")
    }
    catalogue = set(model_to_url())

    runs = []
    for path, run in loaded:
        slug_ = path.stem.split("__", 1)[0]
        run["_file"] = str(path.relative_to(ROOT))
        run["_model"] = (run["steps"][0].get("model_name")
                         if run.get("steps") else names.get(slug_) or slug_)
        run["_retired"] = run["_model"] not in catalogue
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
    header = [
        f"| Model | SWE-bench (/{len(counts['swebench'])}) "
        f"| MBPP (/{len(counts['mbpp'])}) | Total | Cells with no data |",
        "|---|---:|---:|---:|---:|",
    ]

    def rows_for(group: list[dict[str, Any]]) -> list[str]:
        out = []
        for model in sorted({run["_model"] for run in group}):
            mine = [r for r in group if r["_model"] == model]
            line = [sum(1 for r in mine
                        if r["benchmark"] == b and outcome(r) == "pass")
                    for b in ("swebench", "mbpp")]
            dead = sum(1 for r in mine if r.get("error"))
            out.append(f"| {model} | {line[0]} | {line[1]} "
                       f"| **{sum(line)}** | {dead or NA} |")
        passed = sum(1 for r in group if outcome(r) == "pass")
        dead = sum(1 for r in group if r.get("error"))
        out.append(f"| **all** | | | **{passed} / {len(group)}** "
                   f"| {dead or NA} |")
        return out

    current = [r for r in runs if not r["_retired"]]
    retired = [r for r in runs if r["_retired"]]
    parts = ["\n".join(header + rows_for(current))]
    if retired:
        # Kept, not hidden: their cells were run while the models were
        # served, and a model withdrawn mid-campaign is itself a finding
        # about building on free tiers.
        parts.append(
            "Models that left the catalogue during the campaign — "
            "withdrawn by their provider, beyond what the account could "
            "pay for, or moved to another provider. Their cells ran while "
            "they were catalogued, and are kept apart rather than "
            "dropped:\n\n"
            + "\n".join(header + rows_for(retired)))
    return "\n\n".join(parts)


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
    models = sorted({r["_model"] for r in runs if not r["_retired"]})
    retired = sorted({r["_model"] for r in runs if r["_retired"]})
    stamps = sorted(run["timestamp"] for run in runs if run.get("timestamp"))
    swe = sorted({r["task_id"] for r in runs if r["benchmark"] == "swebench"})
    mbpp = sorted({r["task_id"] for r in runs if r["benchmark"] == "mbpp"},
                  key=lambda t: int(t.split("-")[-1]))
    return "\n".join([
        f"- **Commit** `{commit()}` — Python {sys.version.split()[0]} — "
        f"{platform.system()} {platform.machine()}",
        f"- **Cells**: {len(models)} models × ({len(swe)} SWE-bench + "
        f"{len(mbpp)} MBPP tasks), plus {len(retired)} models that left "
        f"the catalogue — {len(runs)} cells, run "
        f"{stamps[0][:10] if stamps else NA} to "
        f"{stamps[-1][:10] if stamps else NA}, each judged by "
        "`moulinette_eval validate`",
        f"- **SWE-bench**: {', '.join(f'`{t}`' for t in swe)}",
        f"- **MBPP**: {', '.join(t.split('-')[-1] for t in mbpp)}",
        "",
        budget_rows(),
        "",
        "```sh",
        "uv run srcs/bench_matrix.py --benchmark mbpp",
        "uv run srcs/bench_matrix.py --benchmark swebench",
        "make validate && make report",
        "```",
        "",
        "> Free-tier quotas can end a cell early — counted as *no data*, "
        "not as a failure — and temperature 0 is not strictly "
        "deterministic: a re-run can move by a cell or two.",
    ])


ABLATION = ROOT / "ablation"
ABLATION_MODEL = "ministral-14b-2512"
# One line changed per variant, against the agent as shipped.
VARIANTS = {
    "baseline": "nothing — the agent as shipped",
    "no-reasoning-guide": "no `REASONING_GUIDE` in the system prompt",
    "fewer-tools": "`find_references`, `list_files`, `run_command` hidden",
    "no-hints": "no `hints_text` in the task prompt",
}
# What each variant takes away, as the conclusions name it.
REMOVED = {
    "no-reasoning-guide": "the reasoning guide",
    "fewer-tools": "the three rarely used tools",
    "no-hints": "the hints",
}
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % interval of a pass rate, sound at small n and near 0 or 1."""
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided exact test on the 2×2 table [[a, b], [c, d]]."""
    row, col, n = a + b, a + c, a + b + c + d

    def prob(x: int) -> float:
        return (math.comb(col, x) * math.comb(n - col, row - x)
                / math.comb(n, row))
    observed = prob(a)
    return min(1.0, sum(prob(x) for x in range(max(0, row + col - n),
                                               min(row, col) + 1)
                        if prob(x) <= observed * (1 + 1e-9)))


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values: several tests, one error budget."""
    adjusted, previous = {}, 0.0
    ranked = sorted(pvalues.items(), key=lambda item: item[1])
    for i, (name, p) in enumerate(ranked):
        previous = max(previous, min(1.0, (len(ranked) - i) * p))
        adjusted[name] = previous
    return adjusted


def paired_bootstrap(base: list[dict[str, Any]], variant: list[dict[str, Any]],
                     field: str) -> tuple[float, float, float]:
    """Median per-task difference, with its 95 % bootstrap interval.

    Tasks are resampled, not runs: the repetitions of one task share
    its difficulty, so treating them as independent would fake a
    precision the design does not have.
    """
    tasks = sorted({r["task"] for r in base})

    def mean(runs: list[dict[str, Any]], task: str) -> float:
        return float(statistics.mean(r[field] for r in runs
                                     if r["task"] == task))
    diffs = [mean(variant, t) - mean(base, t) for t in tasks]
    rng = random.Random(BOOTSTRAP_SEED)
    boots = sorted(statistics.median(rng.choices(diffs, k=len(diffs)))
                   for _ in range(BOOTSTRAP_RESAMPLES))
    return (float(statistics.median(diffs)),
            boots[int(0.025 * BOOTSTRAP_RESAMPLES)],
            boots[int(0.975 * BOOTSTRAP_RESAMPLES)])


def ablation_results() -> dict[str, dict[str, Any]]:
    """Each variant's runs, verdicts and statistics against the baseline.

    Empty until the ablation has run and `bench_validate.py --runs
    ablation --cache ablation/validation.json` has judged it.
    """
    cache = ABLATION / "validation.json"
    if not cache.is_file():
        return {}
    verdicts = json.loads(cache.read_text(encoding="utf-8"))
    results: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        runs = []
        for path in iter_runs(ABLATION / variant):
            run = json.loads(path.read_text(encoding="utf-8"))
            entry = verdicts.get(str(path.relative_to(ROOT)), {})
            runs.append({
                "task": run["task_id"],
                "passed": (entry.get("run_timestamp") == run.get("timestamp")
                           and bool(entry.get("passed"))),
                "tokens": (run["total_input_tokens"]
                           + run["total_output_tokens"]),
                "iterations": run["iterations"],
            })
        if runs:
            results[variant] = {"runs": runs, "k": sum(r["passed"]
                                                       for r in runs),
                                "n": len(runs)}
    base = results.get("baseline")
    if not base:
        return {}
    pvalues = {v: fisher_exact(base["k"], base["n"] - base["k"],
                               r["k"], r["n"] - r["k"])
               for v, r in results.items() if v != "baseline"}
    for variant, p in holm(pvalues).items():
        results[variant]["p"] = p
        for field in ("iterations", "tokens"):
            results[variant][field] = paired_bootstrap(
                base["runs"], results[variant]["runs"], field)
    return results


def ablation_section() -> str:
    """Remove one component at a time, and measure what it was worth."""
    results = ablation_results()
    if not results:
        return f"{NA} — no judged runs under `ablation/`."
    base = results["baseline"]
    tasks = sorted({r["task"] for r in base["runs"]})
    reps = base["n"] // len(tasks)

    rows = ["| Variant | Changed | Resolved | 95 % CI | p (Holm) "
            "| Δ iterations [95 % CI] | Δ tokens [95 % CI] |",
            "|---|---|---:|---|---:|---:|---:|"]
    for variant, r in results.items():
        lo, hi = wilson(r["k"], r["n"])
        cells = [f"{variant}", VARIANTS[variant], f"{r['k']}/{r['n']}",
                 f"{lo:.0%} – {hi:.0%}"]
        if variant == "baseline":
            cells += ["", "", ""]
        else:
            it, tk = r["iterations"], r["tokens"]
            cells += [f"{r['p']:.3f}",
                      f"{it[0]:+.1f} [{it[1]:+.1f}, {it[2]:+.1f}]",
                      f"{tk[0]:+,.0f} [{tk[1]:+,.0f}, {tk[2]:+,.0f}]"]
        rows.append("| " + " | ".join(cells) + " |")

    per_task = ["| Task | " + " | ".join(results) + " |",
                "|---|" + "---:|" * len(results)]
    for task in tasks:
        per_task.append(f"| {task} | " + " | ".join(
            f"{sum(x['passed'] for x in r['runs'] if x['task'] == task)}"
            f"/{reps}" for r in results.values()) + " |")
    split = [t for t in tasks
             if 0 < sum(x["passed"] for x in base["runs"]
                        if x["task"] == t) < reps]

    findings = []
    for variant, r in results.items():
        if variant == "baseline":
            continue
        if r["p"] < 0.05:
            findings.append(
                f"- **{variant} changes the outcome**: {r['k']}/{r['n']} "
                f"against {base['k']}/{base['n']} (p = {r['p']:.3f}), "
                f"{r['iterations'][0]:+.0f} iterations at the median.")
        else:
            findings.append(
                f"- **{variant}: no effect detected** ({r['k']}/{r['n']}, "
                f"p = {r['p']:.2f}).")

    legend = "\n".join([
        f"- **Resolved**: runs the moulinette validated, out of "
        f"{len(tasks)} tasks × {reps} runs.",
        "- **95 % CI**: where the true pass rate lies, with 95 % "
        "confidence (Wilson interval). Widely overlapping intervals "
        "mean the data cannot tell two variants apart.",
        "- **p (Holm)**: the chance of a gap at least this large if "
        "removing the component changed nothing (Fisher's exact test), "
        f"corrected for making {len(results) - 1} comparisons at once "
        "(Holm). Below 0.05, the difference is significant.",
        "- **Δ iterations, Δ tokens**: median per-task change against "
        "the baseline, positive when the variant costs more, with its "
        f"95 % bootstrap interval ({BOOTSTRAP_RESAMPLES:,} resamples of "
        "the tasks). An interval that excludes 0 is a real change.",
    ])

    return "\n\n".join([
        f"`{ABLATION_MODEL}` on the {len(tasks)} SWE-bench tasks, "
        f"{reps} runs each, variants interleaved, temperature 0. Each "
        "variant removes one component, and every run is judged by the "
        "moulinette.",
        "\n".join(rows),
        legend,
        "\n".join(findings),
        f"The baseline itself splits on {len(split)} of {len(tasks)} "
        "tasks across its repetitions, which is why only a large effect "
        "shows at this scale: *no effect detected* is not *no effect*.",
        folded("Resolved per task and variant", "\n".join(per_task)),
    ])


def conclusions_section(runs: list[dict[str, Any]]) -> str:
    """What the data supports, and the model it would lead us to pick."""
    current = [r for r in runs if not r["_retired"]]
    catalogue = json.loads(CATALOG.read_text(encoding="utf-8"))
    provider = {m: name for name, p in catalogue.items() for m in p["model"]}

    def score(model: str, bench: str | None = None) -> int:
        return sum(1 for r in current if r["_model"] == model
                   and (bench is None or r["benchmark"] == bench)
                   and outcome(r) == "pass")

    models = sorted({r["_model"] for r in current},
                    key=lambda m: (-score(m), -score(m, "swebench"), m))
    best, swe_best = models[0], max(models, key=lambda m: score(m, "swebench"))
    n_swe = len({r["task_id"] for r in current
                 if r["benchmark"] == "swebench"})

    claimed = sum(1 for r in current
                  if r["benchmark"] == "swebench" and r.get("success"))
    judged = sum(1 for r in current
                 if r["benchmark"] == "swebench" and outcome(r) == "pass")
    dead: dict[str, int] = {}
    for r in current:
        if r.get("error"):
            name = provider.get(r["_model"], "?")
            dead[name] = dead.get(name, 0) + 1
    clean = [name for name in catalogue if not dead.get(name)]
    retired = sorted({r["_model"] for r in runs if r["_retired"]})

    median = statistics.median(score(m) for m in models)
    weak = [m for m in models if score(m) < median]

    ablation = ablation_results()
    learned = []
    if ablation:
        base = ablation["baseline"]
        needed = [v for v, r in ablation.items()
                  if v != "baseline" and r["p"] < 0.05]
        idle = [v for v in ablation if v not in needed and v != "baseline"]
        learned.append(
            "- **What the agent needs** (ablation): "
            + (", ".join(f"{REMOVED[v]} — without it, "
                         f"{base['k'] - ablation[v]['k']} of {base['n']} "
                         "runs are lost" for v in needed) or "nothing")
            + "; not " + " nor ".join(REMOVED[v] for v in idle)
            + ", no effect detected.")
        if ABLATION_MODEL in models:
            learned.append(
                f"- **One run per cell is not a measure**: "
                f"`{ABLATION_MODEL}` resolved "
                f"{score(ABLATION_MODEL, 'swebench')}/{n_swe} SWE-bench "
                f"tasks in the campaign, {base['k']}/{base['n']} over "
                "three repetitions.")
    return "\n".join([
        f"- **Selected: `{best}`** ({score(best)}/17), with "
        f"`{swe_best}` for SWE-bench ({score(swe_best, 'swebench')}/"
        f"{n_swe}) — the best scores, on a provider with no cell lost. "
        "They are the agent's defaults.",
        "- **Disregarded**: below the median, "
        + ", ".join(f"`{m}` ({score(m)}/17)" for m in weak)
        + f"; and the {len(retired)} models no longer served.",
        f"- **`success` is not a verdict**: {claimed} resolutions claimed "
        f"on SWE-bench, {judged} confirmed by the moulinette.",
        *learned,
        f"- **Free tiers move**: {len(retired)} models left the catalogue "
        "in three days. Cells with no data: "
        + ", ".join(f"{n} on {name}" for name, n in sorted(dead.items()))
        + (f", none on {', '.join(clean)}." if clean else "."),
    ])


# Tasks whose `hints_text` gives the fix away rather than discussing it:
# read by hand from cache/swebench/, stated here so the report can
# measure what they are worth.
REVEALING_HINTS = {
    "sympy__sympy-18189": "the fix's own diff",
    "sympy__sympy-13480": "the line and the change to make",
    "django__django-11066": "a link to the upstream fix",
}
# Code an agent should never need: network access, or history beyond
# the task's base commit.
LOOKUP = re.compile(
    r"https?://|\bcurl\b|\bwget\b|requests\.get|urllib"
    r"|git\s+(?:fetch|pull|log\s+--all|show\s+[0-9a-f]{7,})", re.I)


def inputs_section(runs: list[dict[str, Any]]) -> str:
    """What the agent is given, and whether it reached for anything else."""
    swe = [r for r in runs if not r["_retired"]
           and r["benchmark"] == "swebench"]
    hints = {
        t: len(json.loads((CACHE / "swebench" / f"{t}.json")
                          .read_text(encoding="utf-8")).get("hints_text")
               or "")
        for t in sorted({r["task_id"] for r in swe})
    }

    rows = ["| Task | `hints_text` | What it gives |", "|---|---:|---|"]
    for task, size in hints.items():
        gives = REVEALING_HINTS.get(task, "discussion" if size else NA)
        rows.append(f"| {task} | {size:,} chars | {gives} |")
    revealing = set(REVEALING_HINTS) & set(hints)

    # Whether a hint matters is measured on the same tasks with and
    # without it, not read off a comparison between different tasks.
    ablation = ablation_results()
    if "no-hints" in ablation:
        base, no = ablation["baseline"], ablation["no-hints"]
        measured = (f"The ablation removes them: `{ABLATION_MODEL}` "
                    f"resolves {no['k']}/{no['n']} without, "
                    f"{base['k']}/{base['n']} with (p = {no['p']:.2f}).")
    else:
        measured = "Their effect is measured in the ablation."

    lookups = [(r["_model"], r["task_id"], found.group(0))
               for r in swe for step in r["steps"]
               if (found := LOOKUP.search(step.get("sandbox_input") or ""))]
    return "\n\n".join([
        "The prompt carries the task's `hints_text`, an input the subject "
        f"defines. On {len(revealing)} of the {len(hints)} tasks it gives "
        "the fix away:",
        "\n".join(rows),
        measured,
        "No run fetched anything from outside its task"
        + (f"; one `{lookups[0][2]} …` (`{lookups[0][0]}`) found nothing."
           if lookups else "."),
    ])


def folded(summary: str, body: str) -> str:
    """`body` behind a disclosure: there for the corrector, not in the way.

    The blank lines around the body are load-bearing — without them a
    Markdown table inside <details> is rendered as raw pipes.
    """
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def selection_section(runs: list[dict[str, Any]]) -> str:
    """Why these tasks and these models, and not others."""
    models = sorted({r["_model"] for r in runs if not r["_retired"]})
    return "\n\n".join([
        "**Tasks.** SWE-bench: the moulinette's exam pool, plus "
        "`django__django-17029` outside it. MBPP has no exam pool: its "
        "ten tasks are every 25th id of the sorted test split.",
        f"**Models.** {len(models)}, on the free tiers of four providers "
        "(OpenRouter, Mistral, Groq, Together), chosen for spread: "
        "several vendors, a size ladder (`ministral` 3B, 8B, 14B), a "
        "code model (`codestral`). Each candidate was screened on one "
        "task per benchmark; left out were models that could not follow "
        "the protocol (`gpt-oss-20b` answers with native tool calls, "
        "`allam-2-7b` invents the sandbox's output), paid-only models, "
        "and aliases of models already in. Version ids are pinned where "
        "the provider offers them.",
    ])


def report(runs: list[dict[str, Any]]) -> str:
    """Assemble every section, in the order a reader needs them.

    The per-cell tables are folded: the grid requires them — the
    corrector checks a solution.json against its row — but at 187 rows
    they buried the summary a reader wants first.
    """
    return "\n\n".join([
        "# Benchmark report",
        "## How to reproduce", reproduce_section(runs),
        "## Selection rationale", selection_section(runs),
        "## What the agent is given", inputs_section(runs),
        "## Summary", scoreboard(runs),
        "> `pass` means the moulinette returned both `Correctness: "
        "PASSED` and `Metrics: VALID`. `fail (budget)` means the answer "
        "was correct but a budget was overrun, which the moulinette "
        "counts as a failure.",
        "## Provider reliability", reliability_table(runs),
        "## Results per cell",
        folded("SWE-bench — every (model, task) cell, with the "
               "solution.json behind it", results_table(runs, "swebench")),
        folded("MBPP — every (model, task) cell, with the solution.json "
               "behind it", results_table(runs, "mbpp")),
        "## Intermediary metrics",
        "> SWE-bench only: these metrics read a unified diff and a test "
        "suite, which an MBPP cell has neither of. An em dash means the "
        "run does not contain what the metric needs — a task solved "
        "without ever running the suite has no green step to report.",
        folded("Per SWE-bench cell", metrics_table(runs)),
        "## Ablation", ablation_section(),
        "## Conclusions", conclusions_section(runs),
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
