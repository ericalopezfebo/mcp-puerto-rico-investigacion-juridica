"""Relevance-first MCP layer for Puerto Rico legal research.

This module extends ``research_server`` without replacing its verified-source
core.  The main addition is a server-side research loop for requests such as
"find the best five TSPR decisions for this argument".

The loop does NOT walk years newest-to-oldest.  It first builds a global
candidate pool from public, non-paywalled LexJuris year menus (used only as a
secondary discovery index), ranks candidates by topical signal, then verifies
and re-ranks only the strongest candidates against the official Poder Judicial
PDFs.  Final authorities are returned only when official verification succeeds.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import research_server
import server as jurisprudencia

mcp = research_server.mcp

LEXJURIS_PUBLIC_YEAR = "https://www.lexjuris.com/LexJuris/tspr{year}/lexj{year}Menu.htm"
MIN_PUBLIC_DISCOVERY_YEAR = 1997
DISCOVERY_CONCURRENCY = 8
VERIFY_CONCURRENCY = 5
VERIFY_BATCH_SIZE = 6
MAX_OFFICIAL_VERIFICATIONS = 36
STABLE_ROUNDS_REQUIRED = 2


@dataclass
class DiscoveryCandidate:
    citation: str
    year: int
    title: str
    context: str
    discovery_url: str
    discovery_score: float
    discovered_by: str = "lexjuris_public_year_menu"


def _citation_key(value: str) -> str:
    return jurisprudencia.normalize_citation(value)


def _all_tspr_citations(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for year, number in re.findall(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I):
        citation = f"{year} TSPR {int(number)}"
        key = _citation_key(citation)
        if key not in seen:
            seen.add(key)
            out.append(citation)
    return out


def _discovery_score(blob: str, query: str) -> float:
    """Cheap topical score used only to decide which official PDFs to verify.

    It never establishes legal relevance by itself.  There is deliberately no
    recency/year bonus: a 2001 case can outrank a 2026 case if its public matter
    and summary match the legal issue more closely.
    """
    normalized = jurisprudencia.normalize_text(blob)
    query_norm = jurisprudencia.normalize_text(query)
    terms = jurisprudencia.query_terms(query)
    score = 0.0
    if query_norm and len(query_norm) >= 6 and query_norm in normalized:
        score += 12.0
    for term in terms:
        nt = jurisprudencia.normalize_text(term)
        if not nt:
            continue
        count = min(normalized.count(nt), 5)
        if count:
            phrase_bonus = 2.5 if " " in nt else 1.0
            score += phrase_bonus + min(count, 3) * 0.8
    return round(score, 2)


def _parse_lexjuris_year_menu(html: str, year: int, query: str, base_url: str) -> list[DiscoveryCandidate]:
    """Parse public year-menu entries containing matter/summary text.

    LexJuris is discovery-only here.  Nothing parsed by this function is
    returned as verified authority until ``citation_search`` confirms the exact
    citation against the official Poder Judicial source and reads its PDF.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[DiscoveryCandidate] = []
    seen: set[str] = set()
    citation_re = re.compile(rf"\b{year}\s*TSPR\s*0*(\d{{1,4}})\b", re.I)

    for anchor in soup.find_all("a", href=True):
        title = jurisprudencia.clean(anchor.get_text(" ", strip=True))
        parent_text = jurisprudencia.clean(anchor.parent.get_text(" ", strip=True)) if anchor.parent else title
        haystack = f"{title} {parent_text}"
        match = citation_re.search(haystack.replace("TSPR0", "TSPR "))
        if not match:
            compact = re.search(rf"\b{year}TSPR0*(\d{{1,4}})\b", haystack, re.I)
            if not compact:
                continue
            number = int(compact.group(1))
        else:
            number = int(match.group(1))

        citation = f"{year} TSPR {number}"
        key = _citation_key(citation)
        if key in seen:
            continue

        context_parts = [parent_text]
        node = anchor.parent
        for _ in range(3):
            if not node:
                break
            node = node.find_next_sibling()
            if not node:
                break
            text = jurisprudencia.clean(node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node))
            if text:
                if re.search(rf"\b{year}\s*(?:DTS|TSPR)\s*\d+", text, re.I):
                    break
                context_parts.append(text)
        context = jurisprudencia.clean(" ".join(context_parts))[:2200]
        score = _discovery_score(f"{title} {context}", query)
        if score <= 0:
            continue

        href = urljoin(base_url, anchor["href"])
        seen.add(key)
        results.append(
            DiscoveryCandidate(
                citation=citation,
                year=year,
                title=title,
                context=context,
                discovery_url=href,
                discovery_score=score,
            )
        )

    results.sort(key=lambda c: (-c.discovery_score, c.citation))
    return results


