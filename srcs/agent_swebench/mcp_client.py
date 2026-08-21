from mcp import Client


class MCPClient:

    def __init__(self, url: str = "http://localhost:8000/mcp"):
        self.url = url

    async def _call(self, tool_name: str, arguments: dict):
        async with Client(self.url) as client:
            result = await client.call_tool(tool_name, arguments)

            return result.content[0].text

    async def list_files(self, directory: str = ".",
                         pattern: str = "*") -> str:
        return await self._call(
            "list_files", {"directory": directory, "pattern": pattern}
        )

    async def tools_list(self):
        async with Client(self.url) as client:
            tools = await client.list_tools()
            return tools
