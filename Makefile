FLK 	:= uv run flake8
MYPY 	:= uv run mypy
FLAGS	:= --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
ROOTPY	:= mcp_tools_mbpp.py mcp_tools_swebench.py

# optional: make run-mbpp MODEL="qwen/qwen3.5-flash-02-23" PROVIDER="https://openrouter.ai/api/v1"
LLM	:= $(if $(MODEL),--model-name "$(MODEL)") $(if $(PROVIDER),--provider-url "$(PROVIDER)")

# ======================= subject commands =======================

run-mbpp:
	mkdir -p cache
	cd srcs && uv run python3 -m agent_mbpp \
		--task-file ../cache/mbpp_task.json \
		--output ../cache/mbpp_solution.json $(LLM)

run-swebench:
	mkdir -p cache
	cd srcs && uv run python3 -m agent_swebench \
		--task-file ../cache/swebench_task.json \
		--output ../cache/swebench_solution.json $(LLM)

# TODO: the 3 sandbox targets need a [project.scripts] sandbox entry in
# pyproject.toml and a sandbox_template.json — neither exists yet (M8.c)
sandbox:
	uv run sandbox

sandbox-mbpp:
	uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json

sandbox-swebench:
	uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json

graph:
	uv run srcs/build_graph.py

# the Markdown sections of BENCHMARK_REPORT.md, derived from runs/
report:
	uv run srcs/bench_report.py

# one solution.json per (model, task); re-running skips what is done
# make bench MODELS="codestral-latest,openai/gpt-oss-20b" TASKS="cache/a.json"
bench:
	uv run srcs/bench_matrix.py $(if $(MODELS),--models "$(MODELS)") \
		$(if $(TASKS),--tasks $(TASKS))

# ========================= dev commands =========================

install:
	uv sync

test:
	uv run pytest -q

# srcs/ and the root scripts are separate import roots, hence two mypy runs.
# --follow-imports=silent: still type-checks srcs/ for context, but reports
# only the errors of the files listed, so nothing is reported twice.
lint:
	$(FLK) . --extend-exclude .venv
	cd srcs && $(MYPY) . $(FLAGS)
	$(MYPY) $(ROOTPY) --follow-imports=silent $(FLAGS)

lint-strict:
	$(FLK) . --extend-exclude .venv
	cd srcs && $(MYPY) . $(FLAGS) --strict
	$(MYPY) $(ROOTPY) --follow-imports=silent $(FLAGS) --strict

debug:
	cd srcs && uv run python3 -m pdb -m agent_mbpp

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .python-version .vscode
	find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: run-mbpp run-swebench sandbox sandbox-mbpp sandbox-swebench graph \
	report bench install test lint lint-strict debug clean
