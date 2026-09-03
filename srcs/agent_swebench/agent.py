import ast
import datetime
import json
import re
import textwrap

import cli_agent
from call_llm.calling import LLM
from models import McpSpec
from models.metrics import SolutionOutput, StepMetrics
from models.tasks import SWEBenchTaskInput
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from rich.console import Console
from sandbox.mcp_client import create_mcp_client
from sandbox.sandbox import Sandbox, SandboxConfig


class SWEBench:
    def __init__(
        self,
        task: SWEBenchTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        max_iteration: int = 25
    ):
        """Load the task and the LLM

        Args:
            task_file (str): Task json file
            api_url (str): Url of the providers
            model_name (str): Name of the model
        """
        self.output_file = output_file
        self.task = task
        self.api_url = api_url
        self.model_name = model_name
        self.env_key = env_key
        self.steps: list[StepMetrics] = []

        self.step = 1
        self.sandbox_data = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console
        spec = McpSpec(transport="stdio", command="python3 ../mcp_tools_swebench.py")
        # spec = McpSpec(transport="http", url="http://localhost:8000")
        client = create_mcp_client(spec)
        self.sandbox = Sandbox(mcp_client=client, config=SandboxConfig())
        self.py_code = "result = run_tests()\nprint(result)"
        result = self.sandbox.execute(self.py_code)
        print(result)
        # print(self.sandbox.mcp_client.call_tool("run_tests", {}))

        self.max_iteration = max_iteration
        self.llm = LLM(self.api_url, self.model_name, self.env_key,
                       self._system_content(), self.sandbox.list_tools())

    def execute(self):
        """Launch the loaded Task
        """
        self.prompt = self.get_prompt()

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        if self.llm_output_data.get("tool_calls"):
            tool_call = self.llm_output_data.get("tool_calls")
            cli_agent.display_llm_tool_call(self.console, tool_call)
            self.py_code = self.python_block_gen(tool_call)
        else:
            llm_answer = self.llm_output_data.get("answer")
            match = self.extract_python(llm_answer)
            self.py_code = match.group(1) if match else None
            cli_agent.display_llm_output(self.console,
                                         self.llm_output_data,
                                         llm_answer)
        self.sandbox_data = self.sandbox.execute(self.py_code)
        try:
            output = ast.literal_eval(self.sandbox_data.output)
            new_output:str = output.get('structuredContent').get('result')

            if "run_tests()" in self.py_code:

                all = new_output.split("exit_code:")
                result: str = all[-1]
                if int(result.strip()) == 0:
                    message = "Test Failed"
                else:
                    message = "Test Passed"
                self.llm.messages.append({
                    "role": "user",
                    "content": message
                })
                cli_agent.display_sandbox_tests(self.console,
                    new_output,
                    message,
                    self.py_code)
                return
            new_lines = [i for i, c in enumerate(new_output) if c == '\n']
            max_lines = 20
            if len(new_lines) > max_lines:
                new_output = new_output[:new_lines[max_lines]]
                new_output += f"\n({len(new_lines)-max_lines} Remaining Lines...)"
            self.sandbox_data.output = new_output
        except Exception:
            pass
        self.llm.messages.append({
                    "role": "user",
                    "content": f"Input: {self.py_code}\nSandbox Error: {self.sandbox_data.error}\nTool result :\n{self.sandbox_data.output}"
        })
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def python_block_gen(self,
                         tool_call: ChatCompletionMessageFunctionToolCall):
        fct_call = tool_call.function
        args = []
        for name, val in json.loads(fct_call.arguments).items():
            args.append(f"{name}={val!r}")
        args_txt = ", ".join(args)
        py_code = f"result = {fct_call.name}({args_txt})\nprint(result)"
        return py_code

    def solve_task(self):
        while (True):
            if self.step > self.max_iteration:
                break
            self.execute()
            # metric = self.get_step_metrics()
            # self.steps.append(metric)
            response = json.dumps(
                [
                    m.model_dump() if hasattr(m, "model_dump") else m
                    for m in self.llm.messages
                ],
                indent=2,
                ensure_ascii=False
            )

            with open("llm_messages.json", "w", encoding="utf-8") as file:
                file.write(response)
            if self.sandbox_data and self.sandbox_data.finished:
                break

            else:
                self.step += 1

        # output = self.get_solution_output()
        # cli_agent.display_solution(self.console, output)
        # self.save_output(output)
        print("ENDDDD")

    def get_prompt(self):
        return f"""

{self.task.hints_text}

Here is the problem
{self.task.problem_statement}

"""

    def extract_python(self, text):
        return re.search(r"```python\s*(.*?)```", text, re.DOTALL)

    def save_output(self, output: SolutionOutput):
        """Save the Agent output in a Json file.
        Args:
            output (SolutionOutput): solution output
        """
        with (open(self.output_file, "w", encoding="utf-8") as file):
            file.write(output.model_dump_json(indent=2))

    def get_step_metrics(self) -> StepMetrics:
        return StepMetrics(
                step=self.step,
                input_tokens=self.llm_output_data.get("input_tokens"),
                output_tokens=self.llm_output_data.get("output_tokens"),
                request_time_ms=self.llm_output_data.get("request_time"),
                api_url=self.llm.api_url,
                model_name=self.llm.model_name,
                llm_output=self.llm_output_data.get("answer"),
                sandbox_input=self.py_code,
                sandbox_output=self.sandbox_data.output,
        )

    def get_solution_output(self) -> SolutionOutput:
        timestamp = datetime.datetime.now().isoformat()
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="swebench",
            success=True,
            solution=self.sandbox_data.final_answer,
            iterations=len(self.steps),
            total_requests=self.total_requests,
            total_input_tokens=sum(metric.input_tokens or 0
                                   for metric in self.steps),
            total_output_tokens=sum(metric.output_tokens or 0
                                    for metric in self.steps),
            total_time_seconds=sum(metric.request_time_ms or 0
                                   for metric in self.steps),
            steps=self.steps,
            system_prompt=self.prompt,
            error=None,
            timestamp=timestamp
        )

    def _system_content(self) -> str:
        list_tools = self.sandbox.list_tools()
        tools = build_tool_docs(list_tools)
        return textwrap.dedent(f"""
You are an expert Python software engineer tasked with troubleshooting a bug step by step.

# Objective
Identify and fix the bug in the provided code.

# Rules
1. You have only to communicate by writing Python code in a single ```python ``` block each turn.
2. Only one tool call per code block (never multiple in a row).
3. You may ONLY use the tools listed below—no other actions are permitted.
4. After each call, the sandbox runs your code and returns the output (what was printed using `print`). Use this output to decide on the next step.
5. Explore and understand the code before modifying it (list the files, read the files).
6. Once you think you have fixed the bug, call `run_tests()` to verify that the fix is valid.
7. If the tests pass, finish by calling `final_answer(get_patch())`.

# Expected Format
Always return EXACTLY one block of Python code containing a SINGLE tool call, for example:

​```python
result = list_files(directory=“.”, pattern="*")
print(result)
​```

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
