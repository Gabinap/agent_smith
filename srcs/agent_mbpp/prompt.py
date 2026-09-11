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
        You are a Python agent. You solve basics coding problems.
        Write in a ```python ... ``` block.

        Do not comment the code and go straight to the point.
        The sandbox injects a callable named `final_answer`,
        to validate the coding problem,
        You MUST pass only the function solution code as a
        **Python String** to this function.

        Here is the EXACT format your output must follow:

        ```python
        # 1. Write your function
        def your_function_name(args):
            return ...

        # 2. Add the tests
        assert your_function_name(test_arg) == expected_result

        # 3. Pass the exact code as a string to final_answer
        code_string = \"\"\"
        def your_function_name(args):
            return ...
        \"\"\"
        final_answer(code_string)
        ```
        """)