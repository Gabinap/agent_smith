import textwrap

from models.tasks import SWEBenchTaskInput


def get_prompt(task: SWEBenchTaskInput) -> str:
    prompt = f"REPO: {task.repo}\n"
    if task.hints_text:
        prompt += f"HINT: {task.hints_text}\n"
    prompt += f"PROBLEM: {task.problem_statement}\n"
    return prompt


# The structured response slots and the worked loop the subject asks
# for (V.1.6).
REASONING_GUIDE = """
# How to answer
Every turn has three parts. Only the code runs, the rest is what
makes the next call a deduction instead of a guess.

Thought: one or two sentences. What the last Observation established,
and what this call is meant to find out.
Code: exactly one fenced python block, exactly one tool call.
Observation: what the sandbox prints back. You never write it.

# A worked loop
Thought: I do not know where the failing function lives, so I look it
up by name instead of guessing a path.
```python
result = search_function_or_class_definition_in_code(name="get_names")
print(result)
```
Observation: /testbed/app/query.py:1204 def get_names(self):

Thought: I have the file and the line. I read around it before
changing anything.
```python
result = read_file(filepath="/testbed/app/query.py",
                   start_line=1195, end_line=1215)
print(result)
```
Observation: the numbered source of those lines.

Thought: line 1207 uses the result without checking for None. I
replace that one line, with enough context for the match to be
unique.
```python
result = edit_file(
    filepath="/testbed/app/query.py",
    old_str="        names = self.get_names()",
    new_str="        names = self.get_names() or []",
)
print(result)
```
Observation: ok: /testbed/app/query.py updated

Thought: the edit is in. I run the suite before claiming anything.
```python
print(run_tests())
```
Observation: Test Passed

Thought: the suite is green, so I submit the patch it produced.
```python
final_answer(get_patch())
```

# What that loop shows
Locate before reading, read before editing, test before submitting.
When a call comes back empty twice, change tool rather than retrying
a variation of the same query.
"""


def system_content(tools: str) -> str:
    """Build the system prompt around the sandbox's own tool manual."""
    return textwrap.dedent("""
You are an expert Python software engineer tasked with troubleshooting
a bug step by step.

# Objective
Identify and fix the bug in the provided code, keeping in mind the
hint, if there is one.

# Rules
1. You have only to communicate by writing Python code in a single
   ```python ``` block each turn.
2. Only one tool call per code block (never multiple in a row).
3. You may ONLY use the tools listed below. No other actions are
   permitted.
4. After each call, the sandbox runs your code and returns the output
   (what was printed using `print`). Use this output to decide on the
   next step.
5. Explore before modifying: use `search_code`,
   `search_function_or_class_definition_in_code` to locate code and
   `run_command("find ...")` to locate files. Switch tools after two
   failed/empty attempts, don't retry variations.
6. Once you think you have fixed the bug, call `run_tests()` to verify
   that the fix is valid.
7. If the tests pass, finish by calling `final_answer(get_patch())`.

# Expected Format
Always return EXACTLY one block of Python code containing a SINGLE
tool call, for example:

```python
result = list_files(directory=".", pattern="*")
print(result)
```

# Available Tools
""").strip() + f"\n{tools}\n{REASONING_GUIDE}"
