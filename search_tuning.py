"""Runtime tuning for relevance-first TSPR discovery.

This module improves recall for doctrinally phrased legal questions whose best
cases may be catalogued under a related doctrine rather than the user's exact
facts. It also caps the expensive official-PDF verification phase so a failed
search does not run for many minutes.

The secondary discovery index remains discovery-only. Final authorities still
must pass the existing official Poder Judicial verification path in
``smart_server``.
"""
from __future__ import annotations

import re

import server as jurisprudencia
import smart_server

# Expansions are intentionally doctrinal, not case-specific. They help bridge
# factual phrasing (e.g. confianza -> carrera) to the doctrinal labels often
# used in public case indexes (e.g. debido proceso, planes de clasificación).
_DOCTRINAL_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "empleado de confianza": (
        "servicio de carrera",
        "empleado de carrera",
        "debido proceso de ley",
        "interes propietario",
        "derecho propietario",
        "principio de merito",
        "planes de clasificacion",
        "retribucion",
        "reglamento de personal",
    ),
    "empleado confianza": (
        "servicio de carrera",
        "empleado de carrera",
        "debido proceso de ley",
        "interes propietario",
        "principio de merito",
    ),
    "reinstalacion": (
        "reinstalacion",
        "reposicion",
        "reingreso",
        "servicio de carrera",
        "empleado de carrera",
        "remedio",
    ),
    "derecho propietario": (
        "interes propietario",
        "interes de propiedad",
        "debido proceso de ley",
        "derecho adquirido",
    ),
    "derecho probatorio": (
        "presuncion",
        "carga de la prueba",
        "evidencia",
        "debido proceso de ley",
    ),
    "reglamento": (
        "facultad reglamentaria",
        "agencia obligada a seguir su reglamento",
        "debido proceso de ley",
        "ultra vires",
        "error administrativo",
        "reglamento de personal",
    ),
    "carrera": (
        "servicio de carrera",
        "empleado de carrera",
        "principio de merito",
        "personal publico",
        "planes de clasificacion",
    ),
    "derecho administrativo": (
        "agencia administrativa",
        "debido proceso de ley",
        "facultad reglamentaria",
        "revision judicial",
        "ultra vires",
    ),
}


def expanded_query_terms(query: str) -> list[tuple[str, float]]:
    """Return original and doctrinally-expanded search terms with weights."""
    normalized = jurisprudencia.normalize_text(query or "")
    weighted: dict[str, float] = {}

    for term in jurisprudencia.query_terms(query):
        nt = jurisprudencia.normalize_text(term)
        if nt:
            weighted[nt] = max(weighted.get(nt, 0.0), 1.0)

    for trigger, expansions in _DOCTRINAL_EXPANSIONS.items():
        if jurisprudencia.normalize_text(trigger) not in normalized:
            continue
        for term in expansions:
            nt = jurisprudencia.normalize_text(term)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.72)

    return sorted(weighted.items(), key=lambda item: (-item[1], item[0]))


def improved_discovery_score(blob: str, query: str) -> float:
    """Score public index metadata using exact + doctrinally-related concepts.

    Expanded concepts only influence which candidates get opened. They never
    make a case verified or relevant on their own.
    """
    normalized = jurisprudencia.normalize_text(blob or "")
    query_norm = jurisprudencia.normalize_text(query or "")
    score = 0.0

    if query_norm and len(query_norm) >= 6 and query_norm in normalized:
        score += 12.0

    for term, weight in expanded_query_terms(query):
        if not term:
            continue
        count = min(normalized.count(term), 5)
        if not count:
            continue
        phrase_bonus = 2.5 if " " in term else 1.0
        score += weight * (phrase_bonus + min(count, 3) * 0.8)

    # Give a small bonus when multiple distinct doctrinal concepts co-occur in
    # the same public catalog entry. This helps surface doctrinal cases whose
    # matter label differs from the user's factual wording.
    matched = 0
    for term, _weight in expanded_query_terms(query):
        if term and term in normalized:
            matched += 1
    if matched >= 3:
        score += min(4.0, (matched - 2) * 0.8)

    return round(score, 2)


def faster_minimum_verifications(maximo: int) -> int:
    """Require a meaningful sample without forcing 25+ PDF reads for Top-5."""
    requested = max(1, int(maximo))
    target = max(smart_server.VERIFY_BATCH_SIZE * 2, requested * 3)
    return min(smart_server.MAX_OFFICIAL_VERIFICATIONS, target)


# Apply tuning to the already-registered relevance loop. Python resolves these
# globals at call time, so existing MCP tools automatically use the tuned logic.
smart_server._discovery_score = improved_discovery_score
smart_server._minimum_verifications_before_stability = faster_minimum_verifications
smart_server.VERIFY_BATCH_SIZE = 5
smart_server.VERIFY_CONCURRENCY = 5
smart_server.MAX_OFFICIAL_VERIFICATIONS = 24
smart_server.STABLE_ROUNDS_REQUIRED = 1
