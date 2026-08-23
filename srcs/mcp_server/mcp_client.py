import json
import shlex
import subprocess
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from models.internal import McpSpec


class TransportMode(Enum):
    STDIO = "stdio"
    HTTP = "http"


class McpClient(ABC):
    def __init__(self, transport: TransportMode) -> None:
        self.transport: TransportMode = transport
        self._next_id: int = 1

    def initialize_session(self) -> Dict[str, Any]:
        init_request = self._build_request(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "AgentSmithSandbox",
                    "version": "1.0.0"
                },
            },
        )
        init_response = self.send_message(init_request)
        print(f"Init response: {init_response}\n")  # delete debug print

        notif = self._build_notification(method="notifications/initialized")
        self.send_message(notif)
        print("Notification send (no response needed)\n")  # delete debug print

        server_request = self._build_request("tools/list")
        server_response = self.send_message(server_request)
        print(f"Server response: {server_response}\n")  # delete debug print

        return server_response if server_response else {}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]
                  ) -> Optional[Dict[str, Any]]:
        """Call an MCP tools."""
        req = self._build_request(
            "tools/call",
            params={"name": tool_name, "arguments": arguments}
        )
        return self.send_message(req)

    def _build_request(
            self,
            method: str,
            params: Optional[Dict[str, Any]] = None
            ) -> Dict[str, Any]:
        """Build JSON-RPC 2.0 request with ID incrementation."""
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
        }
        if params is not None:
            req["params"] = params
        self._next_id += 1
        return req

    @staticmethod
    def _build_notification(
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build notification JSON-RPC 2.0 (no ID)"""
        notif: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notif["params"] = params
        return notif

    @abstractmethod
    def send_message(
        self,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send a message to the server and return response."""
        pass

    @abstractmethod
    def connect(self) -> None:
        """Starting the process to connection to the server"""
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class McpHttp(McpClient):
    def __init__(self, url: str) -> None:
        super().__init__(TransportMode.HTTP)
        self.url = url

    def send_message(
        self,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        # TODO: not implemented yet — HTTP transport is not usable.
        pass

    def connect(self) -> None:
        # TODO: not implemented yet — HTTP transport is not usable.
        pass

    def close(self) -> None:
        # TODO: not implemented yet — HTTP transport is not usable.
        pass


class McpStdio(McpClient):
    def __init__(self, command: str) -> None:
        """
        MCP stdio client
        Args:
            command: str = the command to execute on the server
        Return:
            None
        """
        super().__init__(TransportMode.STDIO)
        self.command: str = command
        self.connect()

    def send_message(
        self,
        message: Dict[str, Any]
    ) -> Any | None:
        """Send a message to the server and return response."""
        if (not self.process or
            self.process.stdin is None or
                not self.process.stdout):
            raise RuntimeError("Not connected to Stdio process")

        payload = json.dumps(message) + "\n"
        self.process.stdin.write(payload)
        self.process.stdin.flush()

        if "id" in message:
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("Server closed connection unexpectedly")
            return json.loads(response_line)
        return None

    def connect(self) -> None:
        """Starting the process to connection to the server"""
        self.process = subprocess.Popen(
            shlex.split(self.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def close(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait()

def create_mcp_client(spec: Optional[McpSpec]) -> Optional[McpClient]:
    """Choosing the right client with McpSpec"""
    if not spec:
        return None

    if spec.transport == "stdio":
        if not spec.command:
            raise ValueError("A command is required for the stdio Client.")
        return McpStdio(command=spec.command)

    if spec.transport == "http":
        if not spec.url:
            raise ValueError("An url is required for the http client.")
        return McpHttp(url=spec.url)

    raise ValueError(f"Unknown transport method: {spec.transport}")
# ================ ============ ================ #
# ================ ============ ================ #
# ================ SERVEUR MOCK ================ #
# ================ ============ ================ #
# ================ ============ ================ #

'''
def run_mock_server():
    for line in sys.stdin:
        if not line.strip():
            continue

        request = json.loads(line)
        method = request.get("method")
        msg_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "MockMBPPServer",
                        "version": "1.0.0"
                    }
                }
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "run_tests",
                            "description": "Run the test for the MBPP",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"code": {"type": "string"}},
                                "required": ["code"]
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        run_mock_server()
        return

    try:
        print("=== START MCP CLIENT TEST (STDIO) ===\n")
        client = McpStdio(command=f"python3 {__file__} --server")
        tools_response = client.initialize_session()
        print("=========== PERFECT BBY ===========")
        print("tools_response =", tools_response)
    finally:
        client.close()


if __name__ == "__main__":
    main()
'''
