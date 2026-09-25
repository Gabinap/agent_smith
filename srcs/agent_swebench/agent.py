
import re
import time
from typing import Any

import cli_agent
from call_llm.calling import LLM
from models.metrics import SolutionOutput, StepMetrics
from models.sandbox import SandboxResult
from models.tasks import SWEBenchTaskInput
from rich.console import Console
from sandbox.mcp_client import McpClient
from sandbox.sandbox import Sandbox, SandboxConfig

from code_extract import (EMPTY_ANSWER, NO_CODE, observation,
                          summarise_tests, truncate_output)
from .code_gen import clean_run_tests, llm_output_code
from .prompt import get_prompt, system_content
from .save_data import save_output


TEMPERATURE: float | None = 0.0


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
        max_input_tokens: int = 300_000,
        max_output_tokens: int = 10_000,
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
        self.empty_answers = 0
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.llm_output_data: dict[str, Any] = {}
        # Set when the loop starts
        self.started: float | None = None
        # How long the last iteration took
        self.last_iteration = 0.0

        self.llm = LLM(api_url, model_name, env_keys,
                       system_content(self.sandbox.manual()),
                       temperature=TEMPERATURE)

    def execute(self) -> None:
        """Launch the loaded Task

        `total_requests` counts API attempts, not iterations: a step
        rate-limited twice costs three requests.
        """
        # Each iteration starts without a result: a step that never
        # reaches the sandbox must not inherit the previous one's.
        self.sandbox_data = None
        self.prompt = get_prompt(self.task)

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(
                self.prompt, self.output_tokens_left(),
                self.time_left())
        self.total_requests += 1 + self.llm_output_data.get("retries", 0)

        self.py_code, repair = llm_output_code(
            self.console, self.llm_output_data)

        if not self.py_code:
            self.llm.messages.append({"role": "user", "content": NO_CODE})
            return

        self.sandbox_data = self.sandbox.execute(self.py_code)

        if self.sandbox_data.error:
            self.llm.messages.append({
                "role": "user",
                "content": observation(self.sandbox_data.error,
                                       self.sandbox_data.output, repair),
            })
            cli_agent.display_sandbox(self.console,
                                      self.sandbox_data,
                                      self.py_code)
            return

        if re.search(r'^[^#\n]*\brun_tests\s*\(', self.py_code, re.MULTILINE):

            # The verdict alone leaves the model unable to know which
            # test broke; the whole log swamps the conversation. The
            # summary is what unittest itself reports.
            message = summarise_tests(self.sandbox_data.output)

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
        overshoots the budget by its own duration.
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
        iteration is what decides whether another one fits. One run
        reached 1 008 s against a 900 s ceiling without this.
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
        fact comes one call too late.
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
                    # One chance to do the work, then stop. Told twice
                    # and still empty, a model repeats the same call
                    # forever: measured 13 identical submissions.
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
            self.console.print("[bold red] Agentic Loop Error:", e)
            self.stop_reason = "Agent loop error"
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
        solution = answer or ""

        return SolutionOutput(
            task_id=str(self.task.instance_id),
            benchmark="swebench",
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
            stop_reason=self.stop_reason,
        )
