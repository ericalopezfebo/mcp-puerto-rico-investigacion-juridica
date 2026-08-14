"""Compatibility import for the MCP Python SDK.

The project supports MCP SDK 1.x and 2.x.  The public FastMCP import path
changed in the 2.x line, so keep the compatibility logic in one place.
"""

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server import FastMCP

__all__ = ["FastMCP"]
