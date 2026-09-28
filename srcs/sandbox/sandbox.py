from builtins import __build_class__
from collections.abc import Callable
from multiprocessing.connection import Connection
from types import FrameType
from typing import IO, Any

from models.sandbox import SandboxConfig, SandboxResult

from sandbox.mcp_client import McpClient


class SecurityError(PermissionError):
    """Security Rules are not respected"""


class TimeoutError(Exception):
    """Execution time limit exceeded"""


def _timeout_handler(signum: int, frame: FrameType | None) -> None:
    raise TimeoutError("Execution timed out")


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_OPEN_FILES = 256
CPU_GRACE_SECONDS = 5
TIMEOUT_REPORT_GRACE_SECONDS = 1


# Attributes that walk from any object back to the process (its classes,
# the real builtins, a frame's globals). Blocked as a denylist so plain
# dunders like __init__ or __str__ stay usable: x.__init__ passes,
# x.__init__.__globals__ is stopped on the second hop.
DENIED_ATTRS = frozenset({
    # object-graph traversal
    "__globals__", "__class__", "__bases__", "__base__", "__subclasses__",
    "__mro__", "__code__", "__closure__", "__func__", "__self__", "__dict__",
    "__builtins__", "__getattribute__", "__reduce__", "__reduce_ex__",
    "__loader__", "__spec__", "__import__", "__traceback__",
    "__thisclass__", "__self_class__",  # what super() proxies point to
    # frame / generator / coroutine internals (not dunders, hence listed)
    "gi_frame", "gi_code", "cr_frame", "ag_frame",
    "f_globals", "f_builtins", "f_locals", "f_back",
    "tb_frame", "tb_next",
})

# Names that grant execution or attribute access by string, plus the
# DENIED_ATTRS that are also usable bare (`__builtins__`, `__import__`,
# `__class__`). __name__ is deliberately absent: class bodies read it.
DENIED_NAMES = frozenset({
    "eval", "exec", "compile", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint",
}) | DENIED_ATTRS


def _reject_escapes(code: str) -> Any:
    """Parse `code` and refuse the syntax that escapes the namespace."""
    import ast

    def deny(name: str, node: Any) -> None:
        raise SecurityError(
            f"'{name}' is forbidden by sandbox policy "
            f"(line {getattr(node, 'lineno', '?')})")

    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in DENIED_ATTRS:
            deny(node.attr, node)
        elif isinstance(node, ast.Name) and node.id in DENIED_NAMES:
            deny(node.id, node)
        elif (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("format", "format_map")
                and isinstance(node.func.value, ast.Constant)
                and isinstance(node.func.value.value, str)):
            for attr in DENIED_ATTRS:
                if attr in node.func.value.value:
                    deny(attr, node)
    return tree


SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "range": range, "set": set, "str": str, "sum": sum, "tuple": tuple,
    "zip": zip, "True": True, "False": False, "None": None, "type": type,
    "SystemExit": SystemExit, "KeyboardInterrupt": KeyboardInterrupt,
    "__build_class__": __build_class__, "super": super,
    "sorted": sorted, "reversed": reversed, "isinstance": isinstance,
    "issubclass": issubclass, "round": round, "divmod": divmod,
    "pow": pow, "ord": ord, "chr": chr, "bin": bin, "hex": hex,
    "repr": repr, "hash": hash, "iter": iter, "next": next,
    "slice": slice, "frozenset": frozenset, "format": format,
    "Exception": Exception, "ValueError": ValueError,
    "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "ZeroDivisionError": ZeroDivisionError,
    "AttributeError": AttributeError, "StopIteration": StopIteration,
    "RuntimeError": RuntimeError, "AssertionError": AssertionError,
    "ImportError": ImportError,
    "ModuleNotFoundError": ModuleNotFoundError,
    "FileNotFoundError": FileNotFoundError,
    "PermissionError": PermissionError,
    "OSError": OSError,
    "dir": dir
}


