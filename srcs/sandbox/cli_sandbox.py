"""Interactive CLI for the sandbox REPL (uv run sandbox)."""

import argparse
import sys

from models.internal import McpSpec
from models.sandbox import SandboxConfig, SandboxResult
from pydantic import ValidationError

from sandbox.mcp_client import McpClient, create_mcp_client
from sandbox.sandbox import Sandbox

import os
import select
import codeop

class CLI_Sandbox:
    """Parse CLI args and drive an interactive Sandbox REPL."""

    def __init__(self) -> None:
        """Parse CLI args and build the sandbox from them."""
        self.args = self._sandbox_cli_parsing()
        if len(sys.argv) > 4:
            print("Error: Too many arguments passed", file=sys.stderr)
            return
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
            # A server that will not start is no reason to lose the REPL
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
        with (open(path, "r") as file):
            json = file.read()
            return SandboxConfig.model_validate_json(json)

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
        elif args.mcp_stdio:
            return McpSpec(transport="stdio", command=args.mcp_stdio)
        return None

    @staticmethod
    def _is_complete(source: str) -> bool:
        """True if source is a complete statement, like Python's REPL."""
        try:
            return codeop.compile_command(source, "<sandbox>", "single") is not None
        except (SyntaxError, ValueError, OverflowError):
            return True  # invalid: let the sandbox report the real error

    def _run(self, source: str) -> None:
        result: SandboxResult = self.sandbox.execute(source)
        if result.output:
            print(f"\n{result.output}", end="")
        if result.error:
            print(f"Error: {result.error}")
        if result.finished:
            print(f"Final Answer: {result.final_answer}")
        if not (result.output or result.error or result.finished):
            print("(no output)")

    def _drain_pasted(self) -> str:
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
        print("Available tools:")
        print(self.sandbox.manual())
        print("Type 'manual' to print this again, 'exit' to leave.\n")
        buffer: list[str] = []
        try:
            while True:
                try:
                    line = input("" if buffer else
                                 "Sandbox>").replace("\xa0", " ")
                    pasted = self._drain_pasted()
                    if pasted or "\n" in line:
                        source = "\n".join(buffer + [line]) + ("\n" + pasted if pasted else "")
                        buffer.clear()
                        self._run(source.rstrip("\n") + "\n")
                        continue
                except EOFError:
                    if buffer:                      # flush the last block
                        self._run("\n".join(buffer))
                    print("\nExit the sandbox.")
                    break
                except KeyboardInterrupt:
                    print("\nExit the sandbox.")
                    break

                if not buffer:                      # only at a fresh prompt
                    if line.strip() == "manual":
                        print(self.sandbox.manual())
                        continue
                    if line.strip() == "exit":
                        break
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue

                buffer.append(line)
                source = "\n".join(buffer)
                if not self._is_complete(source):
                    continue                        # wait for more lines
                buffer.clear()
                self._run(f"{source}")
        finally:
            if self.mcp_client:
                self.mcp_client.close()

def main() -> None:
    manual_sandbox = CLI_Sandbox()
    manual_sandbox.execute()


if __name__ == "__main__":
    main()
