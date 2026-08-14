"""MCP server for public Puerto Rico jurisprudence sources.

Core rule: source-first / zero citation hallucination. This server never
fabricates cases, citations, party names, judges, dates, docket numbers,
holdings, or quotations. Missing facts remain missing.

The server may extract and rank information that is actually present in a
public source, but the language model is never treated as the source of legal
authority.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
ALLOWED_HOSTS = ("poderjudicial.pr", "www.poderjudicial.pr", "lexjuris.com", "www.lexjuris.com")
TIMEOUT = 20.0
MAX_RESULTS = 50
MAX_DOCUMENT_CHARS = 50000


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
    # Conservative patterns only. If a format is not recognized, return empty.
    patterns = (
        r"\b([A-Z]{1,5}-\d{2,5}-\d{1,6})\b",
        r"\b([A-Z]{1,5}\s+\d{2,5}-\d{1,6})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            return clean(match.group(1))
    return ""


def source_name(url: str) -> str:
    return "LexJuris" if "lexjuris.com" in url.lower() else "Poder Judicial de Puerto Rico"


def allowed_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
    except Exception:
        return False


async def fetch_response(url: str) -> httpx.Response:
    headers = {
        "User-Agent": "mcp-puerto-rico-sentencias/0.3 (legal-research client)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response


async def fetch_text(url: str) -> str:
    response = await fetch_response(url)
    return response.text


def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    """Extract facts visible in an index page; never infer missing metadata."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[Decision] = []

    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        haystack = f"{text} {href}"
        citation = extract_citation(haystack)
        href_lower = href.lower()

        looks_like_decision = bool(
            citation
            or href_lower.endswith(".pdf")
            or any(token in haystack.upper() for token in ("SENTENCIA", "OPINIÓN", "OPINION", "TSPR"))
        )
        if not looks_like_decision:
            continue

        citation_year = int(re.search(r"\d{4}", citation).group(0)) if citation else None
        if year is not None and citation_year is not None and citation_year != year:
            continue

        # A source URL plus an explicit TSPR citation is enough to verify the
        # citation identifier. Other metadata is never guessed.
        verified = bool(href and citation)
        results.append(
            Decision(
                title=text,
                url=href,
                source=source_name(href),
                citation=citation,
                case_number=extract_case_number(haystack),
                verified=verified,
                verification_status="verified_source_identifier" if verified else "source_found_identifier_unconfirmed",
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
    html = await fetch_text(OFFICIAL_INDEX)
    candidates = parse_index(html, OFFICIAL_INDEX, year)
    terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", query) if len(t) > 2]
    if not terms:
        return candidates[:limit]

    scored: list[tuple[int, Decision]] = []
    for item in candidates:
        blob = f"{item.title} {item.citation} {item.case_number} {item.subject}".lower()
        score = sum(1 for term in terms if term in blob)
        if score:
            scored.append((score, item))

    return [item for _, item in sorted(scored, key=lambda pair: -pair[0])[:limit]]


async def citation_search(citation: str) -> list[Decision]:
    """Return exact citation matches only; never approximate or substitute."""
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


def extract_html_document(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()

    blocks: list[str] = []
    for tag in soup.find_all(["p", "blockquote", "li"]):
        value = clean(tag.get_text(" ", strip=True))
        if value and len(value) >= 20:
            blocks.append(value)

    if blocks:
        return "\n\n".join(blocks), blocks
    text = clean(soup.get_text(" ", strip=True))
    return text, [text] if text else []


def extract_pdf_document(content: bytes) -> tuple[str, list[str]]:
    reader = PdfReader(io.BytesIO(content))
    page_blocks: list[str] = []
    paragraphs: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.replace("\r", "\n")
        raw_blocks = re.split(r"\n\s*\n+", page_text)
        page_paragraphs = [clean(block) for block in raw_blocks if clean(block)]
        for block in page_paragraphs:
            paragraphs.append(f"[página {page_number}] {block}")
        if page_paragraphs:
            page_blocks.append("\n\n".join(page_paragraphs))

    return "\n\n".join(page_blocks), paragraphs


def find_relevant_paragraphs(paragraphs: list[str], terms: str, limit: int = 8) -> list[dict[str, Any]]:
    terms_list = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", terms) if len(t) > 2]
    if not terms_list:
        return [{"numero": i + 1, "texto": p} for i, p in enumerate(paragraphs[:limit])]

    scored: list[tuple[int, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        low = paragraph.lower()
        score = sum(1 for term in terms_list if term in low)
        if score:
            scored.append((score, index, paragraph))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"numero": index + 1, "texto": paragraph, "coincidencias": score}
        for score, index, paragraph in scored[:limit]
    ]


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 20) -> dict[str, Any]:
    """Busca decisiones públicas sin completar datos que la fuente no contiene."""
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
async def leer_sentencia(url: str, terminos: str = "", max_parrafos: int = 8) -> dict[str, Any]:
    """Lee una sentencia/documento público y devuelve pasajes extraídos de la fuente.

    Los pasajes no son generados por el modelo. En PDF se conserva el número de
    página cuando puede obtenerse mediante extracción de texto. Si el documento
    no es accesible o no contiene texto extraíble, se informa el fallo.
    """
    if not allowed_url(url):
        return {"error": "Por seguridad, solo se permiten URLs HTTPS de las fuentes públicas configuradas.", "verificado": False}

    try:
        response = await fetch_response(url)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf")

        if is_pdf:
            text, paragraphs = extract_pdf_document(response.content)
            document_type = "PDF"
        else:
            text, paragraphs = extract_html_document(response.text)
            document_type = "HTML"

        if not text:
            return {
                "url": url,
                "verificado": False,
                "error": "La fuente respondió, pero no contiene texto extraíble. No se generará contenido sustitutivo.",
            }

        try:
            max_parrafos = max(1, min(int(max_parrafos), 30))
        except (TypeError, ValueError):
            max_parrafos = 8

        relevantes = find_relevant_paragraphs(paragraphs, terminos, max_parrafos)
        citation = extract_citation(text)
        case_number = extract_case_number(text)

        return {
            "url": url,
            "fuente": source_name(url),
            "tipo_documento": document_type,
            "cita_tspr": citation,
            "numero_caso": case_number,
            "parrafos": relevantes,
            "total_parrafos_extraidos": len(paragraphs),
            "procedencia": "Texto extraído directamente del documento fuente; no generado por el modelo.",
            "verificado": True,
        }
    except Exception as exc:
        return {
            "error": "No fue posible leer o extraer el documento; no se hará ninguna inferencia sobre su contenido.",
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
    """Devuelve diagnóstico y garantías de integridad."""
    return {
        "servidor": "puerto-rico-sentencias",
        "version": "0.3.0",
        "fuentes": [OFFICIAL_INDEX, LEXJURIS_SEARCH],
        "citation_integrity": {
            "no_casos_inventados": True,
            "no_citas_inventadas": True,
            "no_nombres_inventados": True,
            "no_fechas_o_ponentes_inferidos": True,
            "no_citas_aproximadas_en_buscar_por_cita": True,
            "no_citas_textuales_generadas": True,
            "source_required": True,
        },
        "documentos": {"pdf": True, "html": True, "pasajes_con_procedencia": True},
        "privacidad": "No se almacenan consultas ni documentos por defecto.",
        "anti_bot": "No se eluden CAPTCHA, autenticación ni controles de acceso.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
