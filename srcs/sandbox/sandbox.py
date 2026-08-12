import builtins
from typing import Dict, Any, Optional, Callable
import signal
import os

from srcs.models.sandbox import SandboxConfig


class SecurityError(PermissionError):
    """Security Rules are not respected"""
    pass


class TimeoutError(Exception):
    """Execution time limit exceeded"""
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")


class Sandbox():
    def __init__(self):
        """
        Sandbox to execute code taht can be vulnerable
        """
        self.config = SandboxConfig()
        self.namespace: Dict[str, Any] = {}

        self.final_answer_value: Optional[Any] = None
        self.has_finished = False

        self.stdout = []

        self._setup_namespace()

    def _is_import_allowed(self, name):
        """
        Check if a module can be imported
        Args:
            name: str = module name
        Returns:
            bool: True if the module import is allowed, False otherwise
        """
        base_pkg = name.split(".")[0]
        for pattern in self.config.authorized_imports:
            if pattern.endswith(".*"):
                pkg = pattern[:-2]
                if base_pkg == pkg or name.startswith(f"{pkg}."):
                    return True
            elif name == pattern or base_pkg == pattern:
                return True
        return False

    def _custom_import(
            self,
            name: str,
            globals=None,
            locals=None,
            fromlist=(),
            level=0
            ):
        """
        Rewriting the import function to restrict imports usage
        Args:
            name: str = module name
            globals: None | dict = context variable from the executed program
            locals: None | dict = context variable from the executed program
            fromlist: Any = the function to import from a module
                like 'sqrt' from math
            level: int = import type relative import or absolute, 0 = absolute
        Returns:
            module: The module required
        """
        if not self._is_import_allowed(name):
            raise SecurityError("Import forbidden by sandbox"
                                f" policy: '{name}'")
        return builtins.__import__(name, globals, locals, fromlist, level)

    def _is_open_allowed(self, filepath: str):
        """
        Check if a file can be open
        Args:
            filepath: str = file path
        Returns:
            bool: True if opening this file is allowed, False otherwise
        """
        for allowed_dir in self.config.allowed_directories:
            real_allowed = os.path.realpath(allowed_dir)
            if filepath == real_allowed or filepath.startswith(
                    real_allowed + os.sep):
                return True
        return False

    def _custom_open(self, file: Any, mode: str = "r", *args, **kwargs):
        """
        Rewriting the open function to restrict open usage
        Args:
            file: str = file path
            mode: str = The type of action we have to do in the file
            args:
            kwargs:
        Returns:
            IO: Opened file stream
        """
        filepath = os.path.realpath(str(file))
        if not self._is_open_allowed(filepath):
            raise SecurityError(
                f"Access denied to file path '{filepath}'."
                f" Allowed directories: {self.config.allowed_directories}"
            )
        return builtins.open(file, mode, *args, **kwargs)

    def _custom_print(self, *args, **kwargs):
        """
        Rewriting the function print for the agent to capture
        the standard output and not printing it in the terminal
        Args:
            *args
            **kwargs
        Returns:
            Any: the printed variable from the agent code
        """
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        text = sep.join(str(a) for a in args) + end
        self.stdout.append(text)
        return None

    def _final_answer_tool(self, answer: Any) -> Any:
        """
        The implementation of the function final_answer function,
        that the LLM can use to signal that this is the print to return
        Args:
            answer: Any = the answer from the agent
        Returns: Any = the answer from the agent
        """
        self.final_answer_value = answer
        self.has_finished = True
        return answer

    def register_tool(self, name: str, func: Callable):
        """
        Inject new functions tools to the white list
        Args:
            name: str = The name that the agent as to call
            func: Callable = The code that as to be done
                when the agent call the named function
        """
        self.namespace[name] = func

    def _setup_namespace(self):
        """
        Setting up allowed functions defined in the model SandboxConfig,
        Also permits to rewrite __import__ with _custom_import,
            open with _custom_open and print with _custom_print
        """
        authorized_builtins = dict(builtins.__dict__)
        authorized_builtins["__import__"] = self._custom_import
        authorized_builtins["open"] = self._custom_open
        authorized_builtins["print"] = self._custom_print

        forbidden_builtins = ["eval", "exec", "input", "compile"]

        for builtin in forbidden_builtins:
            authorized_builtins.pop(builtin, None)

        self.namespace = {
            "__builtins__": authorized_builtins,
            "final_answer": self._final_answer_tool,
        }

    def execute(self, code):
        """
        This function securely execute the code build by the agent.
        Args:
            code: str = The code generated by the agent
        Returns:
            Dictionary: - Success: True is no error,
                            False if an exception is raised
                        - output: The standard output from the agent code
                        - error: None is no exception raised
                        - final_answer: The result from the agent code
                        - finished: False if not finished of errors, else True
        """
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(self.config.max_execution_time_seconds)

        self.stdout = []
        try:
            exec(code, self.namespace)
            return {
                "success": True,
                "output": "".join(self.stdout),
                "error": None,
                "final_answer": self.final_answer_value,
                "finished": self.has_finished
            }
        except Exception as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise e
            return {
                "success": False,
                "output": "".join(self.stdout),
                "error": f"{type(e).__name__}: {str(e)}",
                "final_answer": self.final_answer_value,
                "finished": False
            }
        finally:
            signal.alarm(0)


def main():
    sandbox = Sandbox()
    while True:
        try:
            command = input("Sanbox>")
            if command == "exit":
                break
            if not command.strip():
                continue

            result = sandbox.execute(command)
            if result["output"]:
                print(result["output"], end="")
            if result["error"]:
                print(f"Error: {result['error']}")
            if result["finished"]:
                print(f"Final Answer: {result['final_answer']}")
            print(result)
        except (KeyboardInterrupt, EOFError):
            print("\nExit the sandbox.")
            break


