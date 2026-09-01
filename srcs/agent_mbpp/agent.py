"""Autonomous agent loop that solves a single MBPP task."""

from .task_manager import Task
from call_llm.calling import LLM
from models.metrics import StepMetrics, SolutionOutput
from sandbox.sandbox import Sandbox

from rich.console import Console
import cli_agent
import re
import datetime
import textwrap


class Mbpp():
    """Run the generate/execute loop for one MBPP task."""

    def __init__(
        self,
        task_file: str,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        max_iteration: int = 2
    ) -> None:
        """Load the task and set up the LLM, sandbox, and console."""
        self.output_file = output_file
        self.task = Task(task_file).input
        self.llm = LLM(api_url, model_name, env_key, self._system_content())
        self.steps: list[StepMetrics] = []
        self.sandbox = Sandbox()
        self.step = 1
        self.sandbox_data = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console
        self.max_iteration = max_iteration

    def execute(self) -> None:
        """Run one generate -> extract -> sandbox-execute cycle."""
        self.prompt = self.get_prompt()

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        llm_answer = self.llm_output_data.get("answer")
        match = self.extract_python(llm_answer)
        self.py_code = match.group(1) if match else None

        cli_agent.display_llm_output(self.console,
                                     self.llm_output_data,
                                     llm_answer)
        self.sandbox_data = self.sandbox.execute(self.py_code)
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def solve_task(self) -> None:
        """Iterate until the task is solved or max_iteration is hit."""
        while (True):
            if self.step > self.max_iteration:
                break
            self.execute()
            metric = self.get_step_metrics()
            self.steps.append(metric)
            if self.sandbox_data.finished:
                break
            else:
                self.step += 1
                self.llm.sandbox_output = self.sandbox_data

        output = self.get_solution_output()
        cli_agent.display_solution(self.console, output)
        self.save_output(output)

    def get_prompt(self) -> str:
        """Build the user prompt describing the task and its tests."""
        tests = '\n'.join(self.task.test_list)
        return f"""
{self.task.task_definition}

Definition of the function: {self.task.function_definition}

Tests to try:
{tests}
"""

    def extract_python(self, text: str | None) -> re.Match[str] | None:
        """Extract the first ```python fenced code block from `text`."""
        return re.search(r"```python\s*(.*?)```", text, re.DOTALL)

    def save_output(self, output: SolutionOutput) -> None:
        """Write `output` to output_file as JSON."""
        with (open(self.output_file, "w", encoding="utf-8") as file):
            file.write(output.model_dump_json(indent=2))

    def get_step_metrics(self) -> StepMetrics:
        """Build the StepMetrics for the current step."""
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
        """Assemble the final SolutionOutput for this run."""
        timestamp = datetime.datetime.now().isoformat()
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="mbpp",
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
