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
        self.send_message(init_request)
        notif = self._build_notification(method="notifications/initialized")
        self.send_message(notif)
        server_request = self._build_request("tools/list")
        server_response = self.send_message(server_request)

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
    """ MCP HTTP client implementation """

    def __init__(self, url: str) -> None:
        """
        Initialize the HTTP MCP client
        Args:
            url: str = target server endpoint URL
        """
        super().__init__(TransportMode.HTTP)
        self.endpoint_url: str = url.rstrip("/")
        if not self.endpoint_url.endswith("/mcp"):
            self.endpoint_url += "/mcp"

        self.session_id: str | None = None
        self._http_client: httpx.Client | None = None
        self.connect()

    def send_message(self, message: dict[str, Any]) -> Any | None:
        """
        Send a JSON-RPC message to the server
        Args:
            message: dict[str, Any] = payload to send to the server
        Return:
            Any | None = parsed response data or None for notifications
        """
        if self._http_client is None:
            raise RuntimeError(
                "HTTP Client not connected. "
                "Call connect() first."
            )

        client = self._http_client
        headers = {"Content-Type": "application/json"}

        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        response = client.post(
            self.endpoint_url,
            json=message,
            headers=headers,
        )
        response.raise_for_status()

        if not self.session_id and "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]

        if "id" not in message:
            return None

        text = response.text.strip()
        if "data: " in text:
            for line in text.splitlines():
                if line.startswith("data: "):
                    raw_json = line.removeprefix("data: ").strip()
                    return json.loads(raw_json)

        return response.json() if text else None

    def connect(self) -> None:
        """ Establish HTTP client connection """
        self._http_client = httpx.Client(timeout=30.0)
        print(f"[INFO] Client ready for endpoint: {self.endpoint_url}")

    def close(self) -> None:
        """ Close the underlying HTTP client session """
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None


class McpStdio(McpClient):
    def __init__(self, command: str,
                 env: dict[str, str] | None = None) -> None:
        """
        MCP stdio client
        Args:
            command: str = the command to execute on the server
        Return:
            None
        """
        super().__init__(TransportMode.STDIO)
        self.command: str = command
        self.env = env
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
            bufsize=1,
            env=self.env,
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
        return McpStdio(command=spec.command, env=spec.env)

    if spec.transport == "http":
        if not spec.url:
            raise ValueError("An url is required for the http client.")
        return McpHttp(url=spec.url)

    raise ValueError(f"Unknown transport method: {spec.transport}")
