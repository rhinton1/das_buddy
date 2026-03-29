from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


async def run_mcp_operation(server_path, tool_name, arguments):
    """Call an MCP tool via stdio (spawns a local subprocess)."""
    server_params = StdioServerParameters(
        command="python",
        args=[server_path],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result


async def run_mcp_operation_container(base_url, tool_name, arguments):
    """Call an MCP tool via SSE (connects to a running Docker container)."""
    async with sse_client(f"{base_url}/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result
