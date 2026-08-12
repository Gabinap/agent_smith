from srcs.agents.task_manager import Task
from srcs.call_llm.calling import LLM
from srcs.models.metrics import StepMetrics, SolutionOutput
from srcs.sandbox.sandbox import Sandbox
import re
import datetime


class Mbpp():
    def __init__(self, task_file: str, api_url: str, model_name: str):
        """Load the task and the LLM

        Args:
            task_file (str): Task json file
            api_url (str): Url of the providers
            model_name (str): Name of the model
        """
        self.task = Task(task_file)
        self.llm = LLM(api_url, model_name)
        self.steps: list[StepMetrics]
        self.sandbox = Sandbox()
        self.step = 1
        self.sandbox_output = None
        self.py_code = ""

    def execute(self):
        """Launch the loaded Task
        """
        # prompt = f" \
        #     {self.task.input.task_definition} \
        #     \n Here is the definition of the function:\
        #     {self.task.input.function_definition} \
        #     \n Here some test to see if your function work, add them in your code, a sandbox will run it to see if all work properly: \
        #     {self.task.input.test_list}\
        #     \n Do not comment the code. \
        #     \n Call also the function final_answer(your_solution_code) with your function code to validate the task"
        prompt = f"""
            {self.task.input.task_definition}

            Here is the definition of the function to implement:
            {self.task.input.function_definition}

            Here are some tests to see if your function works. Add them to your code so the sandbox can verify them:
            {self.task.input.test_list}

            CRITICAL INSTRUCTION:
            To validate the task, the sandbox injects a callable named `final_answer`.
            You MUST pass your entire solution code as a **Python String** to this function. Do not pass the function object itself, pass the code as a string. Do not comment the code.

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
        self.llm_output = self.llm.call(prompt)
        raw_code = self.llm_output.get("llm_output")
        match = re.search(r"```python\s*(.*?)```", raw_code, re.DOTALL)
        self.py_code = match.group(1) if match else None
        self.sandbox_output = self.sandbox.execute(self.py_code)

    def solve_task(self):
        while (not self.sandbox_output or not self.sandbox_output.get("finished")):
            print(f"Starting step {self.step}")
            self.execute()
            self.step += 1
            print(self.sandbox_output)
            metric = StepMetrics(
                step=self.step,
                input_tokens=self.llm_output.get("input_tokens"),
                output_tokens=self.llm_output.get("output_tokens"),
                request_time_ms=0.0,
                api_url=self.llm.api_url,
                model_name=self.llm.model_name,
                llm_output=self.llm_output.get("llm_output"),
                sandbox_input=self.py_code,
                sandbox_output=self.sandbox_output.get("output"),
                retries=0
            )
            self.steps.append(metric)
            print(metric)
        print(self.sandbox_output.get("final_answer"))
            # analyser l output de la sanbox et mettre des paramettres special pour le recall
        # output = SolutionOutput(
        #     task_id=self.task.input.task_id ,
        #     benchmark="mbpp",
        #     success=True,
        #     solution=self.sandbox_output.get("final_answer"),
        #     iterations=
        # )




