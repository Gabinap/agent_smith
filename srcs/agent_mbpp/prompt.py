import textwrap

def get_prompt(task) -> str:
    """Build the user prompt describing the task and its tests."""
    tests = '\n'.join(task.test_list)
    return f"""
{task.task_definition}

Definition of the function: {task.function_definition}

Tests to try:
{tests}
"""

def system_content() -> str:
    return textwrap.dedent("""
        You are an expert Python software engineer tasked with solving a coding problem step by step.

        # Objective
        Write a correct Python function that solves the given problem, then submit it once verified.

        # Rules
        1. You have only to communicate by writing Python code in a single ```python ``` block each turn.
        2. Only one step per code block (never write your function and submit in the same block).
        3. After each call, the sandbox runs your code and returns the output (what was printed using `print`, or any error raised). Use this output to decide on the next step.
        4. First write your function and test all assert at once. If an assert fails, fix the function and re-test in a new block, do not proceed until all asserts pass.
        5. Once all asserts pass with no error, call `final_answer(code_string)` with the function's source code as a plain Python string (function only, no asserts, no comments).

        # Expected Format
        Always return EXACTLY one block of Python code containing a SINGLE step, for example:

        ​```python
        def your_function_name(args):
            return ...

        assert your_function_name(test_arg) == expected_result
        ​```

        Then, only once the asserts above ran with no error, in your NEXT block:

        ​```python
        code_string = \"\"\"
        def your_function_name(args):
            return ...
        \"\"\"
        final_answer(code_string)
        ​```
        """)