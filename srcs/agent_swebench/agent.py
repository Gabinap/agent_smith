from call_llm.calling import LLM
from models.metrics import StepMetrics, SolutionOutput
from models.tasks import SWEBenchTaskInput
from sandbox.sandbox import Sandbox, SandboxConfig
from sandbox.mcp_client import create_mcp_client
from models import McpSpec


from rich.console import Console
import cli_agent
import re
import datetime
import textwrap
import json

class SWEBench():
    def __init__(
        self,
        task: SWEBenchTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        max_iteration: int = 20
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
        spec = McpSpec(transport="stdio", command="python3 ../mcp_tools_swebench.py")
        client = create_mcp_client(spec)
        self.sandbox =  Sandbox(mcp_client=client, config=SandboxConfig())
        self.max_iteration = max_iteration
        self.llm = LLM(self.api_url, self.model_name, self.env_key,
                               self._system_content(), self.sandbox.list_tools())


    def execute(self):
        """Launch the loaded Task
        """
        self.prompt = self.get_prompt()

        with self.console.status("[bold blue]LMM Generation...",
                                 spinner_style="blue",
                                 spinner="aesthetic",
                                 speed=0.5):
            self.llm_output_data = self.llm.call(self.prompt)
        self.total_requests += 1

        if self.llm_output_data.get("tool_calls"):
            pass
            # tool_call = self.llm_output_data.get("tool_calls")
            # cli_agent.display_llm_tool_call(self.console, tool_call)
            # mcp_output = self.sandbox.mcp_client.call_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
            # cli_agent.display_tool_result(self.console, mcp_output.get('result'))
            # self.sandbox_data = False
            # self.llm.mcp_output = True
            # content = mcp_output.get('result')
            # content_txt = content.get('content')[0].get('text')
            # new_lines = [i for i, c in enumerate(content_txt) if c == '\n']
            # if len(new_lines) > 20:
            #     content = "Warning: output is too long; please be more specific to reduce the tool's output."

            # self.llm.messages.append({
            #     "role": "tool",
            #     "tool_call_id": tool_call.id,
            #     "content": str(content)
            # })
        else:
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

    def solve_task(self):
        while (True):
            if self.step > self.max_iteration:
                break
            self.execute()
            # metric = self.get_step_metrics()
            # self.steps.append(metric)
            response = json.dumps(
                [
                    m.model_dump() if hasattr(m, "model_dump") else m
                    for m in self.llm.messages
                ],
                indent=2,
                ensure_ascii=False
            )

            with open("llm_messages.json", "w", encoding="utf-8") as file:
                file.write(response)
            if self.sandbox_data and self.sandbox_data.finished:
                break

            else:
                self.step += 1

        # output = self.get_solution_output()
        # cli_agent.display_solution(self.console, output)
        # self.save_output(output)
        print("ENDDDD")

    def get_prompt(self):
        return f"""
{self.task.problem_statement}

"""

    def extract_python(self, text):
        return re.search(r"```python\s*(.*?)```", text, re.DOTALL)

    def save_output(self, output: SolutionOutput):
        """Save the Agent output in a Json file.
        Args:
            output (SolutionOutput): solution output
        """
        with (open(self.output_file, "w", encoding="utf-8") as file):
            file.write(output.model_dump_json(indent=2))

    def get_step_metrics(self) -> StepMetrics:
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
        timestamp = datetime.datetime.now().isoformat()
        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="swebench",
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
            You are operating in a code-based tool calling environment.

            The available tools are Python functions that will be executed by an external sandbox.

            DO NOT use native function calling.
            DO NOT return tool calls.
            DO NOT use JSON tool calls.

            Instead, generate ordinary Python code that calls the available functions.

            For example:

            result = search_code("validate_email")
            print(result)

            content = read_file("models.py", 1, 50)
            print(content)
            """)
