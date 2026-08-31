from call_llm.calling import LLM
from models.metrics import StepMetrics, SolutionOutput
from models.tasks import SWEBenchTaskInput
from sandbox.sandbox import Sandbox, SandboxConfig
from sandbox.mcp_client import create_mcp_client
from models import McpSpec
from typing import Any, Dict

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
        self.sandbox = Sandbox(mcp_client=client, config=SandboxConfig())
        self.max_iteration = max_iteration
        print(self._system_content())
        self.llm = LLM(self.api_url, self.model_name, self.env_key,
                       self._system_content())

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
            self.llm.messages.append({
                        "role": "user",
                        "content": "Do not call tools like that, write them in the python code"
                    })
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
            self.llm.messages.append({
                "role": "user",
                "content": f"Here is the result of the execution :\n{self.sandbox_data}"
            })
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
        mcp_tools = self.sandbox.list_tools()
        tools = ""
        for tool in mcp_tools:
            tools += f"{mcp_tool_to_prototype(tool)}\n\n" 
        return textwrap.dedent(f"""
You are a software engineering agent solving SWE-bench issues, one tool call per turn.

SANDBOX: You can ONLY call the tools listed below. No `import`, no `open()`, no writing your own
scripts. Read/edit/test/run only through these tools.

RULES:
1. ONE tool call per turn. One ```python``` block, then STOP. No text after the block.
2. Thought: max 2 sentences, only about this action. Don't discuss these rules, just follow them.
3. Never invent or guess a tool's output. Wait for the real result.
4. Always store output in a variable and print() it.
5. Always use keyword arguments: `read_file(filepath="...", start_line=1)`.
6. Never write your own reproduction/test scripts. Use run_tests() to verify. If it fails from
   environment/tooling issues (not a real pass/fail), retry once; if still stuck, say so plainly
   instead of finalizing anyway.
7. If a tool call fails twice the same way, change approach — don't repeat it a third time.

TOOLS:
{tools}

DONE: Call final_answer(get_patch()) only after run_tests() has shown a real pass — never on
confidence alone.

FORMAT:
Thought: <1-2 sentences>
```python
result = tool_name(keyword=value)
print(result)
```
            """)


JSON_TO_PY = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}


def get_type(arg: Dict[str, Any]) -> str:
    """Résout une propriété JSON Schema en annotation de type Python."""
    if "anyOf" in arg:
        multi_types = [get_type(p) for p in arg["anyOf"]]
        non_null = [type for type in multi_types if type != "None"]
        if "None" in multi_types:
            return f"Optional[{non_null[0]}]" if len(non_null) == 1 else f"Optional[Union[{', '.join(non_null)}]]"
        return f"Union[{', '.join(multi_types)}]"
    return JSON_TO_PY.get(arg.get("type", "Any"), "Any")


def format_default(value: Any) -> str:
    """Formate une valeur par défaut JSON en littéral Python."""
    if value is None or value == "null":
        return "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return repr(value)
    return repr(value)


def mcp_tool_to_prototype(tool: Dict[str, Any]) -> str:
    name = tool["name"]
    description = tool.get("description", "")
    schema = tool["inputSchema"]
    args = schema.get("properties", {})
    required = set(schema.get("required", []))

    ordered = [k for k in args if k in required] + [k for k in args if k not in required]

    params_src, args_doc = [], []
    needs_optional = needs_union = False


    for key in ordered:
        prop = args[key]
        py_type = get_type(prop)
        needs_optional |= py_type.startswith("Optional")
        needs_union |= "Union[" in py_type

        if key in required:
            params_src.append(f"{key}: {py_type}")
        else:
            params_src.append(f"{key}: {py_type} = {format_default(prop.get('default'))}")


    out_props = tool.get("outputSchema", {}).get("properties", {})
    return_type = get_type(out_props["result"]) if list(out_props) == ["result"] else "dict"

    params_joined = ", ".join(params_src)
    return (
        f"def {name}({params_joined}) -> {return_type}:\n"
        f'    """{description}\n'
        f'    """\n'
    )
