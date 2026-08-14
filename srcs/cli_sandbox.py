import sys
import argparse
from pydantic import ValidationError
from models.internal import McpSpec
from models.sandbox import SandboxConfig, SandboxResult
from sandbox.sandbox import Sandbox


class CLI_Sandbox:
    def __init__(self) -> None:
        self._sandbox_cli_parsing()
        if len(sys.argv) > 4:
            print("Error: Too many arguments passed", file=sys.stderr)
            return
        self._get_mcp_spec(self.args)
        self._get_sandbox_config(self.args)
        self.sandbox = Sandbox(config=self.config)

    def _sandbox_cli_parsing(self) -> None:
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
        self.args = parser.parse_args()

    @staticmethod
    def _read_config(config_file: str) -> SandboxConfig:
        """Read the Json config file
        Args:
            config_file (str): config json file
        Returns:
            SandboxConfig: SandboxConfig input modele
        """
        from pathlib import Path
        path = Path(config_file)
        with (open(path, "r") as file):
            json = file.read()
            return SandboxConfig.model_validate_json(json)

    def _get_sandbox_config(self, args: argparse.Namespace) -> None:
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

    def _get_mcp_spec(self, args: argparse.Namespace) -> None:
        if args.mcp_server:
            self.mcp_spec = McpSpec(transport="http", url=args.mcp_server)
            print(self.mcp_spec)
        elif args.mcp_stdio:
            self.mcp_spec = McpSpec(transport="stdio", command=args.mcp_stdio)
            print(self.mcp_spec)
        else:
            self.mcp_spec = None

    def execute(self) -> None:
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


if __name__ == "__main__":
    manual_sandbox = CLI_Sandbox()
    manual_sandbox.execute()
