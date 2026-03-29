#!/usr/bin/env python3
"""
MCP Server for HTTP request tools (Postman-style)
Provides tools to send HTTP requests and inspect responses
"""

import os
import json
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

mcpSvr = Server("PostmanServer")


@mcpSvr.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="http-request",
            description="Send an HTTP request and return the response",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, PATCH, DELETE",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "default": "GET"
                    },
                    "url": {"type": "string", "description": "Full URL to request"},
                    "headers": {"type": "object", "description": "Optional headers"},
                    "body": {"type": "object", "description": "Optional JSON body"},
                    "timeout": {"type": "number", "description": "Timeout in seconds", "default": 30}
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="check-health",
            description="Check if an endpoint is reachable and returns 2xx",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to health-check"}
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="get-headers",
            description="Fetch only the response headers from a URL (HEAD request)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to inspect"}
                },
                "required": ["url"]
            }
        )
    ]


@mcpSvr.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:

    args = arguments or {}

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:

            if name == "http-request":
                method  = (args.get("method") or "GET").upper()
                url     = args["url"]
                headers = args.get("headers") or {}
                body    = args.get("body")
                timeout = float(args.get("timeout") or 30)

                response = await client.request(
                    method, url, headers=headers,
                    json=body if body else None, timeout=timeout,
                )
                try:
                    resp_body = json.dumps(response.json(), indent=2)
                except Exception:
                    resp_body = response.text[:4000]

                return [types.TextContent(type="text", text=json.dumps({
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": resp_body,
                }, indent=2))]

            elif name == "check-health":
                url = args["url"]
                try:
                    r = await client.get(url, timeout=10)
                    return [types.TextContent(type="text", text=json.dumps({
                        "url": url, "healthy": r.is_success, "status_code": r.status_code,
                    }))]
                except Exception as e:
                    return [types.TextContent(type="text", text=json.dumps({
                        "url": url, "healthy": False, "error": str(e)
                    }))]

            elif name == "get-headers":
                url = args["url"]
                r = await client.head(url, timeout=10)
                return [types.TextContent(type="text", text=json.dumps({
                    "status_code": r.status_code,
                    "headers": dict(r.headers),
                }, indent=2))]

            else:
                raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    transport = os.getenv("TRANSPORT", "stdio")

    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        port = int(os.getenv("PORT", "8002"))
        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcpSvr.run(
                    streams[0], streams[1],
                    InitializationOptions(
                        server_name="postman-mcp-server",
                        server_version="0.1.0",
                        capabilities=mcpSvr.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )

        starlette_app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ])
        config = uvicorn.Config(starlette_app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    else:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await mcpSvr.run(
                read_stream, write_stream,
                InitializationOptions(
                    server_name="postman-mcp-server",
                    server_version="0.1.0",
                    capabilities=mcpSvr.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


if __name__ == "__main__":
    asyncio.run(main())

