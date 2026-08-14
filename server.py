"""MCP server for public Puerto Rico jurisprudence sources.

The implementation intentionally avoids bypassing CAPTCHAs, authentication,
rate limits, or other access controls. Search results preserve source URLs so
users can verify every decision against the original publication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
TIMEOUT = 20.0


@dataclass
class Decision:
    title: str
    url: str
    source: str
    citation: str = ""
    case_number: str = ""
    date: str = ""
    judge: str = ""
    subject: str = ""
    snippet: str = ""


async def fetch(url: str) -> str:
    headers = {
        "User-Agent": "mcp-puerto-rico-sentencias/0.1 (research client)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def clean(text: str) -> str:
    return re.sub(r"\\s+", " ", text or "").strip()


def extract_pdf_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        if ".pdf" in href.lower() or "pdf" in (a.get_text(" ", strip=True) or "").lower():
            if href not in out:
                out.append(href)
    return out


def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[Decision] = []
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        haystack = f"{text} {href}"
        if not ("TSPR" in haystack.upper() or "PDF" in text.upper() or "sentencia" in text.lower()):
            continue
        citation_match = re.search(r"(\\d{4})\\s*TSPR\\s*(\\d+)", haystack, re.I)
        if year and citation_match and int(citation_match.group(1)) != year:
            continue
        results.append(Decision(title=text or "Decisión del Tribunal Supremo", url=href, source="Poder Judicial de Puerto Rico", citation=citation_match.group(0) if citation_match else ""))
    # Deduplicate by URL while preserving page order.
    seen: set[str] = set()
    return [r for r in results if not (r.url in seen or seen.add(r.url))]


async def official_search(query: str, year: int | None, limit: int) -> list[Decision]:
    html = await fetch(OFFICIAL_INDEX)
    candidates = parse_index(html, OFFICIAL_INDEX, year)
    terms = [t.lower() for t in re.findall(r"[\\wÀ-ÿ]+", query) if len(t) > 2]
    if terms:
        scored = []
        for item in candidates:
            blob = f"{item.title} {item.citation} {item.subject}".lower()
            score = sum(1 for t in terms if t in blob)
            if score:
                scored.append((score, item))
        candidates = [item for _, item in sorted(scored, key=lambda x: -x[0])]
    return candidates[:limit]


async def citation_search(citation: str) -> list[Decision]:
    year_match = re.search(r"(19|20)\\d{2}", citation)
    year = int(year_match.group(0)) if year_match else None
    results = await official_search(citation, year, 25)
    needle = clean(citation).lower()
    exact = [r for r in results if needle in f"{r.citation} {r.title}".lower()]
    return exact or results


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 20) -> dict[str, Any]:
    """Busca decisiones públicas del Tribunal Supremo de Puerto Rico.

    Args:
        consulta: Términos, cita TSPR, número de caso o asunto.
        ano: Año de la decisión, cuando se conoce.
        maximo: Máximo de resultados, limitado a 50 por consulta.
    """
    maximo = max(1, min(maximo, 50))
    try:
        results = await official_search(consulta, ano, maximo)
        return {"consulta": consulta, "ano": ano, "resultados": [asdict(r) for r in results], "fuente": OFFICIAL_INDEX}
    except Exception as exc:
        return {"error": f"No fue posible consultar la fuente oficial: {exc}", "fuente": OFFICIAL_INDEX}


@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str, Any]:
    """Localiza una decisión por cita TSPR o número de caso."""
    try:
        results = await citation_search(cita)
        return {"cita": cita, "resultados": [asdict(r) for r in results]}
    except Exception as exc:
        return {"error": f"No fue posible consultar la cita: {exc}", "fuente": OFFICIAL_INDEX}


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_chars: int = 12000) -> dict[str, Any]:
    """Lee una decisión pública desde una URL proporcionada por la fuente.

    La herramienta no descarga ni almacena archivos de forma permanente. Para
    PDF se informa del enlace y se intenta obtener texto cuando el servidor lo
    expone como HTML; el procesamiento PDF local puede añadirse posteriormente.
    """
    if not (url.startswith("https://poderjudicial.pr/") or url.startswith("https://www.lexjuris.com/")):
        return {"error": "Por seguridad, solo se permiten URLs de las fuentes públicas configuradas."}
    try:
        html = await fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = clean(soup.get_text(" ", strip=True))
        if terminos:
            terms = [t.lower() for t in re.findall(r"[\\wÀ-ÿ]+", terminos) if len(t) > 2]
            snippets = []
            low = text.lower()
            for term in terms:
                start = low.find(term)
                if start >= 0:
                    snippets.append(text[max(0, start - 500): start + 1500])
            if snippets:
                text = "\\n\\n---\\n\\n".join(snippets)
        return {"url": url, "texto": text[:max(1000, min(max_chars, 50000))], "truncado": len(text) > max_chars}
    except Exception as exc:
        return {"error": f"No fue posible leer el documento: {exc}", "url": url}


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Explica fuentes y filtros disponibles para refinar una búsqueda."""
    return {
        "consulta": consulta,
        "campo": campo,
        "fuentes": {
            "tribunal_supremo": OFFICIAL_INDEX,
            "lexjuris": LEXJURIS_SEARCH,
        },
        "filtros": ["año", "cita TSPR", "número de caso", "términos del asunto"],
        "nota": "La cobertura depende de lo que cada fuente publique y permita consultar públicamente.",
    }


@mcp.tool()
def estado() -> dict[str, Any]:
    """Devuelve información de diagnóstico del servidor."""
    return {
        "servidor": "puerto-rico-sentencias",
        "version": "0.1.0",
        "fuentes": [OFFICIAL_INDEX, LEXJURIS_SEARCH],
        "privacidad": "No se almacenan consultas ni documentos por defecto.",
        "anti_bot": "No se eluden CAPTCHA, autenticación ni controles de acceso.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
