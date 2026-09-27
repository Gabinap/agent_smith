import textwrap

from models.tasks import MBPPTaskInput


def get_prompt(task: MBPPTaskInput) -> str:
    """Build the user prompt describing the task and its tests."""
    tests = '\n'.join(task.test_list)
    return f"""
{task.task_definition}

Definition of the function: {task.function_definition}

Tests executed:
{tests}
"""


def system_content(tools: str = "") -> str:
    """Build the system prompt around the sandbox's own tool manual.

    The manual is appended after dedenting rather than interpolated
    into the template: its own lines start at column 0, so a manual of
    two tools or more leaves `textwrap.dedent` no common prefix to
    strip and the whole prompt goes out indented: wasted tokens on a
    6000-token budget, and a `system_prompt` that no longer starts
    where the prompt starts.
    """
    return textwrap.dedent("""
        You are an expert Python software engineer tasked with solving
        a coding problem step by step.

        # Objective
        Write a correct Python function that solves the given problem,
        then submit it once verified.

        # Rules
        1. You have only to communicate by writing Python code in a
           single ```python ``` block each turn.
        2. Only one step per code block (never write your function and
           submit in the same block).
        3. After each turn, the test framework automatically runs `run_tests`
           on your defined function and returns the result (a JSON response
           with a `success` status and output). Use this automatic feedback to
           decide on your next step.
        4. DO NOT write `assert` statements or call `run_tests` yourself.
           Simply define your function in the code block.
        5. If the automatic test output indicates a failure, fix the function
           in a new code block and let the framework re-test it.
        6. Once the automatic test output shows that all tests passed
           (`success: true`), call `final_answer(code_string)` in
           your NEXT block with the function's source code as a plain
           Python string (function only, no comments, no test harness
           code).

        # Expected Format
        First, write your function definition:

        ```python
        def your_function_name(args):
            return ...
        ```

        (The test framework automatically appends the test execution
        to your code and gives you the output in the next turn.)

        Then, only once the automatic output confirms all tests passed:

        ```python
        code_string = \"\"\"
        def your_function_name(args):
            return ...
        \"\"\"
        final_answer(code_string)
        ```

        # Available Tools
        """).strip() + f"\n{tools}\n"
