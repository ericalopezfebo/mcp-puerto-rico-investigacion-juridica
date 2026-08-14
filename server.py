"""MCP server for public Puerto Rico jurisprudence sources.

Citation-integrity is a hard requirement: this server never fabricates legal
authorities. A decision is returned as verified only when its identifying data
comes from a configured public source. The model may summarize verified text,
but it is never the source of a citation, party name, date, judge, case number,
or quotation.

The implementation intentionally avoids bypassing CAPTCHAs, authentication,
rate limits, or other access controls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
TIMEOUT = 20.0
MAX_RESULTS = 50


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
    verified: bool = False
    verification_status: str = "unverified"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_citation(value: str) -> str:
    return clean(value).upper().replace("-", " ")


def extract_citation(text: str) -> str:
    match = re.search(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I)
    return clean(match.group(0)) if match else ""


def extract_case_number(text: str) -> str:
    # Only recognize conservative Puerto Rico Supreme Court docket formats.
    patterns = [
        r"\b([A-Z]{1,5}-\d{2,5}-\d{1,6})\b",
        r"\b([A-Z]{1,5}\s+\d{2,5}-\d{1,6})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            return clean(match.group(1))
    return ""


async def fetch(url: str) -> str:
    headers = {
        "User-Agent": "mcp-puerto-rico-sentencias/0.2 (research client)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    """Extract only facts actually present in the source page.

    Missing metadata remains empty. Nothing is inferred from the title or by
    asking a language model to fill gaps.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[Decision] = []
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        haystack = f"{text} {href}"
        citation = extract_citation(haystack)
        if not citation and not any(token in haystack.upper() for token in ("PDF", "TSPR", "SENTENCIA", "OPINION")):
            continue
        citation_year = int(re.search(r"\d{4}", citation).group(0)) if citation else None
        if year is not None and citation_year is not None and citation_year != year:
            continue
        # A URL alone is not enough to claim that a legal authority exists.
        # The result is marked verified only when it has a source URL and a
        # source-visible identifier such as a TSPR citation.
        verified = bool(href and citation)
        results.append(
            Decision(
                title=text or "",
                url=href,
                source="Poder Judicial de Puerto Rico",
                citation=citation,
                case_number=extract_case_number(haystack),
                verified=verified,
                verification_status="verified_source" if verified else "identifier_not_confirmed",
            )
        )
    seen: set[str] = set()
    unique: list[Decision] = []
    for result in results:
        if result.url not in seen:
            seen.add(result.url)
            unique.append(result)
    return unique


async def official_search(query: str, year: int | None, limit: int) -> list[Decision]:
    html = await fetch(OFFICIAL_INDEX)
    candidates = parse_index(html, OFFICIAL_INDEX, year)
    terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", query) if len(t) > 2]
    if terms:
        scored: list[tuple[int, Decision]] = []
        for item in candidates:
            blob = f"{item.title} {item.citation} {item.case_number} {item.subject}".lower()
            score = sum(1 for term in terms if term in blob)
            if score:
                scored.append((score, item))
        candidates = [item for _, item in sorted(scored, key=lambda pair: -pair[0])]
    return candidates[:limit]


async def citation_search(citation: str) -> list[Decision]:
    """Return only exact, source-verified citation matches.

    Critically, this function does NOT fall back to approximate results. An
    absent citation means an empty result, never a plausible substitute.
    """
    requested = normalize_citation(citation)
    if not requested:
        return []
    year_match = re.search(r"\b((?:19|20)\d{2})\b", requested)
    year = int(year_match.group(1)) if year_match else None
    results = await official_search(citation, year, MAX_RESULTS)
    return [
        result
        for result in results
        if result.citation and normalize_citation(result.citation) == requested and result.verified
    ]


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 20) -> dict[str, Any]:
    """Busca decisiones públicas y devuelve únicamente datos provenientes de la fuente.

    No completa nombres, citas, fechas, jueces o números de caso que falten.
    """
    maximo = max(1, min(maximo, MAX_RESULTS))
    try:
        results = await official_search(consulta, ano, maximo)
        return {
            "consulta": consulta,
            "ano": ano,
            "resultados": [asdict(r) for r in results],
            "fuente": OFFICIAL_INDEX,
            "integridad_citacion": "Los campos faltantes se dejan vacíos; no se inventan autoridades.",
        }
    except Exception as exc:
        return {
            "error": "No fue posible consultar la fuente oficial.",
            "detalle_tecnico": str(exc),
            "fuente": OFFICIAL_INDEX,
            "resultados": [],
        }


