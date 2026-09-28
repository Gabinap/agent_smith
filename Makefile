FLK 	:= uv run flake8
MYPY 	:= uv run mypy
FLAGS	:= --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
ROOTPY	:= mcp_tools_mbpp.py mcp_tools_swebench.py

LLM	:= $(if $(MODEL),--model-name "$(MODEL)") $(if $(PROVIDER),--provider-url "$(PROVIDER)")

# ======================= subject commands =======================

run-mbpp:
	mkdir -p cache runs
	cd srcs && uv run python3 -m agent_mbpp \
		--task-file ../cache/mbpp_task.json \
		--output ../runs/mbpp_solution.json $(LLM)

run-swebench:
	mkdir -p cache runs
	cd srcs && uv run python3 -m agent_swebench \
		--task-file ../cache/swebench_task.json \
		--output ../runs/swebench_solution.json $(LLM)

sandbox:
	uv run sandbox

sandbox-mbpp:
	uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json

sandbox-swebench:
	uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json

backend-mbpp-http:
	SWE_TASK_FILE=./cache/mbpp_task.json uv run python mcp_tools_swebench.py --http

backend-swebench-http:
	SWE_TASK_FILE=./cache/swebench_task.json uv run python mcp_tools_swebench.py --http

sandbox-http:
	uv run sandbox --mcp-server "http://localhost:8000" sandbox_template.json

report:
	uv run srcs/bench_report.py --output BENCHMARK_REPORT.md

bench:
	uv run srcs/bench_matrix.py $(if $(MODELS),--models "$(MODELS)") \
		$(if $(TASKS),--tasks $(TASKS))

bench-mbpp:
	uv run srcs/bench_matrix.py --benchmark mbpp \
		$(if $(MODELS),--models "$(MODELS)") \
		$(if $(TASKS),--tasks $(TASKS))

validate:
	uv run srcs/bench_validate.py $(if $(FORCE),--force) $(if $(JOBS),--jobs $(JOBS))

# ========================= dev commands =========================

install:
	uv sync

lint:
	$(FLK) . --extend-exclude .venv,moulinette
	cd srcs && $(MYPY) . $(FLAGS)
	$(MYPY) $(ROOTPY) --follow-imports=silent $(FLAGS)

lint-strict:
	$(FLK) . --extend-exclude .venv,moulinette
	cd srcs && $(MYPY) . $(FLAGS) --strict
	$(MYPY) $(ROOTPY) --follow-imports=silent $(FLAGS) --strict

debug:
	cd srcs && uv run python3 -m pdb -m agent_mbpp

clean:
	rm -rf __pycache__ .mypy_cache .python-version .vscode
	find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: run-mbpp run-swebench sandbox sandbox-mbpp sandbox-swebench graph \
	report bench bench-mbpp install lint lint-strict debug clean
