"""Unified local-first VELUM MCP server.

The privacy tools run only against local files. Jurisprudence tools are kept as
separate public-source research capabilities. The server itself uses stdio and
opens no network port.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

import server as jurisprudence
from mcp_server.local_privacy import (
    anonymize_document,
    document_fingerprint,
    list_local_documents,
    privacy_status,
    redact_document_copy,
)

mcp = FastMCP("VELUM Local Legal MCP")


@mcp.tool()
def listar_documentos_locales() -> dict[str, Any]:
    """List local allowed legal documents without returning their contents."""
    return list_local_documents()


@mcp.tool()
def huella_documento_local(ruta: str) -> dict[str, Any]:
    """Calculate a local SHA-256 fingerprint without returning document text."""
    return document_fingerprint(ruta)


@mcp.tool()
def preparar_documento_para_ia(
    ruta: str,
    redacciones_json: str = "",
    max_caracteres: int = 60000,
) -> dict[str, Any]:
    """Sanitize a local document and return only the sanitized text."""
    return anonymize_document(ruta, redacciones_json, max_caracteres)


@mcp.tool()
def crear_copia_anonimizada(
    ruta: str,
    destino: str = "",
    redacciones_json: str = "",
) -> dict[str, Any]:
    """Create a sanitized local text copy without modifying the original."""
    return redact_document_copy(ruta, destino, redacciones_json)


@mcp.tool()
def estado_privacidad() -> dict[str, Any]:
    """Describe the local privacy boundary."""
    return privacy_status()


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 20) -> dict[str, Any]:
    """Search public Puerto Rico jurisprudence using the source-first rules."""
    return await jurisprudence.buscar_sentencias(consulta, ano, maximo)


@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str, Any]:
    """Verify an exact TSPR citation without substituting another citation."""
    return await jurisprudence.buscar_por_cita(cita)


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_parrafos: int = 8) -> dict[str, Any]:
    """Read a public legal decision from an allowed source."""
    return await jurisprudence.leer_sentencia(url, terminos, max_parrafos)


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Show public jurisprudence sources and search rules."""
    return jurisprudence.opciones_busqueda(consulta, campo)


@mcp.tool()
def estado() -> dict[str, Any]:
    """Return combined VELUM status and citation-integrity guarantees."""
    result = jurisprudence.estado()
    result["servidor"] = "VELUM Local Legal MCP"
    result["privacidad_local"] = privacy_status()
    return result


def main() -> None:
    """Run VELUM over stdio; no HTTP listener is started."""
    mcp.run()


if __name__ == "__main__":
    main()