@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str, Any]:
    """Localiza una cita TSPR exacta; nunca sustituye una cita no encontrada."""
    try:
        results = await citation_search(cita)
        if not results:
            return {
                "cita": cita,
                "encontrado": False,
                "resultados": [],
                "verificado": False,
                "mensaje": "La cita exacta no fue encontrada en la fuente oficial consultada. No se generará ni sustituirá por otra cita.",
                "fuente": OFFICIAL_INDEX,
            }
        return {
            "cita": cita,
            "encontrado": True,
            "verificado": True,
            "resultados": [asdict(r) for r in results],
        }
    except Exception as exc:
        return {
            "cita": cita,
            "encontrado": False,
            "verificado": False,
            "resultados": [],
            "error": "No fue posible verificar la cita.",
            "detalle_tecnico": str(exc),
            "fuente": OFFICIAL_INDEX,
        }


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_chars: int = 12000) -> dict[str, Any]:
    """Lee texto público y conserva la procedencia de la URL.

    No afirma que el texto sea una sentencia ni inventa metadatos. El texto
    devuelto se identifica como extracción de la página proporcionada.
    """
    allowed = ("https://poderjudicial.pr/", "https://www.lexjuris.com/")
    if not url.startswith(allowed):
        return {"error": "Por seguridad, solo se permiten URLs de las fuentes públicas configuradas."}
    try:
        html = await fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = clean(soup.get_text(" ", strip=True))
        original_length = len(text)
        if terminos:
            terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", terminos) if len(t) > 2]
            snippets: list[str] = []
            low = text.lower()
            for term in terms:
                start = low.find(term)
                if start >= 0:
                    snippets.append(text[max(0, start - 500): start + 1500])
            if snippets:
                text = "\n\n---\n\n".join(snippets)
        limit = max(1000, min(max_chars, 50000))
        return {
            "url": url,
            "texto": text[:limit],
            "truncado": len(text) > limit,
            "longitud_original": original_length,
            "procedencia": "texto extraído directamente de la URL proporcionada; no generado por el modelo",
            "verificado": True,
        }
    except Exception as exc:
        return {
            "error": "No fue posible leer el documento; no se hará ninguna inferencia sobre su contenido.",
            "detalle_tecnico": str(exc),
            "url": url,
            "verificado": False,
        }


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Explica fuentes y filtros disponibles sin generar autoridades."""
    return {
        "consulta": consulta,
        "campo": campo,
        "fuentes": {"tribunal_supremo": OFFICIAL_INDEX, "lexjuris": LEXJURIS_SEARCH},
        "filtros": ["año", "cita TSPR", "número de caso", "términos del asunto"],
        "regla_integridad": "Las autoridades deben estar verificadas en una fuente identificable; si no se encuentran, se informa que no fueron encontradas.",
    }


@mcp.tool()
def estado() -> dict[str, Any]:
    """Devuelve información de diagnóstico y las garantías de integridad."""
    return {
        "servidor": "puerto-rico-sentencias",
        "version": "0.2.0",
        "fuentes": [OFFICIAL_INDEX, LEXJURIS_SEARCH],
        "citation_integrity": {
            "no_casos_inventados": True,
            "no_citas_inventadas": True,
            "no_nombres_inventados": True,
            "no_fechas_o_ponentes_inferidos": True,
            "no_citas_aproximadas_en_buscar_por_cita": True,
            "source_required": True,
        },
        "privacidad": "No se almacenan consultas ni documentos por defecto.",
        "anti_bot": "No se eluden CAPTCHA, autenticación ni controles de acceso.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
