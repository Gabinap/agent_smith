import json
import shlex
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import httpx
from models.internal import McpSpec


class TransportMode(Enum):
    STDIO = "stdio"
    HTTP = "http"


class McpClient(ABC):
    def __init__(self, transport: TransportMode) -> None:
        self.transport: TransportMode = transport
        self._next_id: int = 1

    def initialize_session(self) -> dict[str, Any]:
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

    def call_tool(self, tool_name: str, arguments: dict[str, Any]
                  ) -> dict[str, Any] | None:
        """Call an MCP tools."""
        req = self._build_request(
            "tools/call",
            params={"name": tool_name, "arguments": arguments}
        )
        return self.send_message(req)

    def _build_request(
            self,
            method: str,
            params: dict[str, Any] | None = None
            ) -> dict[str, Any]:
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
        params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build notification JSON-RPC 2.0 (no ID)"""
        notif: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notif["params"] = params
        return notif

    @abstractmethod
    def send_message(
        self,
        message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Send a message to the server and return response."""

    @abstractmethod
    def connect(self) -> None:
        """Starting the process to connection to the server"""

    @abstractmethod
    def close(self) -> None:
        pass


class McpHttp(McpClient):
    def __init__(self, url: str) -> None:
        super().__init__(TransportMode.HTTP)
        self.endpoint_url: str = url.rstrip("/")
        if not self.endpoint_url.endswith("/mcp"):
            self.endpoint_url += "/mcp"

        self.session_id: str | None = None
        self._http_client: httpx.Client | None = None

    def send_message(self, message: dict[str, Any]) -> Any | None:
        if not self._http_client:
            raise RuntimeError("HTTP Client not connected. "
                               "Call connect() first.")

        headers = {"Content-Type": "application/json"}

        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        response = self._http_client.post(
            self.endpoint_url,
            json=message,
            headers=headers,
        )
        response.raise_for_status()

        if not self.session_id and "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]
            print(f"[INFO] MCP Session established with ID: {self.session_id}")

        if "id" in message:
            text = response.text.strip()

            if "data: " in text:
                for line in text.splitlines():
                    if line.startswith("data: "):
                        raw_json = line[6:].strip()
                        data = json.loads(raw_json)
                        print("response: '", data, "'")
                        return data

            data = response.json()
            print("response: '", data, "'")
            return data

        return None

    def connect(self) -> None:
        self._http_client = httpx.Client(timeout=30.0)
        print(f"[INFO] Client ready for endpoint: {self.endpoint_url}")

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()


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
        message: dict[str, Any]
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


def create_mcp_client(spec: McpSpec | None) -> McpClient | None:
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


# =====================================================================
# HTTP TEST of use example
# =====================================================================
'''def main() -> None:
    target_url = "http://127.0.0.1:8000"
    print(f"=== Testing McpHttp on {target_url} ===")

    client = McpHttp(url=target_url)

    try:
        # Step 1: Establish HTTP Connection
        print("\n1. Connecting...")
        client.connect()

        # Step 2: Initialize MCP Session via JSON-RPC
        print("\n2. Sending 'initialize' message...")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        init_res = client.send_message(init_message)
        print(f"   Initialize response: {init_res}")

        # Send initialization confirmation notification
        # (no 'id', no response expected)
        client.send_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

        # Step 3: List Available Tools
        print("\n===================== Raw 'tools/list' =====================")
        list_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        tools_res = client.send_message(list_message)

        tools = tools_res.get(
            "result", {}).get("tools", []) if tools_res else []
        print(f"\n============ {len(tools)} tool(s) formatted ============")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description')}")

        # Step 4: Call a Tool via 'tools/call'
        print("\n4. Sending 'tools/call' message...")
        target_tool = next(
            (t["name"] for t in tools if t.get("name") == "run_command"),
            tools[0]["name"] if tools else None,
        )

        if target_tool:
            call_message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": target_tool,
                    "arguments": {
                        "command": 'echo "Echo Echa"',
                        "workdir": "./",
                    },
                },
            }
            res = client.send_message(call_message)

            print("\n============= TOOL RESPONSE =============")
            if res and "result" in res:
                content = res["result"].get("content", [{}])[0].get("text", "")
                is_error = res["result"].get("isError", False)
                print(f"isError: {is_error}")
                print(f"Content:\n{content}")
            else:
                print(f"Raw response: {res}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {type(e).__name__}: {e}")

    finally:
        # Step 5: Clean Up
        print("\n5. Closing connection...")
        client.close()


if __name__ == "__main__":
    main()
'''

# ================ ================== ================ #
# ================ ================== ================ #
# ================ SERVEUR MOCK STDIO ================ #
# ================ ================== ================ #
# ================ ================== ================ #

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
