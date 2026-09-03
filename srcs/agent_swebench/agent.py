import ast
import datetime
import json
import re
import textwrap

import cli_agent
from call_llm.calling import LLM
from models import McpSpec
from models.metrics import SolutionOutput, StepMetrics
from models.tasks import SWEBenchTaskInput
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from rich.console import Console
from sandbox.mcp_client import create_mcp_client
from sandbox.sandbox import Sandbox, SandboxConfig


class SWEBench:
    def __init__(
        self,
        task: SWEBenchTaskInput,
        output_file: str,
        api_url: str,
        model_name: str,
        env_key: str,
        console: Console,
        max_iteration: int = 25
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
        self.sandbox = Sandbox(mcp_client=client, config=SandboxConfig())
        self.max_iteration = max_iteration
        print(self._system_content())
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
            tool_call = self.llm_output_data.get("tool_calls")
            cli_agent.display_llm_tool_call(self.console, tool_call)
            self.py_code = self.python_block_gen(tool_call)
        else:
            llm_answer = self.llm_output_data.get("answer")
            match = self.extract_python(llm_answer)
            self.py_code = match.group(1) if match else None
            cli_agent.display_llm_output(self.console,
                                         self.llm_output_data,
                                         llm_answer)
        
        self.sandbox_data = self.sandbox.execute(self.py_code)
        

        try:
            output = ast.literal_eval(self.sandbox_data.output)
            new_output = output.get('structuredContent').get('result')
            
            if "run_tests()" in self.py_code:
                cli_agent.display_sandbox(self.console,
                    self.sandbox_data,
                    new_output)
                match = re.search(r"== tests finished: (.+?) ==", output)
                if match:
                    result = match.group(1)
                    self.llm.messages.append({
                                        "role": "user",
                                        "content": f"test output: {result}"
                            })
                    return
                    
            
            new_lines = [i for i, c in enumerate(new_output) if c == '\n']
            max_lines = 20
            if len(new_lines) > max_lines:
                new_output = new_output[:new_lines[max_lines]]
                new_output += f"\n({len(new_lines)-max_lines} Remaining Lines...)"
            self.sandbox_data.output = new_output
        except Exception:
            pass
        self.llm.messages.append({
                    "role": "user",
                    "content": f"Input: {self.py_code}\nSandbox Error: {self.sandbox_data.error}\nTool result :\n{self.sandbox_data.output}"
        })
        cli_agent.display_sandbox(self.console,
                    self.sandbox_data,
                    self.py_code)

    def python_block_gen(self,
                         tool_call: ChatCompletionMessageFunctionToolCall):
        fct_call = tool_call.function
        args = []
        for name, val in json.loads(fct_call.arguments).items():
            args.append(f"{name}={val!r}")
        args_txt = ", ".join(args)
        py_code = f"result = {fct_call.name}({args_txt})\nprint(result)"
        return py_code

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
Here is the problem
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
        You are an expert Python software engineer resolving bugs step by step.

        Your goal is to fixes the bug.
        
        If you think that you solve the bug, run the tool 'run_tests()',
        if succes, use final_answer(get_patch()) to finish your work.
        
        When you call a tool, always explicitly specify the values of all arguments, never rely on their default values.
        
        Use ONLY the tools, NO import, No install.

""")


# JSON_TO_PY = {
#     "string": "str",
#     "integer": "int",
#     "number": "float",
#     "boolean": "bool",
#     "array": "list",
#     "object": "dict",
#     "null": "None",
# }


# def get_type(arg: Dict[str, Any]) -> str:
#     """Résout une propriété JSON Schema en annotation de type Python."""
#     if "anyOf" in arg:
#         multi_types = [get_type(p) for p in arg["anyOf"]]
#         non_null = [type for type in multi_types if type != "None"]
#         if "None" in multi_types:
#             return f"Optional[{non_null[0]}]" if len(non_null) == 1 else f"Optional[Union[{', '.join(non_null)}]]"
#         return f"Union[{', '.join(multi_types)}]"
#     return JSON_TO_PY.get(arg.get("type", "Any"), "Any")


# def format_default(value: Any) -> str:
#     """Formate une valeur par défaut JSON en littéral Python."""
#     if value is None or value == "null":
#         return "None"
#     if isinstance(value, bool):
#         return str(value)
#     if isinstance(value, str):
#         return repr(value)
#     return repr(value)


# def mcp_tool_to_prototype(tool: Dict[str, Any]) -> str:
#     name = tool["name"]
#     description = tool.get("description", "")
#     schema = tool["inputSchema"]
#     args = schema.get("properties", {})
#     required = set(schema.get("required", []))

#     ordered = [k for k in args if k in required] + [k for k in args if k not in required]

#     params_src = []
#     needs_optional = needs_union = False


#     for key in ordered:
#         prop = args[key]
#         py_type = get_type(prop)
#         needs_optional |= py_type.startswith("Optional")
#         needs_union |= "Union[" in py_type

#         if key in required:
#             params_src.append(f"{key}: {py_type}")
#         else:
#             params_src.append(f"{key}: {py_type} = {format_default(prop.get('default'))}")


#     out_props = tool.get("outputSchema", {}).get("properties", {})
#     return_type = get_type(out_props["result"]) if list(out_props) == ["result"] else "dict"

#     params_joined = ", ".join(params_src)
#     return (
#         f"def {name}({params_joined}) -> {return_type}:\n"
#         f'    """{description}\n'
#         f'    """\n'
#     )
