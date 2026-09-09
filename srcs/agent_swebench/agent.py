
import re

import cli_agent
from call_llm.calling import LLM

from models.metrics import SolutionOutput, StepMetrics
from models.tasks import SWEBenchTaskInput
from rich.console import Console
from sandbox.mcp_client import McpClient
from sandbox.sandbox import Sandbox, SandboxConfig

from .code_gen import clean_run_tests, llm_output_code, truncate_output
from .prompt import get_prompt, system_content
from .save_data import save_llm_messages, save_output


class SWEBench:
    def __init__(
        self,
        task: SWEBenchTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        client: McpClient,
        max_iteration: int = 30,
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

        self.sandbox = Sandbox(mcp_client=client, config=SandboxConfig())

        # self.py_code = "result = get_patch()\nprint(result)"
        # result = self.sandbox.execute(self.py_code)
        # print(result)
        # output = ast.literal_eval(result.output)
        # print("\n\n\n\n")
        # print(output.get('content')[0].get('text'))
        # print("\n\n\n\n")


        self.max_iteration = max_iteration
        list_tools = self.sandbox.list_tools()
        self.llm = LLM(self.api_url, self.model_name, self.env_key,
                       system_content(list_tools), list_tools)

    def execute(self):
        """Launch the loaded Task

        `total_requests` counts API attempts, not iterations: a step
        rate-limited twice costs three requests.
        """
        self.prompt = get_prompt(self.task)

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1 + self.llm_output_data.get("retries", 0)

        self.py_code = llm_output_code(self.console, self.llm_output_data)

        if self.py_code == "":
            self.llm.messages.append({
                                            "role": "user",
                                            "content": f"No python code generated, you have to write valid python block, example ```python #your code here ```"
                                })
            # Create a first visual
            return

        self.sandbox_data = self.sandbox.execute(self.py_code)

        if self.sandbox_data.error or not self.sandbox_data:
            self.llm.messages.append({
                                "role": "user",
                                "content": f"Input: {self.py_code}\nSandbox Error: {self.sandbox_data.error}\nTool result :\n{self.sandbox_data.output}"
                    })
            cli_agent.display_sandbox(self.console,
                                        self.sandbox_data,
                                        self.py_code)
            return


        if re.search(r'^[^#\n]*\brun_tests\s*\(', self.py_code, re.MULTILINE):

            if '[FAIL]' in self.sandbox_data.output or 'FAILED' in self.sandbox_data.output:
                message = "Test Failed"
            else:
                # [OK], OK
                message = "Test Passed"

            self.llm.messages.append({
                "role": "user",
                "content": message
            })
            cli_agent.display_sandbox_tests(self.console,
                clean_run_tests(self.sandbox_data.output),
                message)
            return

        self.sandbox_data.output = truncate_output(self.sandbox_data.output, max_lines=30)

        self.llm.messages.append({
                    "role": "user",
                    "content": f"Input: {self.py_code}\nSandbox Error: {self.sandbox_data.error}\nTool result :\n{self.sandbox_data.output}"
        })
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def solve_task(self):
        self.error = None
        try:
            while (True):
                if self.step > self.max_iteration:
                    break
                self.execute()
                self.steps.append(self.get_step_metrics())
                save_llm_messages(self.llm.messages)

                if self.sandbox_data and self.sandbox_data.finished:
                    break
                else:
                    self.step += 1
        except Exception as e:
            print(f"Error: {e}")
            self.error = e

        output = self.get_solution_output()
        cli_agent.display_solution(self.console, output)
        save_output(output, self.output_file)

    def get_step_metrics(self) -> StepMetrics:
        """Build the StepMetrics for the current step.

        `retries` is what the LLM call reported: 0 means its first
        attempt went through.
        """
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
                retries=self.llm_output_data.get("retries", 0),
        )

    def get_solution_output(self) -> SolutionOutput:
        if not getattr(self.sandbox_data, "final_answer"):
            self.sandbox_data.final_answer = None
        succes = False if self.sandbox_data.final_answer is None else True

        return SolutionOutput(
            task_id=str(self.task.instance_id),
            benchmark="swebench",
            success=succes,
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
            error=self.error
        )
