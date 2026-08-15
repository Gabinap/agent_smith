from .task_manager import Task
from call_llm.calling import LLM
from models.metrics import StepMetrics, SolutionOutput
from models.tasks import MBPPTaskInput
from sandbox.sandbox import Sandbox
from rich.text import Text
from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress
from rich.table import Table
import questionary

import re
import datetime


class Mbpp():
    def __init__(self, task_file: str, output_file: str,
                 api_url: str, model_name: str, env_key: str, console: Console):
        """Load the task and the LLM

        Args:
            task_file (str): Task json file
            api_url (str): Url of the providers
            model_name (str): Name of the model
        """
        self.output_file = output_file
        self.task = Task(task_file).input
        self.llm = LLM(api_url, model_name, env_key)
        self.steps: list[StepMetrics] = []
        self.sandbox = Sandbox()
        self.step = 1
        self.sandbox_data = None
        self.py_code = ""
        self.total_requests = 0
        self.console = console


    def execute(self):
        """Launch the loaded Task
        """
        tests = '\n'.join(self.task.test_list)
        self.prompt = f"""
{self.task.task_definition}

Definition of the function: {self.task.function_definition}

Tests to try:
{tests}
"""
        with self.console.status("[bold blue]LMM Generation...", spinner_style="blue", spinner="aesthetic",speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        self.thought, self.llm_output = self.clean_thought_bloc(
            self.llm_output_data.get("llm_output")
        )
        match = self.extract_python(self.llm_output)
        self.py_code = match.group(1) if match else None
        table = Table(padding=1).grid(padding=(0, 2))
        table.add_column(style="bold")
        table.add_column()

        table.add_row("Model:", self.llm_output_data.get("model_name"))
        table.add_row("Input tokens:", str(self.llm_output_data.get("input_tokens")))
        table.add_row("Output tokens:", str(self.llm_output_data.get("output_tokens")))
        table.add_row("Request time:", f"{self.llm_output_data.get('request_time')}s")
        content = Group(
            Text("Code:", style="bold white", end="\n\n"),
            Syntax(self.py_code, "python", theme="stata-dark", line_numbers=True),
            "\n",
            table
        )
        self.console.print(Panel(
            content,
            title="LLM answer",
            border_style="blue"
        ))
        self.sandbox_data = self.sandbox.execute(self.py_code)
        
        if self.sandbox_data.error is None:
            msg_error = "No Errors"
        else:
            msg_error = self.sandbox_data.error
        sandbox_cli = Group(
            Text("Input:", style="bold white", end="\n\n"),
            Syntax(self.py_code.strip(), "python", theme="stata-dark"),
            Text("\nOutput:", style="bold white", end="\n\n"),
            Syntax(self.sandbox_data.output, "python", theme="stata-dark"),
            Text("\nErrors:", style="bold white", end="\n\n"),
            Syntax(msg_error, "python", theme="stata-dark"),
            Text("\nFinal result:", style="bold white", end="\n\n"),
            Syntax(self.sandbox_data.final_answer, "python", theme="stata-dark", line_numbers=True),
        )
        self.console.print(Panel(sandbox_cli, title=f"[bold orange1]SANDBOX output", border_style="orange1"))
            
        

    def clean_thought_bloc(self, text):
        match = re.search(r"<thought>(.*?)</thought>", text, flags=re.DOTALL)

        thought = match.group(1).strip() if match else ""

        clean_text = re.sub(
            r"<thought>.*?</thought>",
            "",
            text,
            flags=re.DOTALL
        ).strip()

        return thought, clean_text

    def extract_python(self, text):
        return re.search(r"```python\s*(.*?)```", text, re.DOTALL)

    def get_step_metrics(self) -> StepMetrics:
        return StepMetrics(
                step=self.step,
                input_tokens=self.llm_output_data.get("input_tokens"),
                output_tokens=self.llm_output_data.get("output_tokens"),
                request_time_ms=self.llm_output_data.get("request_time"),
                api_url=self.llm.api_url,
                model_name=self.llm.model_name,
                llm_output=self.llm_output,
                sandbox_input=self.py_code,
                sandbox_output=self.sandbox_data.output,
        )

    def get_solution_output(self) -> SolutionOutput:
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

    def solve_task(self):
        while (True):
            self.execute()
            metric = self.get_step_metrics()
            self.steps.append(metric)
            if self.sandbox_data.finished:
                break
            else:
                self.step += 1
                # analyser l output de la sanbox et mettre des paramettres
                # special pour le recall
        output = self.get_solution_output()
        output_cli = Group(
            Text.from_markup(f"[bold]Total input tokens:[/bold] {output.total_input_tokens}"),
            Text.from_markup(f"[bold]Total output tokens:[/bold] {output.total_output_tokens}"),
            Text.from_markup(f"[bold]Total request time:[/bold] {output.total_time_seconds}s"),
            Text("\nSolution:", style="bold white", end="\n\n"),
            Syntax(output.solution, "python", theme="stata-dark"),
        )
        self.console.print(Panel(output_cli, title=f"[bold green3]Solution output", border_style="green3"))
        self.save_output(output)
        exits=['Show the think process', 'Show the prompt', 'Exit']
        while(True):
            selected = questionary.select(
                "Select an option",
                choices=exits,
            ).ask()
            if selected == None : return
            match exits.index(selected):
                case 0:
                    self.console.print(Panel(
                        Text(self.thought, style="italic"),
                        title="Thought",
                        title_align="left",
                        border_style="white"
                    ))
                case 1:
                    self.console.print(Panel(
                        Text(output.system_prompt, style="italic"),
                        title="Prompt",
                        title_align="left",
                        border_style="white"
                    ))
                case 2:
                    return
                
        

    def save_output(self, output: SolutionOutput):
        """Save the Agent output in a Json file.
        Args:
            output (SolutionOutput): solution output
        """
        with (open(self.output_file, "w") as file):
            file.write(output.model_dump_json(indent=2))
