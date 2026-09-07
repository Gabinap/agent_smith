import textwrap
from typing import Any

from models.tasks import SWEBenchTaskInput


def get_prompt(task: SWEBenchTaskInput):
    prompt = f"REPO: {task.repo}\n"
    if task.hints_text:
        prompt += f"HINT: {task.hints_text}\n"
    prompt += f"PROBLEM: {task.problem_statement}\n"
    return prompt


def system_content(list_tools: list[dict[str, Any]]) -> str:
    tools = build_tool_docs(list_tools)
    return textwrap.dedent(f"""
You are an expert Python software engineer tasked with troubleshooting a bug step by step.

# Objective
Identify and fix the bug in the provided code, keeping in mind the hint, if there is one.

# Rules
1. You have only to communicate by writing Python code in a single ```python ``` block each turn.
2. Only one tool call per code block (never multiple in a row).
3. You may ONLY use the tools listed below—no other actions are permitted.
4. After each call, the sandbox runs your code and returns the output (what was printed using `print`). Use this output to decide on the next step.
5. Explore before modifying: use `search_code`, `search_function_or_class_definition_in_code` to locate code and `run_command("find ...")` to locate files. Switch tools after two failed/empty attempts, don't retry variations.
6. Once you think you have fixed the bug, call `run_tests()` to verify that the fix is valid.
7. If the tests pass, finish by calling `final_answer(get_patch())`.

# Expected Format
Always return EXACTLY one block of Python code containing a SINGLE tool call, for example:

\u200b```python
result = list_files(directory=“.”, pattern="*")
print(result)
\u200b```

# Available Tools
{tools}
""")


def build_tool_docs(list_tools) -> str:
    schemas = list_tools
    lines: list[str] = []
    for schema in schemas:
        name = schema.get("name", "")
        description = schema.get("description", "")
        props = schema.get("inputSchema", {}).get("properties", {})
        params = ", ".join(
            f"{k}: {v.get('type', 'str')}"
            for k, v in props.items()
        )
        line_text = (
            f"- {name}({params}): "
            f"{description}"
        )
        lines.append(line_text)
    lines.append(
        "- final_answer(answer): Submit the final solution (patch string) "
        "and stop"
    )
    return "\n".join(lines)
