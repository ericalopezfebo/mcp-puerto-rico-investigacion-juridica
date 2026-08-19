"""Generic reader for public Puerto Rico primary-source documents.

The reader is intentionally conservative: it verifies that a document can be
retrieved from an allow-listed public source and extracts source text/passages.
It does not infer legal effect, current validity, amendment history, or a
holding merely because text was found.
"""
from __future__ import annotations

import re
from typing import Any

import research_server
import server as jurisprudencia

mcp = research_server.mcp


def _source_label(url: str) -> str:
    if "poderjudicial.pr" in url:
        return "Poder Judicial de Puerto Rico"
    if "estado.pr.gov" in url:
        return "Departamento de Estado de Puerto Rico"
    if "jrt.pr.gov" in url:
        return "Junta de Relaciones del Trabajo de Puerto Rico"
    return "Fuente pública permitida"


async def read_public_authority(url: str, consulta: str = "", max_pasajes: int = 8) -> dict[str, Any]:
    """Read an allow-listed official/public document and return exact passages."""
    max_pasajes = max(1, min(int(max_pasajes), 20))
    if not research_server._research_url_allowed(url):
        return {
            "url": url,
            "verificado": False,
            "error": "URL no permitida para lectura de autoridad pública",
        }

    try:
        response = await research_server._fetch(url)
    except Exception as exc:
        return {"url": url, "verificado": False, "error": str(exc)}

    content_type = response.headers.get("content-type", "").lower()
    is_pdf = "application/pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf")
    try:
        if is_pdf:
            text, paragraphs = jurisprudencia.extract_pdf_document(response.content)
            document_type = "pdf"
        else:
            text, paragraphs = jurisprudencia.extract_html_document(response.text)
            document_type = "html"
    except Exception as exc:
        return {
            "url": url,
            "fuente": _source_label(url),
            "verificado": False,
            "error": f"No se pudo extraer texto del documento: {exc}",
        }

    if not text:
        return {
            "url": url,
            "fuente": _source_label(url),
            "tipo_documento": document_type,
            "verificado": False,
            "error": "El documento no produjo texto extraíble",
        }

    terms = jurisprudencia.query_terms(consulta) if consulta else []
    passages = jurisprudencia.find_relevant_paragraphs(paragraphs, terms, limit=max_pasajes) if terms else []
    extracted: list[dict[str, Any]] = []
    for item in passages:
        passage = dict(item)
        page_match = re.search(r"\[página (\d+)\]", passage.get("texto", ""))
        passage["pagina"] = int(page_match.group(1)) if page_match else None
        extracted.append(passage)

    return {
        "url": url,
        "fuente": _source_label(url),
        "nivel_fuente": "fuente_primaria_publica_o_oficial",
        "tipo_documento": document_type,
        "verificado": True,
        "estado_verificacion": "documento_recuperado_y_texto_extraido",
        "consulta": consulta,
        "pasajes": extracted,
        "coincidencia_tematica_verificada": bool(extracted) if consulta else None,
        "caracteres_extraidos": len(text),
        "advertencia": (
            "Texto recuperado de la fuente indicada. Esto no verifica por sí solo vigencia, historial de enmiendas, "
            "tratamiento posterior ni que un pasaje constituya el holding o regla jurídica aplicable."
        ),
    }


@mcp.tool()
async def leer_autoridad_publica(url: str, consulta: str = "", max_pasajes: int = 8) -> dict[str, Any]:
    """Lee una autoridad pública permitida y devuelve pasajes textuales verificables.

    Úsala para verificar documentos descubiertos por las herramientas de leyes,
    reglamentos, Tribunal de Apelaciones o decisiones administrativas antes de
    citarlos como apoyo a una proposición jurídica. No determina vigencia ni
    tratamiento posterior automáticamente.
    """
    return await read_public_authority(url, consulta, max_pasajes)
