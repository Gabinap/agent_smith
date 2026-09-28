import re
from typing import Any

import cli_agent
from code_extract import extract_python
from rich.console import Console


def clean_run_tests(text: str) -> str:
    """Removing Useless lines from the run_tests output.

    Args:
        text (str): run_tests output

    Returns:
        str: simplified output
    """
    pattern = re.compile(r'''
        ^\s*(
            \+                   |
            export[ ]            |
            building[ ]extension |
            Link[ ]requires      |
            diff[ ]--git[ ]      |
            old[ ]mode[ ]        |
            new[ ]mode[ ]
        )
    ''', re.VERBOSE)
    lines = text.splitlines()
    filtered = [line for line in lines if not pattern.match(line)]
    return "\n".join(filtered)


def llm_output_code(console: Console,
                    llm_output_data: dict[str, Any]) -> tuple[str, str]:
    """Show the reply and return the code it carries, with any repair.

    The agent acts by writing Python, so the code always comes from a
    block in the answer never from a provider's native tool call,
    which is the paradigm the subject asks us to move past.
    """
    llm_answer = llm_output_data.get("answer")
    cli_agent.display_llm_output(console,
                                 llm_output_data,
                                 llm_answer or "")
    return extract_python(llm_answer)
