import json
import re
from typing import Any

import cli_agent
from code_extract import extract_python
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from rich.console import Console


def python_block_gen(tool_call: ChatCompletionMessageFunctionToolCall) -> str:
    fct_call = tool_call.function
    args = []
    for name, val in json.loads(fct_call.arguments).items():
        args.append(f"{name}={val!r}")
    args_txt = ", ".join(args)
    py_code = f"result = {fct_call.name}({args_txt})\nprint(result)"
    return py_code


def clean_run_tests(text: str) -> str:
    pattern = re.compile(r'^\s*(\+|export |building extension|Link requires)')
    lines = text.splitlines()
    filtered = [line for line in lines if not pattern.match(line)]
    return "\n".join(filtered)


def llm_output_code(console: Console,
                    llm_output_data: dict[str, Any]) -> tuple[str, str]:
    tool_call = llm_output_data.get("tool_calls")
    if tool_call:
        cli_agent.display_llm_tool_call(console, tool_call)
        return python_block_gen(tool_call), ""

    llm_answer = llm_output_data.get("answer")
    cli_agent.display_llm_output(console,
                                 llm_output_data,
                                 llm_answer or "")
    return extract_python(llm_answer)
