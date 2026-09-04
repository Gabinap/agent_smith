
def get_prompt(task) -> str:
    """Build the user prompt describing the task and its tests."""
    tests = '\n'.join(task.test_list)
    return f"""
{task.task_definition}

Definition of the function: {task.function_definition}

Tests to try:
{tests}
"""
