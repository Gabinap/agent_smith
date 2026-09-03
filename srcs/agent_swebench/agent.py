import ast
import datetime
import json
import re


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
from .prompt import get_prompt, system_content
from .code_gen import extract_python, python_block_gen, clean_run_tests


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

        # self.py_code = "result = run_tests()\nprint(result)"
        # result = self.sandbox.execute(self.py_code)
        # output = ast.literal_eval(result.output)
        # print("\n\n\n\n")
        # print(output.get('content')[0].get('text'))
        # print("\n\n\n\n")
        # raise

        self.max_iteration = max_iteration
        list_tools = self.sandbox.list_tools()
        self.llm = LLM(self.api_url, self.model_name, self.env_key,
                       system_content(list_tools), list_tools)

    def execute(self):
        """Launch the loaded Task
        """
        self.prompt = get_prompt(self.task)

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        self.py_code = self.get_python_exec(self.llm_output_data)

        self.sandbox_data = self.sandbox.execute(self.py_code)
        try:
            output = ast.literal_eval(self.sandbox_data.output)
            new_output: str = output.get('structuredContent').get('result')

            if "run_tests()" in self.py_code:
                trace = output.get('content')[0].get('text')

                if '[FAIL]' in trace or 'FAILED' in trace:
                    message = "Test Failed"
                else:
                    # [OK], OK
                    message = "Test Passed"

                self.llm.messages.append({
                    "role": "user",
                    "content": message
                })
                clean_output = clean_run_tests(new_output)
                cli_agent.display_sandbox_tests(self.console,
                    clean_output,
                    message)
                return
            new_lines = [i for i, c in enumerate(new_output) if c == '\n']
            max_lines = 30
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

    def get_python_exec(self, llm_output_data):
        if llm_output_data.get("tool_calls"):
            tool_call = llm_output_data.get("tool_calls")
            cli_agent.display_llm_tool_call(self.console, tool_call)
            py_code = python_block_gen(tool_call)
        else:
            llm_answer = llm_output_data.get("answer")
            cli_agent.display_llm_output(self.console,
                                         llm_output_data,
                                         llm_answer)
            match = extract_python(llm_answer)
            py_code = match.group(1) if match else None
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




