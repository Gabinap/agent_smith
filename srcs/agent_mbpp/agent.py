"""Autonomous agent loop that solves a single MBPP task."""

import datetime
import time

import cli_agent
from call_llm.calling import LLM
from code_extract import NO_CODE, extract_python, truncate_output
from models.metrics import SolutionOutput, StepMetrics
from rich.console import Console
from sandbox.mcp_client import McpClient
from sandbox.sandbox import Sandbox, SandboxConfig

from .prompt import get_prompt, system_content
from .task_manager import Task

# MBPP has 6000 input tokens for the whole run: a single unbounded
# output can eat the budget the remaining iterations need.
MAX_OUTPUT_LINES = 30


class Mbpp:
    """Run the generate/execute loop for one MBPP task."""

    def __init__(
        self,
        task: Task,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        client: McpClient,
        max_iteration: int = 5,
        max_time_seconds: int = 60,
        sandbox_config: SandboxConfig | None = None,
    ) -> None:
        """Load the task and set up the LLM, sandbox, and console.

        `sandbox_config` defaults to the built-in policy, so an agent
        built without one still runs inside a restricted sandbox.
        """
        self.output_file = output_file
        self.task = task
        self.steps: list[StepMetrics] = []
        self.sandbox = Sandbox(
            mcp_client=client, config=sandbox_config or SandboxConfig())
        self.llm = LLM(api_url, model_name, env_key,
                       system_content(self.sandbox.manual()), [])
        self.step = 1
        self.sandbox_data = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console
        self.max_iteration = max_iteration
        self.error: Exception | None = None
        self.elapsed_seconds = 0.0
        self.max_time_seconds = max_time_seconds
        self.stop_reason = "solved"

    def execute(self) -> None:
        """Run one generate -> extract -> sandbox-execute cycle.

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

        llm_answer = self.llm_output_data.get("answer")
        self.py_code, repair = extract_python(llm_answer)

        cli_agent.display_llm_output(self.console,
                                     self.llm_output_data,
                                     llm_answer)

        if not self.py_code:
            self.llm.messages.append({"role": "user", "content": NO_CODE})
            return

        self.sandbox_data = self.sandbox.execute(self.py_code)
        self.sandbox_data.output = truncate_output(
            self.sandbox_data.output, max_lines=MAX_OUTPUT_LINES)
        feedback = (f"Input: {self.py_code}\n"
                    f"Sandbox Error: {self.sandbox_data.error}\n"
                    f"Output :\n{self.sandbox_data.output}")
        self.llm.messages.append({
            "role": "user",
            "content": f"{repair}\n{feedback}" if repair else feedback,
        })
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def solve_task(self) -> None:
        """Iterate until the task is solved or max_iteration is hit."""
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
            print(f"Error: {e}")
            self.error = e

        self.elapsed_seconds = time.perf_counter() - start
        output = self.get_solution_output()
        cli_agent.display_solution(self.console, output)
        self.save_output(output)

    def save_output(self, output: SolutionOutput) -> None:
        """Write `output` to output_file as JSON."""
        with (open(self.output_file, "w", encoding="utf-8") as file):
            file.write(output.model_dump_json(indent=2))

    def get_step_metrics(self) -> StepMetrics:
        """Build the StepMetrics for the current step.

        `retries` is what the LLM call reported: 0 means its first
        attempt went through.
        """
        return StepMetrics(
                step=self.step,
                input_tokens=self.llm_output_data.get("input_tokens"),
                output_tokens=self.llm_output_data.get("output_tokens"),
                request_time_ms=self.llm_output_data.get("request_time_ms"),
                api_url=self.llm.api_url,
                model_name=self.llm.model_name,
                llm_output=self.llm_output_data.get("answer"),
                sandbox_input=self.py_code,
                sandbox_output=(self.sandbox_data.output
                                if self.sandbox_data else ""),
                retries=self.llm_output_data.get("retries", 0)
        )

    def get_solution_output(self) -> SolutionOutput:
        """Assemble the final SolutionOutput for this run.

        A run that never reached final_answer is a normal outcome, not
        a crash: report success=False with an empty solution rather
        than handing None to a field typed as a required str.
        """
        timestamp = datetime.datetime.now().isoformat()
        answer = self.sandbox_data.final_answer if self.sandbox_data else None
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="mbpp",
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
            timestamp=timestamp,
            stop_reason=self.stop_reason
        )
