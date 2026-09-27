_This project has been created as part of the 42 curriculum by pgougne, gagulhon, mthetcha._
![](./assets/42banner.png)
___
# Description
## Introduction

Software engineering is no longer only about writing correct code, it is about under-
standing systems, navigating large codebases, debugging failures, and iter-
ating efficiently. Modern LLMs generate code well, but fixing real bugs also needs
exploration, hypothesis testing, execution, and observation.\
This is where Agent Smith comes in. A Code Agent is not just a model that writes code:
it reasons about a task, interacts with tools, executes code safely, observes
results, and adapts its strategy. In this project, you will design and implement such
a system, moving beyond static prompts and JSON-based tool calling to build a fully
agentic loop driven by executable Python code.

## Project

Agent Smith is a code agent that acts by writing Python. Instead of
answering in JSON, the model writes a block of code; the code runs in a
sandbox, and what it printed becomes the model's next observation. Two
agents share this loop:

- **MBPP agent** — solves *Mostly Basic Python Problems*: write a
  function, run it against the task's asserts, submit it once they pass.
- **SWE-bench agent** — fixes a real bug in a real repository: explore
  the code, edit it, run the project's tests, and submit the resulting
  git patch.

Both are built from the same three parts:

- **The sandbox** executes model-written code in a fresh, isolated child
  process. It inspects the source before compiling it, hands out only
  allowlisted imports and builtins, confines file access to allowed
  directories, neutralises the network, and lets the kernel cap memory,
  CPU, file size and process creation. A wall-clock timeout stops
  runaway code while keeping what it printed so far.
- **An MCP server** per benchmark exposes the tools the agent may call.
  The sandbox connects to it as an MCP client and injects every tool it
  advertises as a plain Python function. For SWE-bench, the tools work
  inside the task's Docker container, never on the host.
- **An LLM layer** talks to any OpenAI-compatible provider, rotates
  between API keys when one is rate limited, and records the tokens,
  latency and retries of every call.

Every run ends with a `solution.json` in the format the moulinette
validates: the answer, and the metrics of each iteration.
___
# Instructions

## Requirements

