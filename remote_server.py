"""Remote MCP entrypoint for ChatGPT and other MCP clients.

Uses the same MCP instance and the same tools as server.py, but exposes them
through Streamable HTTP instead of stdio.

Deploy this process behind HTTPS. ChatGPT connects to the resulting /mcp URL.
"""

from __future__ import annotations

import os

from server import mcp


def main() -> None:
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )


if __name__ == "__main__":
    main()
