"""Verified search for public JRT decisions and orders.

The JRT public references page exposes direct PDFs through the Government of
Puerto Rico document repository (docs.pr.gov).  This module discovers across
its public Webflow pagination, ranks cheaply by visible metadata, then reads a
bounded set of official PDFs and keeps only source-text matches.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import authority_reader
import research_server
import server as jurisprudencia

mcp = research_server.mcp

JRT_REFERENCES = "https://www.jrt.pr.gov/referencias"
JRT_DECISIONS_PAGE_PARAM = "06e7e024_page"
MAX_JRT_PAGES = 25
JRT_PAGE_CONCURRENCY = 7
JRT_VERIFY_CONCURRENCY = 4
MAX_JRT_DOCUMENT_VERIFICATIONS = 18


@dataclass
class JRTCandidate:
    title: str
    url: str
    page: int
    metadata_score: int
    kind: str


def _kind_from_candidate(title: str, url: str) -> str:
    low = f"{title} {url}".lower()
    if "avisosdesestimacion" in low or "aviso de desestim" in low:
        return "aviso_desestimacion"
    if "resoluci" in low and "administrativa" in low:
        return "resolucion_administrativa"
    if "orden administrativa" in low:
        return "orden_administrativa"
    return "decision_y_orden"


def _is_jrt_document_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host in {"docs.pr.gov", "www.docs.pr.gov"} and "/jrt/" in url.lower()
    except Exception:
        return False


def _metadata_score(title: str, query: str) -> int:
    normalized = jurisprudencia.normalize_text(title)
    terms = jurisprudencia.query_terms(query)
    score = 0
    q = jurisprudencia.normalize_text(query)
    if q and q in normalized:
        score += 10
    for term in terms:
        nt = jurisprudencia.normalize_text(term)
        if nt and nt in normalized:
            score += 3 if " " in nt else 1
    return score


def _parse_jrt_reference_page(html: str, query: str, page: int) -> list[JRTCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[JRTCandidate] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = anchor["href"]
        if url.startswith("//"):
            url = "https:" + url
        if not _is_jrt_document_url(url) or url in seen:
            continue
        title = jurisprudencia.clean(anchor.get_text(" ", strip=True))
        if not title:
            continue
        seen.add(url)
        out.append(
            JRTCandidate(
                title=title,
                url=url,
                page=page,
                metadata_score=_metadata_score(title, query),
                kind=_kind_from_candidate(title, url),
            )
        )
    return out


async def _fetch_jrt_page(page: int, query: str) -> list[JRTCandidate]:
    url = f"{JRT_REFERENCES}?{JRT_DECISIONS_PAGE_PARAM}={page}"
    try:
        client = await jurisprudencia.get_http_client()
        response = await client.get(url)
        response.raise_for_status()
        return _parse_jrt_reference_page(response.text, query, page)
    except Exception:
        return []


async def _discover_jrt_candidates(query: str, paginas: int = MAX_JRT_PAGES) -> list[JRTCandidate]:
    paginas = max(1, min(int(paginas), MAX_JRT_PAGES))
    semaphore = asyncio.Semaphore(JRT_PAGE_CONCURRENCY)

    async def one(page: int) -> list[JRTCandidate]:
        async with semaphore:
            return await _fetch_jrt_page(page, query)

    batches = await asyncio.gather(*(one(page) for page in range(1, paginas + 1)))
    merged: dict[str, JRTCandidate] = {}
    for batch in batches:
        for item in batch:
            current = merged.get(item.url)
            if current is None or item.metadata_score > current.metadata_score:
                merged[item.url] = item
    return sorted(merged.values(), key=lambda x: (-x.metadata_score, x.title))


def _verification_batch(candidates: list[JRTCandidate]) -> list[JRTCandidate]:
    strong = [c for c in candidates if c.metadata_score > 0]
    weak = [c for c in candidates if c.metadata_score <= 0]
    batch = strong[:MAX_JRT_DOCUMENT_VERIFICATIONS]
    if len(batch) < MAX_JRT_DOCUMENT_VERIFICATIONS:
        batch += jurisprudencia.sample_evenly(
            weak, MAX_JRT_DOCUMENT_VERIFICATIONS - len(batch)
        )
    return batch


def _verified_document_score(candidate: JRTCandidate, read: dict[str, Any]) -> float:
    passages = read.get("pasajes", []) if isinstance(read, dict) else []
    hits = sum(int(p.get("coincidencias", 0) or 0) for p in passages if isinstance(p, dict))
    return round(candidate.metadata_score * 2.0 + hits * 4.0 + min(len(passages), 4), 2)


async def search_jrt_fulltext(query: str, maximo: int = 5, paginas: int = MAX_JRT_PAGES) -> dict[str, Any]:
    """Discover JRT records broadly and verify relevance in official PDFs."""
    maximo = max(1, min(int(maximo), 10))
    candidates = await _discover_jrt_candidates(query, paginas)
    batch = _verification_batch(candidates)
    semaphore = asyncio.Semaphore(JRT_VERIFY_CONCURRENCY)

    async def verify(candidate: JRTCandidate):
        async with semaphore:
            result = await authority_reader.read_public_authority(candidate.url, query, max_pasajes=6)
            return candidate, result

    checked = await asyncio.gather(*(verify(c) for c in batch))
    verified: list[dict[str, Any]] = []
    for candidate, read in checked:
        if not isinstance(read, dict) or not read.get("verificado"):
            continue
        if not read.get("coincidencia_tematica_verificada"):
            continue
        passages = read.get("pasajes", [])
        verified.append({
            "tipo_autoridad": "decision_administrativa_laboral",
            "subtipo": candidate.kind,
            "titulo": candidate.title,
            "url": candidate.url,
            "fuente": "Junta de Relaciones del Trabajo de Puerto Rico / docs.pr.gov",
            "nivel_fuente": "fuente_primaria_oficial",
            "estado_verificacion": "texto_fuente_primaria_verificado",
            "puede_citarse_como_proposicion_juridica": True,
            "pasajes": passages,
            "ranking_relevancia": _verified_document_score(candidate, read),
            "pagina_indice_jrt": candidate.page,
            "advertencia": read.get("advertencia"),
        })

    verified.sort(key=lambda row: (-float(row["ranking_relevancia"]), row["titulo"]))
    return {
        "consulta": query,
        "estrategia": "jrt_global_index_then_official_pdf_verification",
        "paginas_indice_exploradas": max(1, min(int(paginas), MAX_JRT_PAGES)),
        "candidatos_descubiertos": len(candidates),
        "documentos_oficiales_verificados": len(batch),
        "resultados": verified[:maximo],
        "total": min(len(verified), maximo),
        "fuente_indice": JRT_REFERENCES,
        "integridad": (
            "Los títulos/enlaces sirven para descubrimiento. Cada resultado final exige lectura del PDF alojado en docs.pr.gov "
            "y un pasaje que coincida con la consulta. No se infiere vigencia ni tratamiento judicial posterior."
        ),
    }


@mcp.tool()
async def buscar_decisiones_laborales_verificables(
    consulta: str, maximo: int = 5, paginas: int = MAX_JRT_PAGES
) -> dict[str, Any]:
    """Busca decisiones/órdenes de la JRT y verifica la relevancia en sus PDFs oficiales."""
    return await search_jrt_fulltext(consulta, maximo, paginas)
