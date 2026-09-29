"""Interactive CLI for the sandbox REPL (uv run sandbox)."""

import argparse
import codeop
import os
import select
import sys

from models.internal import McpSpec
from models.sandbox import SandboxConfig, SandboxResult
from pydantic import ValidationError

from sandbox.mcp_client import McpClient, create_mcp_client
from sandbox.sandbox import Sandbox


class CLI_Sandbox:
    """Parse CLI args and drive an interactive Sandbox REPL."""

    def __init__(self) -> None:
        """Parse CLI args and build the sandbox from them."""
        self.args = self._sandbox_cli_parsing()
        if len(sys.argv) > 4:
            print("Error: Too many arguments passed", file=sys.stderr)
            sys.exit(1)

        self.mcp_spec = self._get_mcp_spec(self.args)
        self._get_sandbox_config(self.args)
        self.mcp_client: McpClient | None = None
        try:
            self.mcp_client = create_mcp_client(self.mcp_spec)
            self.sandbox = Sandbox(
                mcp_client=self.mcp_client,
                config=self.config
            )
        except (RuntimeError, OSError) as error:
            print(f"Warning: MCP server unavailable ({error}). "
                  "Continuing without tools.", file=sys.stderr)
            self.mcp_client = None
            self.sandbox = Sandbox(mcp_client=None, config=self.config)

    @staticmethod
    def _sandbox_cli_parsing() -> argparse.Namespace:
        """Parse --mcp-stdio/--mcp-server and the config file argument."""
        parser = argparse.ArgumentParser(prog="SandboxCLI")
        mcp_group = parser.add_mutually_exclusive_group()
        mcp_group.add_argument(
            "--mcp-stdio",
            type=str,
            help="Command to run MCP server via stdio"
        )
        mcp_group.add_argument(
            "--mcp-server",
            type=str,
            help="URL of MCP server via HTTP"
        )
        parser.add_argument(
            "config_file",
            nargs="?",
            help="Path to the JSON configuration file"
        )
        return parser.parse_args()

    @staticmethod
    def _read_config(config_file: str) -> SandboxConfig:
        """Read a SandboxConfig from a JSON file."""
        from pathlib import Path
        path = Path(config_file)
        with open(path, "r", encoding="utf-8") as file:
            json_str = file.read()
            return SandboxConfig.model_validate_json(json_str)

    def _get_sandbox_config(self, args: argparse.Namespace) -> None:
        """Load the sandbox config from a file, or use the defaults."""
        if args.config_file:
            try:
                self.config = self._read_config(self.args.config_file)
            except FileNotFoundError:
                print("Error: Config File not found, entering the "
                      "Sandbox with default configuration", file=sys.stderr)
                self.config = SandboxConfig()
            except ValidationError:
                print("Error: Bad formatted configuration file, entering the "
                      "Sandbox with default configuration", file=sys.stderr)
                self.config = SandboxConfig()
        else:
            self.config = SandboxConfig()

    @staticmethod
    def _get_mcp_spec(args: argparse.Namespace) -> McpSpec | None:
        """Build the McpSpec from --mcp-stdio/--mcp-server, or None."""
        if args.mcp_server:
            return McpSpec(transport="http", url=args.mcp_server)
        if args.mcp_stdio:
            return McpSpec(transport="stdio", command=args.mcp_stdio)
        return None

    @staticmethod
    def _is_complete(source: str) -> bool:
        """True if source is a complete statement, like Python's REPL."""
        try:
            return codeop.compile_command(
                source, "", "single"
            ) is not None
        except (SyntaxError, ValueError, OverflowError):
            return True

    def _run(self, source: str) -> None:
        """Execute a block of source code in the sandbox and print output."""
        result: SandboxResult = self.sandbox.execute(source)
        if result.output:
            print(result.output, end="")
        if result.error:
            print(f"Error: {result.error}")
        if result.finished:
            print(f"Final Answer: {result.final_answer}")
        if not (result.output or result.error or result.finished):
            print("(no output)")

    @staticmethod
    def _drain_pasted() -> str:
        """Return the lines already waiting on stdin (a paste), else ''."""
        if not sys.stdin.isatty():
            return ""
        fd = sys.stdin.fileno()
        chunks: list[bytes] = []
        while select.select([fd], [], [], 0.05)[0]:
            data = os.read(fd, 65536)
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode(errors="replace")

    def execute(self) -> None:
        """Run execution loop or process redirected stdin completely."""
        # for command like cat, pipe, etc
        if not sys.stdin.isatty():
            code = sys.stdin.read()
            if code.strip():
                self._run(code)
            return

        # interactive REPL
        tools_manual = self.sandbox.manual()
        if tools_manual:
            print("Available tools:")
            print(tools_manual)
            print()

        buffer: list[str] = []
        while True:
            try:
                prompt = "Sandbox> " if not buffer else "........"
                line = input(prompt)

                if not buffer and line.strip() == "exit":
                    break
                if not buffer and line.strip() == "manual":
                    print(self.sandbox.manual())
                    continue

                buffer.append(line)

                # Complet the buffer if pasted text
                pasted = self._drain_pasted()
                if pasted:
                    buffer.extend(pasted.splitlines())

                code_block = "\n".join(buffer)

                # verify if the code is complete
                if self._is_complete(code_block):
                    self._run(code_block)
                    buffer = []

            except (EOFError, KeyboardInterrupt):
                print()
                break


def main() -> None:
    cli = CLI_Sandbox()
    cli.execute()


if __name__ == "__main__":
    main()
