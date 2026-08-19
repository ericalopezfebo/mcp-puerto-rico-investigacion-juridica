"""Remote MCP entrypoint for ChatGPT and other MCP clients.

Uses the expanded Puerto Rico legal research MCP instance and exposes it through
Streamable HTTP instead of stdio.

Deploy this process behind HTTPS. ChatGPT connects to the resulting /mcp URL.
"""

from __future__ import annotations

import os

from mcp.server.transport_security import TransportSecuritySettings

from research_server import mcp


def _configure_remote_server() -> None:
    """Configure the shared FastMCP instance for the HTTP deployment."""
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))

    configured_hosts = [
        value.strip()
        for value in os.getenv("MCP_ALLOWED_HOSTS", "").split(",")
        if value.strip()
    ]
    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_host and render_host not in configured_hosts:
        configured_hosts.append(render_host)

    if not configured_hosts:
        configured_hosts = ["localhost:*", "127.0.0.1:*", "[::1]:*"]

    configured_origins = [
        value.strip()
        for value in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]
    if render_host:
        render_origin = f"https://{render_host}"
        if render_origin not in configured_origins:
            configured_origins.append(render_origin)

    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=configured_hosts,
        allowed_origins=configured_origins,
    )


def main() -> None:
    _configure_remote_server()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
