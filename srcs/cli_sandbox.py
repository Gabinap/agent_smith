import sys
import argparse
from models.internal import McpSpec
from models.sandbox import SandboxConfig, SandboxResult
from sandbox.sandbox import Sandbox
from mcp_server.mcp_client import create_mcp_client, McpClient
from typing import Optional

class CLI_Sandbox:
    def __init__(self) -> None:
        self.args = self._sandbox_cli_parsing()
        if len(sys.argv) > 4:
            print("Error: Too many arguments passed", file=sys.stderr)
            return
        self.mcp_spec = self._get_mcp_spec(self.args)
        self.mcp_client: Optional[McpClient] = create_mcp_client(self.mcp_spec)
        self.sandbox = Sandbox(mcp_client=self.mcp_client, config=SandboxConfig())

    @staticmethod
    def _sandbox_cli_parsing() -> None:
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

    @staticmethod
    def _get_mcp_spec(args: argparse.Namespace) -> Optional[McpSpec]:
        if args.mcp_server:
            return McpSpec(transport="http", url=args.mcp_server)
        elif args.mcp_stdio:
            return McpSpec(transport="stdio", command=args.mcp_stdio)
        return None

    def execute(self) -> None:
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
