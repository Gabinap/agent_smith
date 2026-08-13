from srcs.agents.task_manager import Task
from srcs.call_llm.calling import LLM
from srcs.models.metrics import StepMetrics, SolutionOutput
from srcs.sandbox.sandbox import Sandbox
import re
import datetime


class Mbpp():
    def __init__(self, task_file: str, output_file: str,
                 api_url: str, model_name: str, ui_queue_push=None):
        """Load the task and the LLM

        Args:
            task_file (str): Task json file
            api_url (str): Url of the providers
            model_name (str): Name of the model
        """
        self.output_file = output_file
        self.task = Task(task_file).input
        self.llm = LLM(api_url, model_name)
        self.steps: list[StepMetrics] = []
        self.sandbox = Sandbox()
        self.step = 1
        self.sandbox_output = None
        self.py_code = ""
        self.ui_queue_push = ui_queue_push
        self.update_ui()
        self.total_requests = 0

    def update_ui(self):
        if self.ui_queue_push:
            self.ui_queue_push(self)

    def run_agent(self):

        self.solve_task()
        self.update_ui()
        # time.sleep(5)

    def execute(self):
        """Launch the loaded Task
        """
        self.prompt = f"""
            {self.task.task_definition}

            Here is the definition of the function to implement:
            {self.task.function_definition}

            Here are some tests to see if your function works. Add them to
            your code so the sandbox can verify them:
            {self.task.test_list}

            CRITICAL INSTRUCTION:
            To validate the task, the sandbox injects a callable
            named `final_answer`.
            You MUST pass your entire solution code as a **Python String** to
            this function. Do not pass the function object itself, pass the
            code as a string. Do not comment the code.

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
            final_answer(code_string)"""

        self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        self.llm_output = self.clean_thought_bloc(
            self.llm_output_data.get("llm_output")
        )
        match = self.extract_python(self.llm_output)
        self.py_code = match.group(1) if match else None
        self.sandbox_output = self.sandbox.execute(self.py_code)

    def clean_thought_bloc(self, text):
        return re.sub(r"<thought>.*?</thought>", "",
                      text, flags=re.DOTALL).strip()

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
                sandbox_output=self.sandbox_output.get("output"),
        )

    def get_solution_output(self) -> SolutionOutput:
        timestamp = datetime.datetime.now().isoformat()
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="mbpp",
            success=True,
            solution=self.sandbox_output.get("final_answer"),
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
        print(f"Solving task {self.task.task_id}:")
        while (True):
            print(f"Starting step {self.step}...")
            self.execute()
            print("Step finished, saving metrics")

            metric = self.get_step_metrics()
            self.steps.append(metric)

            if self.sandbox_output.get("finished"):
                break
            else:
                self.step += 1
                # analyser l output de la sanbox et mettre des paramettres
                # special pour le recall

        output = self.get_solution_output()
        self.save_output(output)

    def save_output(self, output: SolutionOutput):
        """Save the Agent output in a Json file.
        Args:
            output (SolutionOutput): solution output
        """
        with (open(self.output_file, "w") as file):
            file.write(output.model_dump_json(indent=2))
