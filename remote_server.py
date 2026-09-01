"""Remote MCP entrypoint for ChatGPT and other MCP clients.

Uses the expanded Puerto Rico legal research MCP instance and exposes it through
Streamable HTTP instead of stdio.

Deploy this process behind HTTPS. MCP clients connect to the resulting /mcp URL.
"""

from __future__ import annotations

import os
import secrets

from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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


def _authorized(authorization: str | None, expected_token: str) -> bool:
    """Validate a Bearer token without leaking timing information."""
    if not authorization or not authorization.startswith("Bearer "):
        return False
    supplied = authorization.removeprefix("Bearer ").strip()
    return bool(supplied) and secrets.compare_digest(supplied, expected_token)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Protect every MCP request while leaving the health probe public."""

    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return JSONResponse({"status": "ok"})
        if not _authorized(request.headers.get("authorization"), self.token):
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


def create_remote_app():
    """Create the authenticated ASGI application used in remote deployments."""
    _configure_remote_server()
    token = os.getenv("MCP_API_KEY", "").strip()
    allow_insecure = os.getenv("MCP_ALLOW_INSECURE", "").lower() in {"1", "true", "yes"}
    if not token and not allow_insecure:
        raise RuntimeError(
            "MCP_API_KEY is required for remote deployment. "
            "Set MCP_ALLOW_INSECURE=true only for isolated local development."
        )
    app = mcp.streamable_http_app()
    if token:
        app.add_middleware(BearerAuthMiddleware, token=token)
    return app


def main() -> None:
    import uvicorn

    app = create_remote_app()
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port)


if __name__ == "__main__":
    main()
