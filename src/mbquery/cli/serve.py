"""mbquery serve — start MCP server."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

err_console = Console(stderr=True)

def serve_cmd(profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """Start MCP server (stdio transport)."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        err_console.print("[red]Error:[/] MCP not installed. Run: pip install mbquery[mcp]")
        raise typer.Exit(1)

    from mbquery.config.store import ConfigStore
    from mbquery.mcp.server import create_mcp_server

    store = ConfigStore()
    try:
        active = store.resolve_profile(profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    cache_dir = store.config_dir / "schema_cache"
    mbq = create_mcp_server(active, cache_dir)
    server = Server("mbquery")

    @server.list_tools()
    async def list_tools():
        tools = mbq.get_tools()
        return [Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"]) for t in tools]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result_text = mbq.call_tool(name, arguments)
        return [TextContent(type="text", text=result_text)]

    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    err_console.print("[dim]mbquery MCP server starting...[/]")
    asyncio.run(run())