async def _fetch_public_year_candidates(year: int, query: str) -> list[DiscoveryCandidate]:
    if year < MIN_PUBLIC_DISCOVERY_YEAR:
        return []
    url = LEXJURIS_PUBLIC_YEAR.format(year=year)
    try:
        response = await jurisprudencia.fetch_response(url)
        return _parse_lexjuris_year_menu(response.text, year, query, url)
    except Exception:
        return []


async def _global_discovery(query: str, years: list[int]) -> list[DiscoveryCandidate]:
    semaphore = asyncio.Semaphore(DISCOVERY_CONCURRENCY)

    async def one(year: int) -> list[DiscoveryCandidate]:
        async with semaphore:
            return await _fetch_public_year_candidates(year, query)

    batches = await asyncio.gather(*(one(y) for y in years))
    merged: dict[str, DiscoveryCandidate] = {}
    for batch in batches:
        for candidate in batch:
            key = _citation_key(candidate.citation)
            current = merged.get(key)
            if current is None or candidate.discovery_score > current.discovery_score:
                merged[key] = candidate
    return sorted(merged.values(), key=lambda c: (-c.discovery_score, c.citation))


def _verified_rank(decision: jurisprudencia.Decision, discovery_score: float, query: str) -> float:
    """Rank verified decisions without a recency bonus.

    Source-text relevance dominates discovery metadata.  Explicitly tangential
    language is penalized.  This is a ranking aid, not a holding classifier.
    """
    snippet = jurisprudencia.normalize_text(decision.snippet)
    score = float(decision.relevance_score) * 4.0 + float(discovery_score)
    query_norm = jurisprudencia.normalize_text(query)
    if query_norm and query_norm in snippet:
        score += 8.0
    if any(phrase in snippet for phrase in (
        "no es relevante para la controversia",
        "no son relevantes para la controversia",
        "no guarda relacion con la controversia",
    )):
        score -= 18.0
    if "denegando la expedicion del auto" in snippet or "denego la expedicion del auto" in snippet:
        score -= 4.0
    return round(score, 2)


async def _verify_candidate(candidate: DiscoveryCandidate, query: str) -> tuple[jurisprudencia.Decision | None, float]:
    matches = await jurisprudencia.citation_search(candidate.citation)
    if not matches:
        return None, 0.0
    decision = matches[0]
    # citation_search verifies the exact official citation and reads the source,
    # but an empty query does not create a topical snippet. Re-read the verified
    # official document with the user's issue solely for relevance extraction.
    decision = await jurisprudencia.read_decision(decision, query)
    if not decision.verified or not jurisprudencia._document_relevance_confirmed(decision, query):
        return None, 0.0
    return decision, _verified_rank(decision, candidate.discovery_score, query)