class Sandbox:
    def __init__(
            self,
            mcp_client: McpClient | None = None,
            config: SandboxConfig | None = None,
            ) -> None:
        """
        Sandbox to execute code that can be vulnerable
        """
        self.config = config if config is not None else SandboxConfig()
        self.mcp_client = mcp_client
        self._tool_conn: Connection | None = None
        self.namespace: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []
        self.final_answer_value: Any | None = None
        self.has_finished = False

        self.stdout: list[Any] = []

        self._setup_namespace()
        if self.mcp_client:
            self._bind_mcp_tools()
        self._base_keys = set(self.namespace)
        self._persist_src: list[str] = []

    def _export_state(self) -> dict[str, Any]:
        """Variables créées par le code utilisateur et transmissibles."""
        import pickle
        state: dict[str, Any] = {}
        for key, value in self.namespace.items():
            if key in self._base_keys:
                continue
            try:
                pickle.dumps(value)
            except Exception:
                continue
            state[key] = value
        return state

    def _remember(self, code: str) -> None:
        """Retient les définitions top-level pour les rejouer ensuite."""
        import ast
        for node in ast.parse(code).body:
            if isinstance(node, (ast.Import, ast.ImportFrom,
                                 ast.FunctionDef, ast.ClassDef)):
                segment = ast.get_source_segment(code, node)
                if segment:
                    self._persist_src.append(segment)

    def _is_import_allowed(self, name: str) -> bool:
        """
        Check if a module can be imported
        Args:
            name: str = module name
        Returns:
            bool: True if the module import is allowed, False otherwise
        """
        for pattern in self.config.authorized_imports:
            if pattern.endswith(".*"):
                pkg = pattern[:-2]
                if name == pkg or name.startswith(f"{pkg}."):
                    return True
            else:
                if name == pattern:
                    return True
        return False

    def _custom_import(
            self,
            name: str,
            globals: dict[str, Any] | None = None,
            locals: dict[str, Any] | None = None,
            fromlist: Any = (),
            level: int = 0
            ) -> Any:
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
        from builtins import __import__ as real_import

        if not self._is_import_allowed(name):
            raise SecurityError("Import forbidden by sandbox"
                                f" policy: '{name}'")
        return real_import(name, globals, locals, fromlist, level)

    def _is_open_allowed(self, filepath: str) -> bool:
        """
        Check if a file can be open
        Args:
            filepath: str = file path
        Returns:
            bool: True if opening this file is allowed, False otherwise
        """
        from os import sep
        from os.path import realpath

        for allowed_dir in self.config.allowed_directories:
            real_allowed = realpath(allowed_dir)
            if filepath == real_allowed or filepath.startswith(
                    real_allowed + sep):
                return True
        return False

    def _custom_open(
            self,
            file: Any,
            mode: str = "r",
            *args: Any,
            **kwargs: Any
            ) -> IO[Any]:
        """
        Rewriting the open function to restrict open usage
        Args:
            file: str = file path
            mode: str = The type of action we have to do in the file
            args: other arguments that can be needed by open
            kwargs: other arguments that can be needed by open
        Returns:
            IO: Opened file stream
        """
        from builtins import open as real_open
        from os.path import realpath

        filepath = realpath(str(file))
        if not self._is_open_allowed(filepath):
            raise SecurityError(
                f"Access denied to file path '{filepath}'."
                f" Allowed directories: {self.config.allowed_directories}"
            )
        return real_open(file, mode, *args, **kwargs)

    def _custom_print(self, *args: Any, **kwargs: Any) -> None:
        """Capture what the code prints instead of writing it out.

        Faithfully: shortening belongs to the agent, which decides
        what goes into the conversation. Rewriting here corrupted
        every print — a leading "+" was stripped as if it were a diff
        marker, and `final_answer` would have carried the damage.
        """
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")

        text = sep.join(str(a) for a in args) + end
        self.stdout.append(text)

    def _final_answer_tool(self, answer: str) -> str:
        """
        The implementation of the function final_answer function,
        that the LLM can use to signal that this is the print to return
        Args:
            answer: Any = the answer from the agent
        Returns: Any = the answer from the agent
        """
        answer = str(answer)
        self.final_answer_value = answer
        self.has_finished = True
        return answer

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """
        Inject new functions tools to the white list
        Args:
            name: str = The name that the agent as to call
            func: Callable = The code that as to be done
                when the agent call the named function
        """
        self.namespace[name] = func

    def _setup_namespace(self) -> None:
        """
        Setting up allowed functions defined in the model SandboxConfig,
        Also permits to rewrite __import__ with _custom_import,
            open with _custom_open and print with _custom_print
        """
        authorized_builtins = SAFE_BUILTINS.copy()
        authorized_builtins["__import__"] = self._custom_import
        authorized_builtins["open"] = self._custom_open
        authorized_builtins["print"] = self._custom_print

        self.namespace = {
            "__builtins__": authorized_builtins,
            "__name__": "__main__",
            "final_answer": self._final_answer_tool,
        }

    def _bind_mcp_tools(self) -> None:
        """Report MCP functions directly as usable for the agent."""
        if not self.mcp_client:
            return

        tools_res = self.mcp_client.initialize_session()
        tools = tools_res.get("result", {}).get("tools", [])
        self.tools = tools

        def create_wrapper(tool_name: str) -> Callable[..., Any]:
            def tool_wrapper(**kwargs: Any) -> Any:
                if self._tool_conn is None:
                    return self._call_tool(tool_name, kwargs)
                return self._call_tool_through_parent(tool_name, kwargs)
            return tool_wrapper

        for tool in tools:
            t_name = tool["name"]
            self.namespace[t_name] = create_wrapper(t_name)

    def _call_tool(self, name: str, args: dict[str, Any]) -> str:
        """Call an MCP tool from this process and return its text."""
        if self.mcp_client is None:
            return ""
        res = self.mcp_client.call_tool(name, args)
        result = res.get("result", {}) if res else {}
        content = result.get("content", [])
        return str(content[0].get("text", "")) if content else ""

    def _call_tool_through_parent(self, name: str,
                                  args: dict[str, Any]) -> str:
        """Have the parent make the MCP call, from inside the child.

        MCP tools act outside the sandbox: the child has no network, so a
        call made from here worked only while the connection opened
        before the fork stayed alive, and an HTTP server drops an idle one
        after a few seconds. The sandbox timeout is paused meanwhile —
        a tool's own run time is not the sandboxed code's.
        """
        import signal
        assert self._tool_conn is not None
        paused = signal.alarm(0)
        try:
            self._tool_conn.send({"__tool__": name, "args": args})
            reply: dict[str, Any] = self._tool_conn.recv()
        finally:
            if paused:
                signal.alarm(paused)
        if "error" in reply:
            raise RuntimeError(reply["error"])
        return str(reply["result"])

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the discovered MCP tool specs, or [] if none."""
        return self.tools

    def manual(self) -> str:
        """Document the tools this sandbox exposes, from their schemas.

        Built at call time from the connected server's `tools/list`
        reply, so pointing the sandbox at another server yields another
        manual with no code change. `final_answer` is listed alongside
        them: it is a sandbox feature, not an MCP tool.
        """
        lines = []
        for tool in self.tools:
            params = ", ".join(
                f"{name}: {spec.get('type', 'str')}"
                for name, spec in tool.get("inputSchema", {})
                .get("properties", {}).items()
            )
            lines.append(
                f"- {tool.get('name', '')}({params}): "
                f"{tool.get('description', '')}"
            )
        lines.append(
            "- final_answer(answer): Submit the final answer and stop")
        return "\n".join(lines)

    @staticmethod
    def _setrlimit(name: str, value: int) -> None:
        """Apply one kernel limit, as both the soft and the hard one.

        Equal soft and hard values make the limit a one-way door: a
        process may lower its limits, never raise the hard one back.
        Platforms missing the limit, and hard limits already stricter
        than ours, are left alone.
        """
        import resource

        kind = getattr(resource, name, None)
        if kind is None:
            return
        try:
            resource.setrlimit(kind, (value, value))
        except (ValueError, OSError):
            pass

    def _limit_resource(self) -> None:
        """Cap what the sandboxed process may consume, kernel-side.

        Called after the fork, so only the child is bound and the agent
        keeps its own limits. These caps do not prevent an escape from
        the namespace; they bound the damage one could do.
        """
        # Virtual address space: a bigger allocation fails as MemoryError.
        self._setrlimit(
            "RLIMIT_AS", self.config.max_memory_mb * 1024 * 1024)
        # No fork: os.system() and subprocess cannot spawn a shell, which
        # is what _block_network() alone cannot cover (a child process
        # would carry its own, unpatched network stack).
        self._setrlimit("RLIMIT_NPROC", 0)
        # Cap what a single file may grow to, and how many stay open.
        self._setrlimit("RLIMIT_FSIZE", MAX_FILE_SIZE_BYTES)
        self._setrlimit("RLIMIT_NOFILE", MAX_OPEN_FILES)
        # No multi-gigabyte core dump when the child is killed.
        self._setrlimit("RLIMIT_CORE", 0)
        # Deliberately above the wall-clock timeout: execute() should be
        # the one reporting a timeout, this is only the backstop for
        # when the parent itself is stuck.
        self._setrlimit(
            "RLIMIT_CPU",
            self.config.max_execution_time_seconds + CPU_GRACE_SECONDS)

    def _block_network(self) -> None:
        """Blocking the network access to the child process"""
        import socket

        def dummy_socket(*args: Any, **kwargs: Any) -> None:
            raise SecurityError("Network access is blocked by sandbox policy")
        socket.socket = dummy_socket  # type: ignore
        socket.create_connection = dummy_socket  # type: ignore

    def _worker(self, code: str, conn: Connection) -> None:
        """
        Thread specialy made for the code execution to controll the RAM
            and time and only stop this thread if a limit is reached
            and not all the running code
        Args:
            code: str = The code that the sandbox has to run securly
            conn : mp.connection.Connection = The conneciton between the child
                and the parent
        """
        import signal

        try:
            self._limit_resource()
            self._block_network()
            self._tool_conn = conn

            tree = _reject_escapes(code)
            compiled_code = compile(tree, filename="<sandbox>", mode="exec")
            for src in self._persist_src:
                exec(compile(src, "<sandbox>", "exec"), self.namespace)
            signal.signal(signal.SIGALRM, _timeout_handler)
            try:
                exec(compiled_code, self.namespace)
            finally:
                signal.alarm(0)

            conn.send({
                "success": True,
                "output": "".join(self.stdout),
                "error": None,
                "final_answer": self.final_answer_value,
                "finished": self.has_finished,
                "state": self._export_state()
            })
        except SystemExit as e:
            conn.send({"__control__": "SystemExit", "code": e.code})
        except KeyboardInterrupt:
            conn.send({"__control__": "KeyboardInterrupt"})
        except SyntaxError as e:
            conn.send({
                "success": False,
                "output": "".join(self.stdout),
                "error": (f"SyntaxError: {e.msg} (line {e.lineno}, "
                          f"col {e.offset})"),
                "final_answer": self.final_answer_value,
                "finished": False,
            })
        except SecurityError as e:
            conn.send({
                "success": False,
                "output": "".join(self.stdout),
                "error": f"SecurityError: {e!s}",
                "final_answer": self.final_answer_value,
                "finished": False,
            })
        except MemoryError:
            conn.send({
                "success": False,
                "output": "".join(self.stdout),
                "error": (
                    "MemoryError: RAM limit exceeded ("
                    f"{self.config.max_memory_mb} MB limit)"
                ),
                "final_answer": self.final_answer_value,
                "finished": False,
            })
        except TimeoutError:
            conn.send({
                "success": False,
                "output": "".join(self.stdout),
                "error": (
                    "TimeoutError: Execution time limit exceeded ("
                    f"{self.config.max_execution_time_seconds}s limit)"
                ),
                "final_answer": self.final_answer_value,
                "finished": False,
            })
        except Exception as e:
            conn.send({
                "success": False,
                "output": "".join(self.stdout),
                "error": f"{type(e).__name__}: {e!s}",
                "final_answer": self.final_answer_value,
                "finished": False,
            })

    def execute(self, code: str) -> SandboxResult:
        """
        The main function to run untrusted code in the secure sandbox.
        Args:
            code : str = The code to run
        Return Value:
            SandboxResult = The return of the executed code in the
                SandboxResult class
        """
        from multiprocessing import Pipe, Process, ProcessError

        parent_conn, child_conn = Pipe()
        process = Process(target=self._worker, args=(code, child_conn))
        process.daemon = True
        try:
            process.start()
        except (ProcessError, TypeError) as e:
            return SandboxResult.model_validate({
                "success": False,
                "output": "",
                "error": (
                    "ProcessCreationFailed: Failed to spawn sandbox "
                    f"worker process: {e!s}"
                ),
                "final_answer": None,
                "finished": False
            })

        child_conn.close()

        import time
        deadline = time.monotonic() + (self.config.max_execution_time_seconds
                                       + TIMEOUT_REPORT_GRACE_SECONDS)
        res_dict = None
        while parent_conn.poll(timeout=max(deadline - time.monotonic(), 0)):
            try:
                # recv() drains the whole message however large, which
                # unblocks the child's send()
                message = parent_conn.recv()
            except EOFError:
                break
            if "__tool__" not in message:
                res_dict = message
                break
            started = time.monotonic()
            try:
                reply = {"result": self._call_tool(message["__tool__"],
                                                   message["args"])}
            except Exception as e:
                reply = {"error": f"{type(e).__name__}: {e!s}"}
            parent_conn.send(reply)
            deadline += time.monotonic() - started

        if res_dict is not None:
            process.join(timeout=TIMEOUT_REPORT_GRACE_SECONDS)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            control = res_dict.get("__control__")
            if control == "SystemExit":
                raise SystemExit(res_dict.get("code"))
            if control == "KeyboardInterrupt":
                raise KeyboardInterrupt()
            state = res_dict.pop("state", None)     # avant model_validate
            result = SandboxResult.model_validate(res_dict)
            if result.success:
                if state:
                    self.namespace.update(state)
                self._remember(code)
            return result

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
            return SandboxResult.model_validate({
                "success": False,
                "output": "",
                "error": (
                    "TimeoutError: Execution time limit exceeded ("
                    f"{self.config.max_execution_time_seconds}s limit)"
                ),
                "final_answer": None,
                "finished": False
            })

        exit_code = process.exitcode
        error_msg = (
            "ProcessCrashed: Process terminated abruptly with exit "
            f"code {exit_code}."
        )
        if exit_code == -9:
            error_msg += (
                " (Likely killed by OS OOM killer for exceeding "
                f"memory limit of {self.config.max_memory_mb} MB)"
            )

        return SandboxResult.model_validate({
            "success": False,
            "output": "",
            "error": error_msg,
            "final_answer": None,
            "finished": False
        })
