import subprocess
from enum import Enum
import shlex
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import json


class TransportMode(Enum):
    STDIO = "stdio"
    HTTP = "http"


class McpClient(ABC):
    def __init__(self, transport: str) -> None:
        self.transport: TransportMode = TransportMode(transport)

    def _build_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    def _build_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build notification JSON-RPC 2.0 (no ID)."""
        notif = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notif["params"] = params
        return notif

    @abstractmethod
    def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message to the server and return response."""
        pass

    @abstractmethod
    def connect(self) -> None:
        """Starting the process to connection to the server"""
        pass


class McpHttp(McpClient):
    def __init__(self, url):
        super().__init__(TransportMode.HTTP)
        self.url = url


class McpStdio(McpClient):
    def __init__(self, command: str) -> None:
        super().__init__(TransportMode.STDIO)
        self.command: str = command
        self.process: Optional[subprocess.Popen] = None
        self.connect()

    def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message to the server and return response."""
        if not self.process or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("Not connected to Stdio process")

        payload = json.dumps(message)
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