async def relevance_first_search(
    query: str,
    maximo: int = 5,
    ano_desde: int = MIN_PUBLIC_DISCOVERY_YEAR,
    ano_hasta: int = 2026,
) -> dict[str, Any]:
    """Server-side retrieval/evaluation loop for globally ranked TSPR research."""
    maximo = max(1, min(int(maximo), 10))
    ano_desde = max(MIN_PUBLIC_DISCOVERY_YEAR, int(ano_desde))
    ano_hasta = max(ano_desde, min(int(ano_hasta), 2100))
    years = list(range(ano_desde, ano_hasta + 1))

    candidates = await _global_discovery(query, years)
    queue: list[DiscoveryCandidate] = list(candidates)
    queued = {_citation_key(c.citation) for c in queue}
    verified: dict[str, tuple[jurisprudencia.Decision, float, DiscoveryCandidate]] = {}
    verifications = 0
    rounds = 0
    stable_rounds = 0
    previous_top: tuple[str, ...] = ()

    while queue and verifications < MAX_OFFICIAL_VERIFICATIONS:
        rounds += 1
        batch = queue[:VERIFY_BATCH_SIZE]
        queue = queue[VERIFY_BATCH_SIZE:]
        remaining_budget = MAX_OFFICIAL_VERIFICATIONS - verifications
        batch = batch[:remaining_budget]
        semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

        async def one(candidate: DiscoveryCandidate):
            async with semaphore:
                return candidate, await _verify_candidate(candidate, query)

        checked = await asyncio.gather(*(one(c) for c in batch))
        verifications += len(batch)

        for candidate, (decision, score) in checked:
            if decision is None:
                continue
            key = _citation_key(decision.citation or candidate.citation)
            current = verified.get(key)
            if current is None or score > current[1]:
                verified[key] = (decision, score, candidate)

            # Citation chaining: citations appearing in the exact relevant
            # passage become additional candidates. They are still required to
            # pass exact official verification before they can rank.
            for cited in _all_tspr_citations(decision.snippet):
                cited_key = _citation_key(cited)
                if cited_key in queued or cited_key in verified:
                    continue
                year_match = re.match(r"((?:19|20)\d{2})", cited)
                if not year_match:
                    continue
                cited_year = int(year_match.group(1))
                queued.add(cited_key)
                queue.append(
                    DiscoveryCandidate(
                        citation=cited,
                        year=cited_year,
                        title=f"Citada por {decision.citation}",
                        context=decision.snippet,
                        discovery_url=decision.url,
                        discovery_score=max(1.0, candidate.discovery_score * 0.75),
                        discovered_by="citation_chain",
                    )
                )

        ranked = sorted(verified.values(), key=lambda item: (-item[1], item[0].citation or item[0].title))
        top_keys = tuple(_citation_key(item[0].citation) for item in ranked[:maximo])
        if len(top_keys) >= maximo and top_keys == previous_top:
            stable_rounds += 1
        else:
            stable_rounds = 0
        previous_top = top_keys

        if len(top_keys) >= maximo and stable_rounds >= STABLE_ROUNDS_REQUIRED:
            break

    ranked = sorted(verified.values(), key=lambda item: (-item[1], item[0].citation or item[0].title))[:maximo]
    resultados: list[dict[str, Any]] = []
    for decision, score, candidate in ranked:
        row = asdict(decision)
        row["ranking_relevancia"] = score
        row["descubierto_por"] = candidate.discovered_by
        row["fuente_descubrimiento"] = "LexJuris público" if candidate.discovered_by == "lexjuris_public_year_menu" else "cita dentro de autoridad verificada"
        row["verificacion_final"] = "Poder Judicial de Puerto Rico — documento oficial"
        resultados.append(row)

    return {
        "consulta": query,
        "estrategia": "relevance_first_global_loop",
        "orden": "relevancia verificada; sin bono por recencia",
        "anos_descubrimiento": [ano_desde, ano_hasta],
        "candidatos_globales": len(candidates),
        "documentos_oficiales_verificados": verifications,
        "rondas": rounds,
        "ranking_estabilizado": stable_rounds >= STABLE_ROUNDS_REQUIRED,
        "resultados": resultados,
        "total": len(resultados),
        "integridad": (
            "LexJuris público se usa solo para descubrir y priorizar candidatos. "
            "Cada resultado final exige coincidencia exacta de cita y lectura del documento oficial del Poder Judicial."
        ),
        "cobertura": (
            "El índice público de descubrimiento cubre 1997 en adelante. Autoridades anteriores pueden aparecer solo si son descubiertas por referencias verificables; "
            "esta versión no afirma cobertura exhaustiva pre-1997."
        ),
    }


@mcp.tool()
async def buscar_mejores_sentencias(
    argumento: str,
    maximo: int = 5,
    ano_desde: int = MIN_PUBLIC_DISCOVERY_YEAR,
    ano_hasta: int = 2026,
) -> dict[str, Any]:
    """Busca las mejores decisiones TSPR para un argumento mediante un loop interno.

    USA ESTA HERRAMIENTA cuando el usuario pida "las mejores", "más relevantes"
    o "Top N" decisiones del Tribunal Supremo para apoyar, refutar o investigar
    un argumento. No busca año por año ni favorece casos recientes: crea primero
    un pool global de candidatos, verifica los mejores contra los PDFs oficiales,
    reordena por relevancia del texto fuente y sigue iterando hasta estabilizar
    el Top-K o agotar un presupuesto conservador. Puede devolver menos resultados
    si no hay suficientes autoridades verificables.
    """
    return await relevance_first_search(argumento, maximo, ano_desde, ano_hasta)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