if __name__ == "__main__":
    main()

'''
if __name__ == "__main__":
    sandbox = Sandbox()
    print("=== Sandbox Tests ===\n")

    # TEST 1 : Calcul & stdout
    print("[Test 1] Calcul & print()")
    code_1 = """
a = 10
b = 20
print("result :", a + b)
"""
    res1 = sandbox.execute(code_1)
    print("Success  :", res1["success"])
    print("Output   :", repr(res1["output"]))
    assert res1["success"] is True
    assert res1["output"] == "result : 30\n"
    print("-> OK\n")

    # TEST 2 : Import (math + collections)
    print("[Test 2] Allowed Imports")
    code_2 = """
import math
from collections import Counter

c = Counter(["a", "b", "a"])
print("Sqrt :", math.sqrt(16))
print("Count:", c["a"])
"""
    res2 = sandbox.execute(code_2)
    print("Success  :", res2["success"])
    print("Output   :", repr(res2["output"]))
    assert res2["success"] is True
    print("-> OK\n")

    # TEST 3 : Forbidden Import (ex: os)
    print("[Test 3] Security : Forbidden Import (os)")
    code_3 = "import os"
    res3 = sandbox.execute(code_3)
    print("Success  :", res3["success"])
    print("Error    :", res3["error"])
    assert res3["success"] is False
    assert "SecurityError" in res3["error"]
    print("-> OK\n")

    # TEST 4 : Timeout exceeded
    print("[Test 4] Security : Execution Timeout")
    code_4 = """
while True:
    pass
"""
    res4 = sandbox.execute(code_4)
    print("Success  :", res4["success"])
    print("Error    :", res4["error"])
    assert res4["success"] is False
    assert "TimeoutError" in res4["error"]
    print("-> OK\n")

    # TEST 5 : final_answer()
    print("[Test 5] tool : final_answer()")
    code_5 = """
def solve():
    return "solution_code_mbpp"
final_answer(solve())
"""
    res5 = sandbox.execute(code_5)
    print("Finished     :", res5["finished"])
    print("Final Answer :", res5["final_answer"])
    assert res5["finished"] is True
    assert res5["final_answer"] == "solution_code_mbpp"
    print("-> OK\n")

    # TEST 6 : Inject extern tool with register_tool
    print("[Test 6] Injeciting externe tool (MCP simulation)")
    def mock_mcp_tool(filepath: str):
        return f"Simulating {filepath}"

    sandbox.register_tool("read_file", mock_mcp_tool)
    code_6 = """
res = read_file("test.py")
print(res)
"""
    res6 = sandbox.execute(code_6)
    print("Output :", repr(res6["output"]))
    assert "Simulating" in res6["output"]
    print("-> OK\n")

    print("=== ALL TEST PASSED ===")
'''


"""
# ===================== DOCUMENTATION FOR MY M8 ===================== #

To build a secure environment, the LLM’s Python code must be handled purely as raw text.

The sandbox then runs this code using exec(). By configuring the globals variable, we explicitly define which modules and built-in functions exec() is allowed to access.

Here, we implement a strict allowlist—blocking any module not explicitly granted access. We only include the bare minimum required for execution. Modules handling file systems, networking, or system access must be avoided at all costs to prevent the agent from breaking out of its sandbox.

Additionally, execution should be hard-capped—for instance, with a 5-second timeout—alongside strict CPU and resource limits.


# --------- How to disable built-in functions in a Python sandbox? --------- #

def sandboxed_execution(code):
    # Create a restricted environment
    sandbox_globals = {"__builtins__": {}}
    sandbox_locals = {}
    try:
        exec(code, sandbox_globals, sandbox_locals)
    except Exception as e:
        print("Error:", e)




# --------- How to restrict module imports in a Python sandbox? --------- #

def sandboxed_execution(code):
    # Create a restricted environment
    sandbox_globals = {}
    sandbox_locals = {}
    banned_modules = {"math", "random"}  # Add more as needed
    for module in banned_modules:
        sandbox_globals[module] = None
    try:
        exec(code, sandbox_globals, sandbox_locals)
    except Exception as e:
        print("Error:", e)




# --------- How to sandbox Python code with restricted filesystem access? --------- #

def restricted_open(*args, **kwargs):
    raise RuntimeError("Filesystem access is restricted")

def sandboxed_execution(code):
    # Create a restricted environment
    sandbox_globals = {"open": restricted_open}
    sandbox_locals = {}
    try:
        exec(code, sandbox_globals, sandbox_locals)
    except Exception as e:
        print("Error:", e)




# --------- How to implement a whitelist approach in a Python sandbox? --------- #

def sandboxed_execution(code):
    # Create a restricted environment
    sandbox_globals = {"safe_function": lambda x: x}
    sandbox_locals = {}
    try:
        exec(code, sandbox_globals, sandbox_locals)
    except Exception as e:
        print("Error:", e)




# --------- How to limit the resource usage in a Python sandbox? --------- #

import resource

def sandboxed_execution(code):
    # Set resource limits
    resource.setrlimit(resource.RLIMIT_CPU, (1, 1))  # 1 second CPU time limit
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 10, 1024 * 1024 * 10))  # 10 MB memory limit
    try:
        exec(code)
    except Exception as e:
        print("Error:", e)




# --------- How to limit execution time in Python sandbox? --------- #

import signal

def handler(signum, frame):
    raise TimeoutError("Execution timed out")

def sandboxed_execution(code):
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(5)  # 5 seconds time limit
    try:
        exec(code)
    except Exception as e:
        print("Error:", e)
    finally:
        signal.alarm(0)  # Cancel the alarm



"""
