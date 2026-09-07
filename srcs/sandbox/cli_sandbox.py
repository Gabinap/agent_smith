"""Interactive CLI for the sandbox REPL (uv run sandbox)."""

import argparse
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
            return
        self.mcp_spec = self._get_mcp_spec(self.args)
        self._get_sandbox_config(self.args)
        self.mcp_client: McpClient | None = create_mcp_client(self.mcp_spec)
        self.sandbox = Sandbox(
            mcp_client=self.mcp_client,
            config=self.config
            )

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

    def execute(self) -> None:
        """Run the read-eval-print loop until 'exit' or EOF/Ctrl-C."""
        try:
            while True:
                try:
                    command = input("Sanbox>")
                    if command == "exit":
                        break
                    if not command.strip():
                        continue

                    result: SandboxResult = self.sandbox.execute(command)
                    if result.output:
                        print(result.output, end="")
                    if result.error:
                        print(f"Error: {result.error}")
                    if result.finished:
                        print(f"Final Answer: {result.final_answer}")
                    print(result)
                except (KeyboardInterrupt, EOFError):
                    print("\nExit the sandbox.")
                    break
        finally:
            if self.mcp_client:
                self.mcp_client.close()


if __name__ == "__main__":
    manual_sandbox = CLI_Sandbox()
    manual_sandbox.execute()
