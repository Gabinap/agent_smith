
import re
import time

import cli_agent
from call_llm.calling import LLM
from models.metrics import SolutionOutput, StepMetrics
from models.sandbox import SandboxResult
from models.tasks import SWEBenchTaskInput
from rich.console import Console
from sandbox.mcp_client import McpClient
from sandbox.sandbox import Sandbox, SandboxConfig

from code_extract import NO_CODE, truncate_output
from .code_gen import clean_run_tests, llm_output_code
from .prompt import get_prompt, system_content
from .save_data import save_output


class SWEBench:
    def __init__(
        self,
        task: SWEBenchTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_keys: list[str],
        console: Console,
        client: McpClient | None,
        max_iteration: int = 30,
        max_time_seconds: int = 60,
        sandbox_config: SandboxConfig | None = None,
    ):
        """Load the task and the LLM

        Args:
            task_file (str): Task json file
            api_url (str): Url of the providers
            model_name (str): Name of the model
            sandbox_config: policy for the sandbox, built-in one if None
        """
        self.output_file = output_file
        self.task = task
        self.steps: list[StepMetrics] = []
        self.step = 1
        self.sandbox_data: SandboxResult | None = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console
        self.max_iteration = max_iteration
        self.max_time_seconds = max_time_seconds
        self.error: Exception | None = None
        self.elapsed_seconds = 0.0
        self.sandbox = Sandbox(
            mcp_client=client, config=sandbox_config or SandboxConfig())
        self.stop_reason = "solved"

        self.llm = LLM(api_url, model_name, env_keys,
                       system_content(self.sandbox.manual()),
                       self.sandbox.list_tools())

    def execute(self) -> None:
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

        self.py_code, repair = llm_output_code(
            self.console, self.llm_output_data)

        if not self.py_code:
            self.llm.messages.append({"role": "user", "content": NO_CODE})
            return

        self.sandbox_data = self.sandbox.execute(self.py_code)

        if self.sandbox_data.error or not self.sandbox_data:
            self.llm.messages.append({
                                "role": "user",
                                "content": f"Input: {self.py_code}\n"
                                f"Sandbox Error: {self.sandbox_data.error}\n"
                                f"Tool result :\n{self.sandbox_data.output}"
                    })
            cli_agent.display_sandbox(self.console,
                                      self.sandbox_data,
                                      self.py_code)
            return

        if re.search(r'^[^#\n]*\brun_tests\s*\(', self.py_code, re.MULTILINE):

            if ('[FAIL]' in self.sandbox_data.output
                    or 'FAILED' in self.sandbox_data.output):
                message = "Test Failed"
            else:
                message = "Test Passed"

            self.llm.messages.append({
                "role": "user",
                "content": message
            })
            cli_agent.display_sandbox_tests(self.console,
                                            clean_run_tests(
                                                self.sandbox_data.output),
                                            message)
            return

        self.sandbox_data.output = truncate_output(
            self.sandbox_data.output, max_lines=30)

        feedback = (f"Input: {self.py_code}\n"
                    f"Sandbox Error: {self.sandbox_data.error}\n"
                    f"Tool result :\n{self.sandbox_data.output}")
        self.llm.messages.append({
            "role": "user",
            "content": f"{repair}\n{feedback}" if repair else feedback,
        })
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def solve_task(self) -> None:
        self.error = None
        start = time.perf_counter()
        try:
            while (True):
                if self.step > self.max_iteration:
                    self.stop_reason = "Iterations limit reached"
                    break
                if time.perf_counter() - start > self.max_time_seconds:
                    self.stop_reason = "Time limit reached"
                    break
                self.execute()
                self.steps.append(self.get_step_metrics())

                if self.sandbox_data and self.sandbox_data.finished:
                    break
                else:
                    self.step += 1
        except Exception as e:
            self.console.print("[bold red] Agentic Loop Error:", e)
            self.error = e

        self.elapsed_seconds = time.perf_counter() - start
        output = self.get_solution_output()
        cli_agent.display_solution(self.console, output)
        save_output(output, self.output_file)

    def get_step_metrics(self) -> StepMetrics:
        """Build the StepMetrics for the current step.

        `retries` is what the LLM call reported: 0 means its first
        attempt went through.

        Token counts are None when the provider omits `usage`, and
        StepMetrics types them as required ints: without these
        fallbacks a silent provider costs the whole run a
        ValidationError.
        """
        return StepMetrics(
                step=self.step,
                input_tokens=self.llm_output_data.get("input_tokens") or 0,
                output_tokens=self.llm_output_data.get("output_tokens") or 0,
                request_time_ms=(
                    self.llm_output_data.get("request_time_ms") or 0.0),
                api_url=self.llm.api_url,
                model_name=self.llm.model_name,
                llm_output=self.llm_output_data.get("answer") or "",
                sandbox_input=self.py_code,
                sandbox_output=(self.sandbox_data.output
                                if self.sandbox_data else ""),
                retries=self.llm_output_data.get("retries", 0),
        )

    def get_solution_output(self) -> SolutionOutput:
        """Assemble the final SolutionOutput for this run.

        A run that never reached final_answer is a normal outcome, not
        a crash: report success=False with an empty solution rather
        than handing None to a field typed as a required str.
        """
        answer = self.sandbox_data.final_answer if self.sandbox_data else None

        return SolutionOutput(
            task_id=str(self.task.instance_id),
            benchmark="swebench",
            success=answer is not None,
            solution=answer or "",
            iterations=len(self.steps),
            total_requests=self.total_requests,
            total_input_tokens=sum(metric.input_tokens or 0
                                   for metric in self.steps),
            total_output_tokens=sum(metric.output_tokens or 0
                                    for metric in self.steps),
            total_time_seconds=self.elapsed_seconds,
            steps=self.steps,
            system_prompt=self.prompt,
            error=str(self.error) if self.error else None,
            stop_reason=self.stop_reason,
        )
