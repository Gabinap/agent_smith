from srcs.agents.task_manager import Task
from srcs.call_llm.calling import LLM
from srcs.models.agent_output import StepMetrics


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
        self.step = 0

    def execute(self):
        """Launch the loaded Task
        """
        prompt = f" \
            {self.task.input.task_definition} \
            \n Here is the definition of the function:\
            {self.task.input.function_definition} \
            \n Here some test to see if your function work: \
            {self.task.input.test_list}\
            \n Do not comment the code"
        answer = self.llm.call(prompt)
        print(answer)
