"""MCP server for verifiable Puerto Rico jurisprudence research.

Design goal: source-first legal research. The server never invents cases,
citations, holdings, dates, party names, judges, docket numbers, or quotations.
It searches public documents, extracts source text, and returns the exact source
URL plus passages that were actually extracted from that source.
"""
from __future__ import annotations

import asyncio
import io
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
ALLOWED_HOSTS = (
    "poderjudicial.pr",
    "www.poderjudicial.pr",
    "lexjuris.com",
    "www.lexjuris.com",
)
TIMEOUT = 25.0
MAX_RESULTS = 50
MAX_DOCUMENT_CHARS = 120_000
MAX_CONTENT_CANDIDATES = 72


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
    page: int | None = None
    relevance_score: float = 0.0
    verified: bool = False
    verification_status: str = "unverified"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_citation(value: str) -> str:
    return clean(value).upper().replace("-", " ")


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ü", "u")
    value = re.sub(r"[^a-z0-9ñ\s]", " ", value)
    return clean(value)


def extract_citation(text: str) -> str:
    match = re.search(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I)
    return clean(match.group(0)) if match else ""


def extract_case_number(text: str) -> str:
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
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
    except Exception:
        return False


async def fetch_response(url: str) -> httpx.Response:
    if not allowed_url(url):
        raise ValueError("URL no permitida")
    headers = {
        "User-Agent": "mcp-puerto-rico-sentencias/1.0 (legal-research client)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response


async def fetch_text(url: str) -> str:
    response = await fetch_response(url)
    return response.text


def looks_like_year_page(url: str) -> bool:
    return bool(re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})/?$", url.lower()))


def year_from_url(url: str) -> int | None:
    match = re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})", url.lower())
    return int(match.group(1)) if match else None


def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    """Extract only facts visible in an index page; never infer metadata."""
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
        citation_year = int(re.search(r"\d{4}", citation).group(0)) if citation else year_from_url(href)
        if year is not None and citation_year is not None and citation_year != year:
            continue
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
    return dedupe_decisions(results)


def dedupe_decisions(items: list[Decision]) -> list[Decision]:
    seen: set[str] = set()
    out: list[Decision] = []
    for item in items:
        if item.url not in seen:
            seen.add(item.url)
            out.append(item)
    return out


async def get_year_links(year: int) -> list[Decision]:
    """Fetch one official year index and return its decision/PDF links."""
    main_html = await fetch_text(OFFICIAL_INDEX)
    main_links = parse_index(main_html, OFFICIAL_INDEX)
    year_links = [r for r in main_links if year_from_url(r.url) == year]
    direct_pdfs = [r for r in year_links if r.url.lower().split("?", 1)[0].endswith(".pdf")]
    page_links = [r for r in year_links if looks_like_year_page(r.url)]
    if page_links:
        try:
            year_html = await fetch_text(page_links[0].url)
            nested = parse_index(year_html, page_links[0].url, year)
            return dedupe_decisions(direct_pdfs + nested)
        except Exception:
            pass
    return dedupe_decisions(direct_pdfs)


LEGAL_SYNONYMS = {
    "pension alimenticia": [
        "pension alimenticia", "pensión alimenticia", "alimentos", "obligacion alimentaria",
        "obligación alimentaria", "obligaciones alimentarias", "alimentante", "alimentista",
        "manutencion", "manutención", "cuota alimentaria", "sustento", "child support",
    ],
    "alimentos": [
        "alimentos", "pension alimenticia", "pensión alimenticia", "obligacion alimentaria",
        "obligación alimentaria", "alimentante", "alimentista", "manutencion", "manutención",
    ],
    "custodia": ["custodia", "guarda", "patria potestad", "relaciones paterno filiales"],
    "divorcio": ["divorcio", "divorciado", "disolucion matrimonial", "disolución matrimonial"],
    "menor": ["menor", "menores", "niño", "niña", "hijo", "hija"],
}


