"""Runtime tuning for relevance-first TSPR discovery.

This module improves recall for doctrinally phrased legal questions whose best
cases may be catalogued under a related doctrine rather than the user's exact
facts. It also caps the expensive official-PDF verification phase so a failed
search does not run for many minutes.

The secondary discovery index remains discovery-only. Final authorities still
must pass exact citation lookup and official Poder Judicial PDF verification.
"""
from __future__ import annotations

import copy

import server as jurisprudencia
import smart_server

# Expansions are intentionally doctrinal, not case-specific. They help bridge
# factual phrasing to doctrinal labels often used in public case indexes.
_DOCTRINAL_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "empleado de confianza": (
        "servicio de carrera", "empleado de carrera", "debido proceso de ley",
        "interes propietario", "derecho propietario", "principio de merito",
        "planes de clasificacion", "retribucion", "reglamento de personal",
    ),
    "empleado confianza": (
        "servicio de carrera", "empleado de carrera", "debido proceso de ley",
        "interes propietario", "principio de merito",
    ),
    "reinstalacion": (
        "reinstalacion", "reposicion", "reingreso", "servicio de carrera",
        "empleado de carrera", "remedio",
    ),
    "derecho propietario": (
        "interes propietario", "interes de propiedad", "debido proceso de ley",
        "derecho adquirido",
    ),
    "derecho probatorio": (
        "presuncion", "carga de la prueba", "evidencia", "debido proceso de ley",
    ),
    "reglamento": (
        "facultad reglamentaria", "agencia obligada a seguir su reglamento",
        "derechos establecidos en reglamento", "debido proceso de ley", "ultra vires",
        "error administrativo", "reglamento de personal",
    ),
    "carrera": (
        "servicio de carrera", "empleado de carrera", "principio de merito",
        "personal publico", "planes de clasificacion",
    ),
    "derecho administrativo": (
        "agencia administrativa", "debido proceso de ley", "facultad reglamentaria",
        "revision judicial", "ultra vires",
    ),
    # Regla 21 / intervención. These terms describe the doctrine generically;
    # no case name or citation is encoded here.
    "interventor": (
        "intervencion", "intervencion de terceros", "parte interventora", "regla 21",
        "intervencion como cuestion de derecho", "intervencion permisible",
        "interes que amerite proteccion", "interes afectado", "representacion adecuada",
        "derecho o interes en la propiedad", "asunto objeto del litigio", "economia procesal",
        "tercero", "terceria", "regla 21.1", "regla 21.2", "regla 21.4", "regla 21.5",
        "dilacion", "perjuicio a las partes originales",
    ),
    "intervencion": (
        "interventor", "intervencion de terceros", "parte interventora", "regla 21",
        "intervencion como cuestion de derecho", "intervencion permisible",
        "interes que amerite proteccion", "interes afectado", "representacion adecuada",
        "derecho o interes en la propiedad", "asunto objeto del litigio", "economia procesal",
        "tercero", "terceria", "regla 21.1", "regla 21.2", "regla 21.4", "regla 21.5",
    ),
    "regla 21": (
        "interventor", "intervencion de terceros", "parte interventora",
        "intervencion como cuestion de derecho", "intervencion permisible",
        "interes que amerite proteccion", "interes afectado", "representacion adecuada",
        "economia procesal", "regla 21.1", "regla 21.2", "regla 21.4", "regla 21.5",
    ),
}

_INTERVENTION_QUERY_TRIGGERS = (
    "interventor", "intervencion", "parte interventora", "regla 21",
    "intervencion de terceros", "intervencion permisible", "intervencion como cuestion de derecho",
)

# Common false senses of the word "intervención" that should not dominate a
# Regla 21 civil-procedure query merely because they share the same surface word.
_INTERVENTION_FALSE_SENSES = (
    "intervencion policial", "intervencion policiaca", "intervencion de la policia",
    "intervencion apelativa", "intervencion del tribunal de apelaciones",
    "intervencion de abogado", "intervencion del abogado", "intervencion de letrado",
    "solicitud de intervencion ante la agencia", "intervencion administrativa bajo la lpau",
    "intervencion de procurador", "intervencion del procurador",
)


