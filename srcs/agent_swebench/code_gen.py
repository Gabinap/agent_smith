import re
import json
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)


def extract_python(text: str):
    return re.search(r"```python\s*(.*?)```", text, re.DOTALL)


def python_block_gen(tool_call: ChatCompletionMessageFunctionToolCall) -> str:
    fct_call = tool_call.function
    args = []
    for name, val in json.loads(fct_call.arguments).items():
        args.append(f"{name}={val!r}")
    args_txt = ", ".join(args)
    py_code = f"result = {fct_call.name}({args_txt})\nprint(result)"
    return py_code