- Python 3.10 and [uv](https://docs.astral.sh/uv/)
- A running Docker daemon, for SWE-bench
- At least one API key from a supported provider

## Installation

```sh
make install
```

API keys are read from a `.env` file at the repository root, never from
the code. The variable names each provider expects are listed in
`srcs/call_llm/providers.json`; a second key per provider enables
rotation when the first one is rate limited:

```sh
MISTRAL_STUDIO_1=...
MISTRAL_STUDIO_2=...
GROQ_CONSOLE_1=...
```

A provider URL that is not in the catalog falls back to `API_KEY`.

## Getting a task

Tasks come from the moulinette, dumped into `cache/`:

```sh
cd moulinette && uv sync
uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json
uv run moulinette_eval dump swebench --output ../cache/swebench_task.json
```

## Running an agent

Each agent reads a task file and writes its solution as JSON. Both run
from `srcs/`, which the Makefile does for you:

```sh
make run-mbpp          # cache/mbpp_task.json     -> runs/mbpp_solution.json
make run-swebench      # cache/swebench_task.json -> runs/swebench_solution.json
```

Without arguments, each agent runs its benchmark's default model —
`ministral-8b-2512` for MBPP, `ministral-14b-2512` for SWE-bench, both
on Mistral, the best scores of the benchmark campaign — so a run never
stops to ask. To use another:

```sh
make run-mbpp MODEL="codestral-2508" PROVIDER="https://api.mistral.ai/v1"
```

or pass `--choose` to the agent to pick the provider and model from a
menu. The defaults read their keys from `MISTRAL_STUDIO_1` to
`MISTRAL_STUDIO_6` in `.env`.

The agent starts its MCP server itself, over stdio. To reach a server
already listening on `http://localhost:8000` instead, start it with
`python mcp_tools_mbpp.py --http` and pass `--http` to the agent.

To check a solution the way the evaluation does:

```sh
cd moulinette
uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../runs/mbpp_solution.json
```

## Running the sandbox on its own

The sandbox is also a standalone REPL. It prints the manual of the tools
it discovered, executes each line under the same restrictions, and
exits on `exit` or Ctrl-D; `manual` prints the tool list again.

```sh
uv run sandbox                                            # built-in policy
uv run sandbox sandbox_strict.json                        # explicit policy
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py"     # with an MCP server
uv run sandbox --mcp-server http://localhost:8000         # same, over HTTP
make sandbox-mbpp                                         # MBPP tools + template
make sandbox-swebench                                     # SWE-bench tools + template
```

An MCP server started this way without a task file serves the first
matching task it finds in `cache/`.

## Benchmark

```sh
make bench                    # every catalogued model on the SWE-bench set
make bench-mbpp               # the same, on the MBPP set
make bench MODELS="codestral-2508,ministral-8b-2512"
make validate                 # the moulinette's verdict on every run
make graph                    # success rate per model, in the terminal
make report                   # writes BENCHMARK_REPORT.md from runs/
```

Each (model, task) pair leaves one solution file, under
`runs/<model>/` for SWE-bench and `runs/<model>/mbpp_task/` for MBPP,
and a re-run skips the pairs already done. `make validate` caches the
moulinette's verdicts in `runs/validation.json`; the report reads its
results from there, never from a run's own `success` field.

## Checks

```sh
make lint          # flake8, then mypy
make lint-strict   # same, with mypy --strict
```

___
# Resources

**Topic references**

- Model Context Protocol specification — https://modelcontextprotocol.io/specification
- MBPP: *Program Synthesis with Large Language Models* — https://arxiv.org/abs/2108.07732
- SWE-bench: *Can Language Models Resolve Real-World GitHub Issues?* — https://arxiv.org/abs/2310.06770
- CodeAct: *Executable Code Actions Elicit Better LLM Agents* — https://arxiv.org/abs/2402.01030
- Python `ast`, `resource`, `signal` and `multiprocessing` documentation — https://docs.python.org/3.10/library/
- Docker SDK for Python — https://docker-py.readthedocs.io/
- Sandboxing Python in pure Python — https://www.iditect.com/faq/python/how-to-sandbox-python-in-pure-python.html
- What is an MCP server — https://phase2online.com/insights/explain-it-like-i-m-five-what-the-heck-is-an-mcp-server

**How AI was used**

AI was used as a support and learning assistant, and for some parts as a
code generator whose output we reviewed and can explain.

- Organising:
  - Split the project into multiple parts
  - Suggest an organisation plan
- Debugging and review:
  - Explain unexpected behaviors and suggest potential causes of bugs
  - Audit the repository against the subject and the evaluation grid,
    by running the code rather than reading it
- Code generation, reviewed by the team:
  - The benchmark report extractor (`srcs/bench_report.py`)
  - The benchmark matrix generator (`srcs/bench_matrix.py`)
  - The type annotations that bring the code to `mypy`
- Writing: docstrings, and drafting parts of this README.

___
# System architecture

The architecture was dictated by the subject:
![](./assets/achitecture.png)

Here is how the parts fit together during a run:

- **Task processing** — the agent reads the task dumped by the
  moulinette and builds the prompt describing it.
- **Code generation** — the LLM answers with Python code aimed at the
  next step.
- **Sandboxed execution** — the agent extracts the code and runs it in
  the sandbox.
- **Tool access** — when the code calls a tool, the sandbox forwards the
  call to the MCP server through its MCP client, and the result comes
  back as the function's return value.
- **Evaluation loop** — the sandbox's output is fed back to the model,
  until the code calls `final_answer()` or a limit is reached.

The code is organised by responsibility:

```
mcp_tools_mbpp.py        MCP server for MBPP: run_tests
mcp_tools_swebench.py    MCP server for SWE-bench: the nine tools
sandbox_*.json           sandbox policies, one per use
srcs/
├── agent_mbpp/          MBPP agent: CLI entry point, prompts, loop
├── agent_swebench/      SWE-bench agent: CLI entry point, prompts, loop
├── call_llm/            provider catalog, key rotation, API calls
├── sandbox/             sandbox, MCP client, standalone REPL
├── mcp_server/          tool implementations, task file lookup
├── backends/            where tools execute: host directory or Docker
├── models/              pydantic models and shared interfaces
├── cli_agent/           terminal display
├── code_extract.py      code extraction from model replies
├── bench_matrix.py      benchmark runner, and the task set it runs
├── bench_report.py      report tables derived from the runs
└── build_graph.py       success-rate graph
```

`cache/` holds what goes into a run and `runs/` everything a run puts
out (solutions, provider replies, runner logs). Each benchmark's task
set lives in its own directory, `cache/swebench/` and `cache/mbpp/`:
the runner dumps whatever is missing from it before starting, so the
matrix is exactly the declared set.

___
# Agent loop explanation

Both agents run the same **Thought → Code → Observation** loop,
implemented in `solve_task()` and `execute()` of each agent. No agent
framework is involved.

## The conversation

The conversation opens with a **system prompt** that sets the rules —
one Python block per turn, one step per block, explore before editing,
call `final_answer()` to finish — and ends with the manual of the tools
the sandbox actually discovered, generated from the MCP server's
schemas. The **task prompt** follows: the problem and its tests for
MBPP; the repository, the hints and the issue for SWE-bench.

Every later turn is appended to that same history, and the whole
history is sent on each call. The model therefore always sees every
step it took and every result it got, which is also why input tokens
grow with each iteration.

## One iteration

1. **Thought and code** — the LLM is called with the conversation.
   Reasoning is separated from the answer, whether the model marks it
   with `</think>` / `</thought>` tags or the provider returns it in a
   dedicated field.
2. **Extraction** — the Python block is taken from the answer. A
   well-formed ` ```python ` block is used as is; otherwise the
   extractor tries, in order, a block with another tag or none, a block
   that was never closed, and finally the whole reply as bare code. A
   candidate is only accepted if `ast.parse` confirms it is Python, so a
   shell or JSON block is never run as if it were.
3. **Execution** — the code runs in the sandbox, which calls the MCP
   tools on its behalf. Each execution starts from a clean interpreter:
   what persists between steps is the conversation, and the files the
   tools changed — not Python variables.
4. **Observation** — the result is appended to the conversation as the
   environment's turn, and the next iteration begins.

## Feedback in every situation

The model is never left guessing about what happened to its code:

| Situation | What the model receives |
|---|---|
| No code found in the reply | Nothing is executed; the model is told no Python was found and which format is expected |
| Malformed block, recovered | The observation starts with a note naming the repair — wrong tag, missing closing fence, no fence at all — and the correct format |
| Code raised an error | The error type and message, and what it printed before failing |
| Execution timed out | `TimeoutError: Execution time limit exceeded`, with the output printed before the deadline |
| Output too long | The first 30 lines, followed by `(N Remaining Lines...)` |
| An edit would break a file | `edit_file` writes nothing and names the syntax error its `new_str` would introduce |
| Code ran and printed nothing | Said in as many words, so silence is never mistaken for a silent failure |
| SWE-bench `run_tests()` | The verdict and the failing test names, as unittest itself reports them |

The observation carries what happened, never the code that caused it:
the model's own message is already in the conversation, and the whole
history is resent on every call.

## How the loop ends

- **`final_answer()` is called** — the sandbox marks the execution as
  finished and the loop stops. For MBPP the answer is the function's
  source code; for SWE-bench it is the patch returned by `get_patch()`.
- **The iteration cap is reached**, or **the time budget is spent** —
  checked before each iteration. The budget sits below the subject's
  timeout, because an iteration already in flight cannot be
  interrupted.
- **An unexpected error occurs** — every API key rate limited, for
  instance. It is caught and recorded instead of crashing the program.

In every case a `solution.json` is written: `success` says whether a
final answer was given, `stop_reason` tells a solved task from one
stopped by a limit, and `error` holds the exception if one occurred.

| | Subject limit | Agent setting | Sandbox, per execution |
|---|---|---|---|
| MBPP | 10 iterations, 120 s | 5 iterations, 100 s | 15 s, 256 MB |
| SWE-bench | 30 iterations, 900 s | 30 iterations, 840 s | 120 s, 1024 MB |

MBPP stops at 5 iterations on purpose: the evaluation rewards iteration
efficiency, and every extra iteration resends the whole history against
a cumulative budget of 6,000 input tokens.

## Talking to the LLM

Providers and their models are listed in `srcs/call_llm/providers.json`:
Google AI Studio, OpenRouter, Mistral and Groq, all reached through the
same OpenAI-compatible client. When a call is rate limited, the client
switches to the provider's next API key and tries again; each rejected
attempt counts as a retry. Every raw response is appended to
`runs/llm_responses.jsonl`, which keeps what the metrics do not, such as
the `finish_reason`.

## Metrics

Each iteration produces a `StepMetrics`: input and output tokens, request
time in milliseconds, retries, model and provider, the model's reply,
and the code sent to the sandbox with the output it returned. The
`SolutionOutput` adds the totals — tokens summed over the steps,
iterations, API requests including retries, and the elapsed wall-clock
time.

___
# Sandbox design

The `Sandbox` class securely executes the code generated by the agent.

## Execution model

Each call to `execute()` forks a **new child process**. The child
restricts itself, runs the code, and sends a result back to the parent
through a pipe: whether it succeeded, what it printed, the error if
any, and the final answer if `final_answer()` was called. Everything the
code did to the interpreter dies with the child.

The namespace the code runs in replaces `print` so that the output is
captured instead of reaching the terminal, and injects `final_answer()`
and one function per MCP tool. Tool functions take keyword arguments —
`read_file(filepath="/testbed/setup.py")` — and return the tool's text.

**Timeouts keep the partial output.** The printed output only exists in
the child, so only the child can report it. It arms `SIGALRM` for the
policy's time limit before running the code; when the alarm fires, it
catches its own timeout and sends what it had printed. The parent waits
one extra second for that report, then terminates the process if it
never came; `RLIMIT_CPU` remains a last resort should the parent itself
be stuck. A child
killed by the kernel — typically for exceeding its memory — is reported
as a crash with its exit code.

## Why a restricted namespace is not enough

Handing `exec()` a dictionary without `os` filters **names**. CPython's
object graph is not addressed by name but by attributes, and from any
value at all you can walk back to the interpreter:

```python
().__class__.__bases__[0].__subclasses__()   # every class in the process
final_answer.__globals__["os"]               # the module that defined it
```

Neither line imports anything, so an import allowlist never sees them.
Three layers answer this, each covering what the others cannot.

**1. The source is inspected before it is compiled.** The code is parsed
into an abstract syntax tree and refused if it contains an attribute
that leads out — `__globals__`, `__class__`, `__subclasses__`, `__mro__`
and the frame internals `gi_frame`, `tb_frame`, `f_globals` — or a name
that grants execution or attribute access by string: `eval`, `exec`,
`compile`, `getattr`, `vars`. A denylist rather than an allowlist, so
that `super().__init__()` and `def __init__` keep working. The very tree
that was inspected is the one compiled, never a second parse. Format
templates get the same treatment, because `"{0.__class__}".format(x)`
hides its dots inside a string literal.

**2. The namespace hands out no capability.** Builtins are replaced by a
small allowlist in which `__import__`, `open` and `print` are our own
guarded versions: imports are checked against the policy, and `open`
resolves the real path of the file — symbolic links included — before
checking it lies inside an allowed directory. More subtly, the module
that defines those functions keeps **no module and no real builtin in
its own globals**: every import it needs happens inside the function
that uses it. This matters because `injected_function.__globals__` is
exactly that dictionary — if `os` sat there, one attribute lookup would
be enough.

**3. The kernel caps what an escape could do.** The child process sets
its own limits before running anything, each as both the soft and the
hard value so nothing can raise them back: address space
(`RLIMIT_AS`), **no fork at all** (`RLIMIT_NPROC`), maximum file size,
open file descriptors, no core dumps, and CPU time as a backstop above
the wall-clock timeout. Forbidding `fork` is what closes the gap left by
neutralising `socket`: a patched socket only protects this process,
while a shell spawned through `os.system` would carry its own network
stack.

## The policy is data

Imports, readable directories, per-execution timeout and memory ceiling
all come from a `SandboxConfig`, loaded from a JSON template. Each use
gets the policy it needs, without a line of code changing:

| Template | Used by | Imports | Directories | Timeout | Memory |
|---|---|---|---|---|---|
| `sandbox_template.json` | standalone REPL | 16 standard modules | `/testbed`, `/tmp/agent` | 30 s | 512 MB |
| `sandbox_mbpp.json` | MBPP agent | 12 standard modules | none | 15 s | 256 MB |
| `sandbox_swebench.json` | SWE-bench agent | 13 standard modules | `/testbed`, `/tmp/agent` | 120 s | 1024 MB |
| `sandbox_strict.json` | demonstration | `math` only | none | 5 s | 256 MB |

MBPP never touches the filesystem, so it runs with no readable directory
at all. `sandbox_strict.json` exists to demonstrate the point: `import
json` fails under it and succeeds under the default template. A missing
or malformed template falls back to the built-in policy, which is
restrictive.

___
# Tool implementation details

## Two MCP servers, one per benchmark

Tools are exposed to the agent through an MCP server started as a child
process and spoken to over stdio (or HTTP with `--http`). The server
receives its task through an environment variable set by the agent;
started by hand without one, it serves the first matching task in
`cache/`.

- `mcp_tools_mbpp.py` exposes a single tool, `run_tests(code,
  test_list)`. It writes the candidate code followed by the asserts into
  a script, runs it in a working directory on the host, and returns a
  JSON verdict with the combined output.
- `mcp_tools_swebench.py` exposes the nine tools required by the
  subject, because fixing a real bug means exploring a repository
  before touching it.

The sandbox discovers whatever the connected server advertises through
`tools/list`, injects each tool into the execution namespace as a plain
Python function, and generates the tool manual from the same schemas.
Nothing is hardcoded on the client side: connect a different server and
the agent gets different tools, documented accordingly.

`final_answer()` is not one of these tools. It belongs to the sandbox,
because it controls the agent loop rather than acting on the
repository.

## The nine SWE-bench tools

| Tool | Purpose |
|---|---|
| `read_file` | Read a file, or a line range, numbered `cat -n` style |
| `edit_file` | Replace one exact, unique occurrence of a string |
| `list_files` | List a directory, non-recursively, filtered by a glob |
| `search_code` | Recursive regex search across the codebase |
| `search_function_or_class_definition_in_code` | Locate where a symbol is *defined* |
| `find_references` | Locate where a symbol is *used*, definition excluded |
| `run_tests` | Run the task's evaluation script |
| `get_patch` | Stage everything and return the diff against HEAD |
| `run_command` | Run an arbitrary shell command |

## Design decisions

**Every tool returns text, never an object.** The consumer is a language
model, so the return value is what it will read. Search results use one
mandated shape — `/absolute/path:<line> <content>` — so the model can
feed a result straight back into `read_file` or `edit_file`.

**Failures are returned, not raised.** A tool that cannot do its job
answers `"error: ..."`. An exception would abort the sandbox execution
and leave the model with nothing to react to; a returned message keeps
the loop alive and tells it what went wrong.

**`edit_file` refuses ambiguity.** If `old_str` appears more than once
it edits nothing and asks for more surrounding context. Silently
patching the first match is how an agent corrupts a file it cannot see.

**`edit_file` refuses to break a file.** The replacement is parsed
before being written: a `.py` file that parsed before the edit and
would not parse after is reported, and nothing is written. Only the
edit's own damage counts — a file already unparseable is left alone,
since the parse runs on this host rather than in the container.

**`get_patch` cleans before staging.** Running the test suite generates
`__pycache__` and `.pyc` files; they are deleted before `git add`, so
build noise never ends up in a submitted patch.

**Two timeout classes.** Read-only tools get 15 seconds; tools that
spawn a process — `run_tests`, `run_command` — get 300. A grep that
hangs is a bug, a test suite that takes four minutes is normal.

## The execution backend

No tool touches the filesystem itself. Each one receives an
`ExecBackend` and goes through its three operations:

```python
run(cmd, workdir, timeout, bash=False) -> CommandResult
read_file(path) -> str
write_file(path, content) -> None
```

This indirection is what lets the same tool code run in two very
different places:

- **`LocalExecBackend`** executes on the host, confined to a root
  directory. Every path is resolved and any path escaping that root is
  refused. MBPP uses it, and it also stands in for Docker while testing
  the tools.
- **`DockerExecBackend`** executes inside the container named by the
  task's `docker_image` field. SWE-bench uses it, because a task's
  repository comes with its own dependencies and its own Python.

Both report the same `CommandResult` — `stdout`, `stderr`, `exit_code`,
`timed_out` — so a tool cannot tell them apart. Three details worth
knowing:

**Images already present are not pulled again.** The backend looks the
image up in the local Docker store first and only pulls what is missing.
A plain pull contacts the registry every time, which would make every
run depend on Docker Hub being reachable.

**Timeouts are measured, not inferred.** Docker reports a timeout
through the exit code of the `timeout` utility, whose convention
differs between GNU coreutils and BusyBox. Comparing elapsed time
against the limit works the same everywhere.

**Containers are cleaned on every exit path.** The backend registers an
`atexit` handler, supports the `with` statement, and purges any
container left labelled `agent-smith` when it starts. The MCP server
also turns `SIGTERM` into a normal interpreter shutdown, so a killed
agent still runs its cleanup instead of leaking a container.

___
# Benchmark results and analysis

The full report is [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md), generated
from the runs by `make report`. It covers eleven models on the free tiers
of four providers, against seven SWE-bench tasks and ten MBPP tasks, and
holds:

- **how to reproduce** the campaign — commit, budgets, temperature,
  commands;
- **why these tasks and models**, and why others were left out;
- **what the agent is given** — including the task's `hints_text`,
  which on three tasks gives the fix away, and a check that no run
  reached outside its task;
- **results** per model and per cell, each row linked to the
  `solution.json` behind it, every verdict the moulinette's;
- **provider reliability** and the **intermediary metrics**;
- **an ablation** of the sandbox pipe fix, before and after, on the
  same cells;
- **conclusions**, and the model the data would lead us to choose.