def _is_rule21_query(query: str) -> bool:
    normalized = jurisprudencia.normalize_text(query or "")
    return any(jurisprudencia.normalize_text(term) in normalized for term in _INTERVENTION_QUERY_TRIGGERS)


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

    terms = expanded_query_terms(query)
    for term, weight in terms:
        if not term:
            continue
        count = min(normalized.count(term), 5)
        if not count:
            continue
        phrase_bonus = 2.5 if " " in term else 1.0
        score += weight * (phrase_bonus + min(count, 3) * 0.8)

    matched = sum(1 for term, _weight in terms if term and term in normalized)
    if matched >= 3:
        score += min(6.0, (matched - 2) * 1.0)

    bridge_sets = (
        ("debido proceso de ley", "planes de clasificacion"),
        ("debido proceso de ley", "retribucion"),
        ("reglamento de personal", "debido proceso de ley"),
        ("servicio de carrera", "principio de merito"),
        # Generic Regla 21 bridges.
        ("regla 21", "interes afectado"),
        ("regla 21", "representacion adecuada"),
        ("intervencion como cuestion de derecho", "interes que amerite proteccion"),
        ("intervencion permisible", "economia procesal"),
    )
    available = {term for term, _weight in terms}
    for left, right in bridge_sets:
        if left in available and right in available and left in normalized and right in normalized:
            score += 8.0

    if _is_rule21_query(query):
        false_hits = sum(
            1 for phrase in _INTERVENTION_FALSE_SENSES
            if jurisprudencia.normalize_text(phrase) in normalized
        )
        # A false-sense marker is not an absolute exclusion: a case could discuss
        # both doctrines. It is a strong ranking penalty unless Rule 21-specific
        # concepts also appear in the same catalog text.
        rule21_signals = sum(
            1 for phrase in (
                "regla 21", "intervencion de terceros", "parte interventora",
                "interes afectado", "representacion adecuada", "economia procesal",
                "intervencion como cuestion de derecho", "intervencion permisible",
            )
            if jurisprudencia.normalize_text(phrase) in normalized
        )
        if false_hits and rule21_signals == 0:
            score -= min(24.0, false_hits * 12.0)

    return round(max(0.0, score), 2)


def doctrinal_verification_queries(query: str) -> list[str]:
    """Create focused legal-doctrine queries for reading an official PDF."""
    normalized = jurisprudencia.normalize_text(query or "")
    queries = [query]

    def add(value: str) -> None:
        key = jurisprudencia.normalize_text(value)
        if key and all(jurisprudencia.normalize_text(q) != key for q in queries):
            queries.append(value)

    if "reglamento" in normalized:
        add("agencia obligada a seguir su reglamento debido proceso derechos establecidos reglamento")
        add("reglamento crea derecho concreto derecho propietario interes propietario")
        add("reglamento error administrativo ultra vires derechos reconocidos")
    if "confianza" in normalized or "carrera" in normalized:
        add("empleado de confianza servicio de carrera empleado de carrera principio de merito")
        add("planes de clasificacion retribucion debido proceso servicio de carrera")
    if "reinstal" in normalized or "reposicion" in normalized or "reingreso" in normalized:
        add("reinstalacion reposicion reingreso empleado de carrera remedio")
    if "derecho propietario" in normalized or "interes propietario" in normalized:
        add("interes propietario derecho propietario debido proceso derecho adquirido")
    if "derecho administrativo" in normalized:
        add("derecho administrativo agencia reglamento debido proceso facultad reglamentaria")

    if _is_rule21_query(query):
        # Separate the doctrine into sub-issues so a controlling case can verify
        # even if one paragraph does not contain every part of the user's prompt.
        add("regla 21 intervencion de terceros interventor definicion proposito economia procesal")
        add("regla 21.1 intervencion como cuestion de derecho interes que amerite proteccion interes afectado")
        add("regla 21.2 intervencion permisible dilacion perjuicio partes originales")
        add("disposicion del pleito pueda afectar en la practica interes interventor representacion adecuada")
        add("regla 21.4 regla 21.5 parte interventora requisitos procedimiento intervencion")

    return queries[:9]


async def doctrine_aware_verify_candidate(
    candidate: smart_server.DiscoveryCandidate,
    query: str,
):
    """Verify one candidate with exact citation + multiple focused PDF reads."""
    matches = await jurisprudencia.citation_search(candidate.citation)
    if not matches:
        return None, 0.0

    base = matches[0]
    best_decision = None
    best_score = 0.0
    matched_queries = 0

    for focused_query in doctrinal_verification_queries(query):
        decision = await jurisprudencia.read_decision(copy.deepcopy(base), focused_query)
        if not decision.verified:
            continue
        if not jurisprudencia._document_relevance_confirmed(decision, focused_query):
            continue
        matched_queries += 1
        score = smart_server._verified_rank(decision, candidate.discovery_score, focused_query)
        score += min(6.0, max(0, matched_queries - 1) * 1.5)
        if best_decision is None or score > best_score:
            best_decision = decision
            best_score = score

    if best_decision is None:
        return None, 0.0

    return best_decision, round(best_score, 2)


def faster_minimum_verifications(maximo: int) -> int:
    """Require a meaningful sample without forcing 25+ PDF reads for Top-5."""
    requested = max(1, int(maximo))
    target = max(smart_server.VERIFY_BATCH_SIZE * 2, requested * 3)
    return min(smart_server.MAX_OFFICIAL_VERIFICATIONS, target)


# Apply tuning to the already-registered relevance loop. Python resolves these
# globals at call time, so existing MCP tools automatically use the tuned logic.
smart_server._discovery_score = improved_discovery_score
smart_server._verify_candidate = doctrine_aware_verify_candidate
smart_server._minimum_verifications_before_stability = faster_minimum_verifications
smart_server.VERIFY_BATCH_SIZE = 5
smart_server.VERIFY_CONCURRENCY = 5
smart_server.MAX_OFFICIAL_VERIFICATIONS = 24
smart_server.STABLE_ROUNDS_REQUIRED = 1
