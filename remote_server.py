"""Remote MCP entrypoint for ChatGPT and other MCP clients.

Uses the expanded Puerto Rico legal research MCP instance and exposes it through
Streamable HTTP instead of stdio.

Deploy this process behind HTTPS. MCP clients connect to the resulting /mcp URL.
"""

from __future__ import annotations

import os

from mcp.server.transport_security import TransportSecuritySettings

from mixed_server import mcp

# Stable public deployment host. Keeping this explicit preserves DNS-rebinding
# protection while allowing the production Railway endpoint without requiring
# a manually configured environment variable.
RAILWAY_PRODUCTION_HOST = (
    "mcp-puerto-rico-investigacion-juridica-production.up.railway.app"
)


def _append_host(values: list[str], host: str) -> None:
    host = (host or "").strip()
    if not host:
        return
    # FastMCP's host validation may see the Host header either with or without
    # an explicit port depending on the reverse proxy, so allow both forms.
    for candidate in (host, f"{host}:*"):
        if candidate not in values:
            values.append(candidate)


def _append_origin(values: list[str], host: str) -> None:
    host = (host or "").strip()
    if not host:
        return
    origin = f"https://{host}"
    if origin not in values:
        values.append(origin)


def _configure_remote_server() -> None:
    """Configure the shared FastMCP instance for HTTP deployments.

    Supports Render and Railway automatically while retaining explicit
    MCP_ALLOWED_HOSTS/MCP_ALLOWED_ORIGINS overrides for other deployments.
    """
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))

    configured_hosts = [
        value.strip()
        for value in os.getenv("MCP_ALLOWED_HOSTS", "").split(",")
        if value.strip()
    ]
    configured_origins = [
        value.strip()
        for value in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]

    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    railway_host = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

    # Railway exposes RAILWAY_PUBLIC_DOMAIN on public services. The explicit
    # production hostname is also included so the service works immediately if
    # that variable is absent or delayed during a deployment.
    for deployment_host in (
        render_host,
        railway_host,
        RAILWAY_PRODUCTION_HOST,
    ):
        _append_host(configured_hosts, deployment_host)
        _append_origin(configured_origins, deployment_host)

    # Local development remains allowed. These are intentionally explicit
    # rather than disabling DNS-rebinding protection globally.
    for local_host in ("localhost", "127.0.0.1", "[::1]"):
        _append_host(configured_hosts, local_host)

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
