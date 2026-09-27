"""Autonomous agent loop that solves a single MBPP task."""

import datetime
import pathlib
import time
from typing import Any

import cli_agent
from call_llm.calling import LLM
from code_extract import (EMPTY_ANSWER, NO_CODE, extract_python,
                          observation,
                          truncate_output)
from models.metrics import SolutionOutput, StepMetrics
from models.sandbox import SandboxResult
from models.tasks import MBPPTaskInput
from rich.console import Console
from sandbox.mcp_client import McpClient
from sandbox.sandbox import Sandbox, SandboxConfig

from .prompt import get_prompt, system_content

MAX_OUTPUT_LINES = 30

TEMPERATURE: float | None = 0.0


class Mbpp:
    """Run the generate/execute loop for one MBPP task."""

    def __init__(
        self,
        task: MBPPTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_keys: list[str],
        console: Console,
        client: McpClient | None,
        max_iteration: int = 5,
        max_time_seconds: int = 60,
        max_input_tokens: int = 6000,
        max_output_tokens: int = 1500,
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
        self.llm = LLM(api_url, model_name, env_keys,
                       system_content(self.sandbox.manual()),
                       temperature=TEMPERATURE)
        self.step = 1
        self.sandbox_data: SandboxResult | None = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console
        self.max_iteration = max_iteration
        self.error: Exception | None = None
        self.elapsed_seconds = 0.0
        self.max_time_seconds = max_time_seconds
        self.stop_reason = "solved"
        self.empty_answers = 0
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.llm_output_data: dict[str, Any] = {}
        self.started: float | None = None

        self.last_iteration = 0.0

    def execute(self) -> None:
        """Run one generate -> extract -> sandbox-execute cycle.

        `total_requests` counts API attempts, not iterations: a step
        rate-limited twice costs three requests.
        """
        self.sandbox_data = None
        self.prompt = get_prompt(self.task)

        with self.console.status("[bold blue]LLM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(
                self.prompt, self.output_tokens_left(), self.time_left())
        self.total_requests += 1 + self.llm_output_data.get("retries", 0)

        llm_answer = self.llm_output_data.get("answer")
        self.py_code, repair = extract_python(llm_answer)

        cli_agent.display_llm_output(self.console,
                                     self.llm_output_data,
                                     llm_answer or "")

        if not self.py_code:
            self.llm.messages.append({"role": "user", "content": NO_CODE})
            return

        if "final_answer" not in self.py_code:
            self.py_code = f"{self.py_code}\n\
print(run_tests(code={self.py_code!r},  \
test_list={self.task.test_list}))"
        self.sandbox_data = self.sandbox.execute(self.py_code)
        self.sandbox_data.output = truncate_output(
            self.sandbox_data.output, max_lines=MAX_OUTPUT_LINES)
        self.llm.messages.append({
            "role": "user",
            "content": observation(self.sandbox_data.error,
                                   self.sandbox_data.output, repair),
        })
        cli_agent.display_sandbox(self.console,
                                  self.sandbox_data,
                                  self.py_code)

    def output_tokens_left(self) -> int:
        """What the output budget still allows for one generation.

        Capping each call is the only defence against a single runaway
        answer: the loop guard runs between iterations and cannot
        interrupt a generation already under way.
        """
        spent = sum(step.output_tokens for step in self.steps)
        return max(self.max_output_tokens - spent, 1)

    def time_left(self) -> float:
        """Seconds the time budget still allows for one call.

        The same reasoning as `output_tokens_left`, for the clock: the
        guard runs between iterations, so the call it lets through
        overshoots by its own duration. Four runs reached 188 s against
        a 120 s ceiling before this capped the call itself.
        """
        if self.started is None:
            return float(self.max_time_seconds)
        spent = time.perf_counter() - self.started
        return max(self.max_time_seconds - spent, 1.0)

    def out_of_time(self, start: float) -> bool:
        """True when one more iteration would breach the time budget.

        A forecast, like the input-token guard, and for the same reason:
        checking the elapsed time alone lets the iteration it admits run
        past the budget by its own duration. Capping the call is not
        enough — the sandbox runs after it — so the last measured
        iteration is what decides whether another one fits.
        """
        spent = time.perf_counter() - start
        return spent + self.last_iteration > self.max_time_seconds

    def budget_spent(self) -> str:
        """Why one more call would breach a token budget, or "".

        Read from `self.steps`, the very sums the moulinette validates,
        so the guard and the validator can never disagree.

        Input is checked against a forecast, not against the running
        total: the whole conversation is resent every turn, so the next
        call always costs more than the last and a check made after the
        fact comes one call too late. The forecast is the last call
        plus the growth measured between the last two — real data
        rather than a safety factor. Output grows linearly, one code
        block per turn, so the last turn is estimate enough.
        """
        if not self.steps:
            return ""
        spent_in = sum(step.input_tokens for step in self.steps)
        spent_out = sum(step.output_tokens for step in self.steps)
        last_in = self.steps[-1].input_tokens
        growth = (last_in - self.steps[-2].input_tokens
                  if len(self.steps) > 1 else last_in)

        if spent_in + last_in + max(growth, 0) > self.max_input_tokens:
            return "Input token limit reached"
        if spent_out + self.steps[-1].output_tokens > self.max_output_tokens:
            return "Output token limit reached"
        return ""

    def solve_task(self) -> None:
        """Iterate until the task is solved or max_iteration is hit."""
        self.error = None
        start = self.started = time.perf_counter()
        try:
            while (True):
                if self.step > self.max_iteration:
                    self.stop_reason = "Iterations limit reached"
                    break
                if self.out_of_time(start):
                    self.stop_reason = "Time limit reached"
                    break

                spent = self.budget_spent()
                if spent:
                    self.stop_reason = spent
                    break

                began = time.perf_counter()
                self.execute()
                self.last_iteration = time.perf_counter() - began
                self.steps.append(self.get_step_metrics())

                if self.sandbox_data and self.sandbox_data.finished:
                    if (self.sandbox_data.final_answer or "").strip():
                        break
                    self.empty_answers += 1
                    if self.empty_answers > 1:
                        self.stop_reason = "Empty final answer"
                        break
                    self.llm.messages.append(
                        {"role": "user", "content": EMPTY_ANSWER})
                    self.step += 1
                    continue
                else:
                    self.step += 1

        except Exception as e:
            print(f"Error: {e}")
            self.stop_reason = "Agent loop error"
            self.error = e

        self.elapsed_seconds = time.perf_counter() - start
        output = self.get_solution_output()
        cli_agent.display_solution(self.console, output)
        self.save_output(output)

    def save_output(self, output: SolutionOutput) -> None:
        """Write `output` to output_file as JSON."""
        pathlib.Path(self.output_file).parent.mkdir(
            parents=True, exist_ok=True)
        with (open(self.output_file, "w", encoding="utf-8") as file):
            file.write(output.model_dump_json(indent=2))

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
        solution = answer or ""
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="mbpp",
            success=bool(solution.strip()),
            solution=solution,
            iterations=len(self.steps),
            total_requests=self.total_requests,
            total_input_tokens=sum(metric.input_tokens or 0
                                   for metric in self.steps),
            total_output_tokens=sum(metric.output_tokens or 0
                                    for metric in self.steps),
            total_time_seconds=self.elapsed_seconds,
            steps=self.steps,
            system_prompt=self.llm.system_prompt,
            error=str(self.error) if self.error else None,
            timestamp=timestamp,
            stop_reason=self.stop_reason
        )