def query_terms(query: str) -> list[str]:
    raw = [t for t in re.findall(r"[\wÀ-ÿ]+", query.lower()) if len(t) > 2]
    expanded: list[str] = list(raw)
    qnorm = normalize_text(query)
    for key, synonyms in LEGAL_SYNONYMS.items():
        if normalize_text(key) in qnorm or any(normalize_text(s) in qnorm for s in synonyms):
            expanded.extend(synonyms)
    seen: set[str] = set()
    result: list[str] = []
    for item in expanded:
        normalized = normalize_text(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(item)
    return result


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
        page_text = (page.extract_text() or "").replace("\r", "\n")
        raw_blocks = re.split(r"\n\s*\n+", page_text)
        page_paragraphs = [clean(block) for block in raw_blocks if clean(block)]
        for block in page_paragraphs:
            paragraphs.append(f"[página {page_number}] {block}")
        if page_paragraphs:
            page_blocks.append("\n\n".join(page_paragraphs))
    return "\n\n".join(page_blocks), paragraphs


def find_relevant_paragraphs(paragraphs: list[str], terms: str | list[str], limit: int = 8) -> list[dict[str, Any]]:
    terms_list = terms if isinstance(terms, list) else query_terms(terms)
    normalized_terms = [normalize_text(t) for t in terms_list if normalize_text(t)]
    scored: list[tuple[float, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        low = normalize_text(paragraph)
        hits = [term for term in normalized_terms if term and term in low]
        if hits:
            score = float(len(hits)) + (2.0 if len(hits) >= 2 else 0.0)
            scored.append((score, index, paragraph))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"numero": index + 1, "texto": paragraph, "coincidencias": round(score, 2)}
        for score, index, paragraph in scored[:limit]
    ]


def score_document(decision: Decision, text: str, paragraphs: list[str], query: str) -> tuple[float, dict[str, Any] | None]:
    terms = query_terms(query)
    low = normalize_text(text[:MAX_DOCUMENT_CHARS])
    score = 2.0 if decision.citation else 0.0
    for term in terms:
        nt = normalize_text(term)
        if nt:
            count = min(low.count(nt), 8)
            if count:
                score += 1.0 + min(count, 4) * 0.7
    relevant = find_relevant_paragraphs(paragraphs, terms, limit=6)
    if relevant:
        score += min(10.0, sum(float(x["coincidencias"]) for x in relevant) / 2)
    return score, relevant[0] if relevant else None


async def read_decision(decision: Decision, query: str) -> Decision:
    try:
        response = await fetch_response(decision.url)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or decision.url.lower().split("?", 1)[0].endswith(".pdf")
        text, paragraphs = extract_pdf_document(response.content) if is_pdf else extract_html_document(response.text)
        if not text:
            return decision
        score, best = score_document(decision, text, paragraphs, query)
        decision.relevance_score = round(score, 2)
        if best:
            decision.snippet = best["texto"]
            page_match = re.search(r"\[página (\d+)\]", best["texto"])
            decision.page = int(page_match.group(1)) if page_match else None
        citation = extract_citation(text)
        if citation:
            decision.citation = citation
            decision.verified = True
            decision.verification_status = "verified_source_identifier"
        if not decision.case_number:
            decision.case_number = extract_case_number(text)
        return decision
    except Exception:
        return decision


async def content_search(query: str, years: list[int], limit: int) -> list[Decision]:
    all_candidates: list[Decision] = []
    for year in years:
        try:
            all_candidates.extend(await get_year_links(year))
        except Exception:
            continue
    all_candidates = dedupe_decisions(all_candidates)
    by_year: dict[int, list[Decision]] = {year: [] for year in years}
    for item in all_candidates:
        item_year = year_from_url(item.url)
        if item_year in by_year and item.url.lower().split("?", 1)[0].endswith(".pdf"):
            by_year[item_year].append(item)
    per_year = max(1, MAX_CONTENT_CANDIDATES // max(1, len(years)))
    sampled: list[Decision] = []
    for year in years:
        sampled.extend(by_year.get(year, [])[:per_year])
    candidates = sampled[:MAX_CONTENT_CANDIDATES]
    semaphore = asyncio.Semaphore(8)

    async def one(item: Decision) -> Decision:
        async with semaphore:
            return await read_decision(item, query)

    results = await asyncio.gather(*(one(item) for item in candidates))
    results = [r for r in results if r.relevance_score > 0 and r.verified]
    results.sort(key=lambda r: (-r.relevance_score, r.citation or r.title))
    return results[:limit]


async def official_search(query: str, year: int | None, limit: int) -> list[Decision]:
    if year is not None:
        candidates = await get_year_links(year)
    else:
        html = await fetch_text(OFFICIAL_INDEX)
        candidates = parse_index(html, OFFICIAL_INDEX)
    terms = query_terms(query)
    scored: list[tuple[int, Decision]] = []
    for item in candidates:
        blob = normalize_text(f"{item.title} {item.citation} {item.case_number} {item.subject}")
        score = sum(1 for term in terms if normalize_text(term) in blob)
        if score:
            scored.append((score, item))
    if scored:
        return [item for _, item in sorted(scored, key=lambda pair: -pair[0])[:limit]]
    years = [year] if year is not None else [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
    return await content_search(query, years, limit)


async def citation_search(citation: str) -> list[Decision]:
    requested = normalize_citation(citation)
    if not requested:
        return []
    year_match = re.search(r"\b((?:19|20)\d{2})\b", requested)
    year = int(year_match.group(1)) if year_match else None
    results = await official_search(citation, year, MAX_RESULTS)
    return [r for r in results if r.citation and normalize_citation(r.citation) == requested and r.verified]


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 10) -> dict[str, Any]:
    """Busca sentencias y opiniones del Tribunal Supremo de Puerto Rico.

    Para consultas temáticas, intenta buscar dentro del texto de los PDFs oficiales.
    Devuelve solo documentos encontrados y verificables.
    """
    maximo = max(1, min(int(maximo), 20))
    try:
        results = await official_search(consulta, ano, maximo)
        return {
            "consulta": consulta,
            "ano": ano,
            "resultados": [asdict(r) for r in results],
            "fuente": OFFICIAL_INDEX,
            "regla_integridad": "Solo se devuelven documentos encontrados en fuentes permitidas; los campos no disponibles quedan vacíos.",
        }
    except Exception as exc:
        return {"error": "No fue posible consultar las fuentes públicas.", "detalle_tecnico": str(exc), "resultados": []}


@mcp.tool()
async def investigar_sentencias(consulta: str, anos: str = "2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015", maximo: int = 5) -> dict[str, Any]:
    """Encuentra autoridades potencialmente relevantes y verificables para una cuestión jurídica.

    Busca en el contenido de PDFs públicos del Tribunal Supremo, puntúa coincidencias
    textuales y devuelve cita TSPR, URL oficial, pasaje textual extraído y página
    cuando está disponible. El servidor NO decide que una sentencia 'apoya' una
    posición jurídica: entrega evidencia fuente para que el modelo la evalúe.
    """
    try:
        years = [int(x.strip()) for x in anos.split(",") if x.strip().isdigit()]
        years = list(dict.fromkeys(years))[:12] or [2026, 2025, 2024, 2023, 2022]
        maximo = max(1, min(int(maximo), 10))
        results = await content_search(consulta, years, maximo)
        return {
            "consulta": consulta,
            "anos_consultados": years,
            "resultados": [asdict(r) for r in results],
            "total": len(results),
            "verificacion": "Cada resultado incluye una URL de fuente permitida y fue leído desde el documento fuente; los pasajes no son generados por el modelo.",
            "limitacion": "La puntuación mide coincidencia textual/temática y no sustituye el análisis jurídico de holding, ratio decidendi o precedentes posteriores.",
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "total": 0, "error": "No fue posible completar la investigación documental.", "detalle_tecnico": str(exc)}


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
        return {"cita": cita, "encontrado": True, "verificado": True, "resultados": [asdict(r) for r in results]}
    except Exception as exc:
        return {"cita": cita, "encontrado": False, "verificado": False, "resultados": [], "error": "No fue posible verificar la cita.", "detalle_tecnico": str(exc)}


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_parrafos: int = 8) -> dict[str, Any]:
    """Lee una sentencia/documento público y devuelve pasajes extraídos de la fuente."""
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
            return {"url": url, "verificado": False, "error": "La fuente no contiene texto extraíble; no se generará contenido sustitutivo."}
        max_parrafos = max(1, min(int(max_parrafos), 30))
        relevantes = find_relevant_paragraphs(paragraphs, terminos, max_parrafos)
        return {
            "url": url,
            "fuente": source_name(url),
            "tipo_documento": document_type,
            "cita_tspr": extract_citation(text),
            "numero_caso": extract_case_number(text),
            "parrafos": relevantes,
            "total_parrafos_extraidos": len(paragraphs),
            "procedencia": "Texto extraído directamente del documento fuente; no generado por el modelo.",
            "verificado": True,
        }
    except Exception as exc:
        return {"error": "No fue posible leer o extraer el documento; no se hará ninguna inferencia sobre su contenido.", "detalle_tecnico": str(exc), "url": url, "verificado": False}


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Explica las fuentes y herramientas disponibles."""
    return {
        "consulta": consulta,
        "campo": campo,
        "fuentes": {"tribunal_supremo": OFFICIAL_INDEX, "lexjuris": LEXJURIS_SEARCH},
        "herramientas_recomendadas": {
            "investigar_sentencias": "Encontrar autoridades por el contenido de las sentencias.",
            "buscar_por_cita": "Verificar una cita TSPR exacta.",
            "leer_sentencia": "Recuperar pasajes y páginas directamente de una sentencia.",
        },
        "filtros": ["año", "cita TSPR", "número de caso", "términos del asunto"],
        "regla_integridad": "Si una autoridad o cita no se encuentra en una fuente permitida, se informa como no encontrada.",
    }


@mcp.tool()
def estado() -> dict[str, Any]:
    """Devuelve diagnóstico y garantías de integridad."""
    return {
        "servidor": "puerto-rico-sentencias",
        "version": "1.0.0",
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
        "documentos": {"pdf": True, "html": True, "pasajes_con_procedencia": True, "pagina_pdf": True},
        "privacidad": "No se almacenan consultas ni documentos por defecto.",
        "anti_bot": "No se eluden CAPTCHA, autenticación ni controles de acceso.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
