"""Runtime resilience layer: local corpus first, live network second.

Imported after ``search_tuning`` so it wraps the final doctrine-aware discovery
and verification functions. This prevents a slow or unavailable public website
from making the entire MCP return zero candidates.
"""
from __future__ import annotations

import asyncio

import corpus_index
import smart_server

_LOCAL_DISCOVERY_SUFFICIENT = 3
_LIVE_DISCOVERY_TIMEOUT = 8.0
_LIVE_VERIFY_TIMEOUT = 7.0

_live_global_discovery = smart_server._global_discovery
_live_verify_candidate = smart_server._verify_candidate
_live_relevance_search = smart_server.relevance_first_search


def _local_candidates(query: str, years: list[int]) -> list[smart_server.DiscoveryCandidate]:
    out: list[smart_server.DiscoveryCandidate] = []
    for record, score in corpus_index.search_corpus(query, years=years, limit=100):
        out.append(
            smart_server.DiscoveryCandidate(
                citation=record.citation,
                year=record.year,
                title=record.title,
                context=" ".join((record.subject, record.excerpt, " ".join(record.concepts))),
                discovery_url=record.url,
                discovery_score=score,
                discovered_by="local_primary_source_corpus",
            )
        )
    return out


async def corpus_first_global_discovery(query: str, years: list[int]) -> list[smart_server.DiscoveryCandidate]:
    """Search the persistent corpus instantly; use live discovery only as expansion."""
    local = _local_candidates(query, years)
    if len(local) >= _LOCAL_DISCOVERY_SUFFICIENT:
        return sorted(local, key=smart_server._queue_sort_key)

    live: list[smart_server.DiscoveryCandidate] = []
    try:
        live = await asyncio.wait_for(
            _live_global_discovery(query, years), timeout=_LIVE_DISCOVERY_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError, Exception):
        live = []

    merged: dict[str, smart_server.DiscoveryCandidate] = {}
    for candidate in [*local, *live]:
        key = smart_server._citation_key(candidate.citation)
        current = merged.get(key)
        if current is None or candidate.discovery_score > current.discovery_score:
            merged[key] = candidate
    return sorted(merged.values(), key=smart_server._queue_sort_key)


async def resilient_verify_candidate(candidate: smart_server.DiscoveryCandidate, query: str):
    """Prefer live official verification, then degrade to a cached official excerpt.

    The fallback is only available for records whose provenance says they were
    captured from an official primary-source document. The returned status makes
    the distinction explicit; it never claims a fresh live verification.
    """
    try:
        decision, score = await asyncio.wait_for(
            _live_verify_candidate(candidate, query), timeout=_LIVE_VERIFY_TIMEOUT
        )
        if decision is not None:
            return decision, score
    except (TimeoutError, asyncio.TimeoutError, Exception):
        pass

    if candidate.discovered_by != "local_primary_source_corpus":
        return None, 0.0

    cached = corpus_index.cached_decision(candidate.citation, query)
    if cached is None:
        return None, 0.0
    score = smart_server._verified_rank(cached, candidate.discovery_score, query)
    return cached, max(score, candidate.discovery_score)


async def corpus_aware_relevance_search(*args, **kwargs):
    result = await _live_relevance_search(*args, **kwargs)
    if not isinstance(result, dict):
        return result
    rows = result.get("resultados", [])
    cached_count = 0
    local_count = 0
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        if row.get("descubierto_por") == "local_primary_source_corpus":
            local_count += 1
            row["fuente_descubrimiento"] = "corpus local construido desde fuente primaria oficial"
        status = str(row.get("verification_status", ""))
        if status.startswith("cached_official"):
            cached_count += 1
            row["verificacion_final"] = (
                "copia/extracto previamente capturado del documento oficial; "
                "verificacion en vivo no disponible en esta llamada"
            )
        else:
            row["verificacion_final"] = "Poder Judicial de Puerto Rico — verificación en vivo"
    result["estrategia"] = "persistent_corpus_first_then_live_verification"
    result["candidatos_desde_corpus_local"] = local_count
    result["resultados_con_fallback_cache_oficial"] = cached_count
    result["integridad"] = (
        "El corpus local contiene únicamente metadatos/extractos capturados previamente desde fuentes primarias. "
        "Se prefiere verificación en vivo; si falla la red, el estado cached_official_* se informa expresamente y no se presenta como verificación fresca."
    )
    return result


smart_server._global_discovery = corpus_first_global_discovery
smart_server._verify_candidate = resilient_verify_candidate
smart_server.relevance_first_search = corpus_aware_relevance_search
