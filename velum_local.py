"""Local-first VELUM MCP server for legal documents.

This server is intentionally stdio-only. It never uploads local documents and
contains no HTTP client. Local documents are read, fingerprinted, redacted,
and prepared for an external AI entirely on the user's machine.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.local_privacy import (
    anonymize_document,
    document_fingerprint,
    list_local_documents,
    privacy_status,
    redact_document_copy,
)

mcp = FastMCP("VELUM Local Legal Privacy")


@mcp.tool()
def listar_documentos_locales() -> dict:
    """List allowed local legal-document files without reading their contents."""
    return list_local_documents()


@mcp.tool()
def huella_documento_local(ruta: str) -> dict:
    """Return a SHA-256 fingerprint and metadata for a local document, never its text."""
    return document_fingerprint(ruta)


@mcp.tool()
def preparar_documento_para_ia(
    ruta: str,
    redacciones_json: str = "",
    max_caracteres: int = 60000,
) -> dict:
    """Extract and redact a local document, returning only the sanitized text.

    The original file is never returned. Built-in redactions cover common
    identifiers such as email, phone, SSN and payment-card numbers. Additional
    exact strings can be supplied as a JSON object mapping sensitive text to a
    replacement label, for example: {"Juan Pérez": "[CLIENTE]"}.

    This is deterministic local redaction, not an AI privacy guarantee. Review
    the sanitized result before sending it to an external model.
    """
    return anonymize_document(ruta, redacciones_json, max_caracteres)


@mcp.tool()
def crear_copia_anonimizada(
    ruta: str,
    destino: str = "",
    redacciones_json: str = "",
) -> dict:
    """Create a sanitized local copy without returning the original document text."""
    return redact_document_copy(ruta, destino, redacciones_json)


@mcp.tool()
def estado_privacidad() -> dict:
    """Describe the local-only privacy boundary of this server."""
    return privacy_status()


def main() -> None:
    """Run the MCP server over stdio; no listening port is opened."""
    mcp.run()


if __name__ == "__main__":
    main()
