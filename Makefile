FLK 	:= flake8
MYPY 	:= mypy
FLAGS	:= --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

install:
	uv sync

run:
	uv run python3 -m src

debug:
	python -m pdb src/__main__.py

clean:
	rm -rf __pycache__ .mypy_cache .python-version .vscode
	find . -type d -name "__pycache__" -exec rm -rf {} +

lint:
	$(FLK) . --extend-exclude .venv
	$(MYPY) . $(FLAGS)

lint-strict:
	$(FLK) . --extend-exclude .venv
	$(MYPY) . $(FLAGS) --strict

.PHONY: install, run, debug, clean, lint, lint-strict
