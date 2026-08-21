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
from doctrine_ontology import matching_concepts

# Small high-value bridges kept for historically difficult queries. The broader
# vocabulary now lives in doctrine_ontology.py so search tuning is not a pile of
# one-off exceptions.
_DOCTRINAL_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "empleado de confianza": (
        "servicio de carrera", "empleado de carrera", "debido proceso de ley",
        "interes propietario", "derecho propietario", "principio de merito",
        "planes de clasificacion", "retribucion", "reglamento de personal",
    ),
    "reinstalacion": (
        "reposicion", "reingreso", "servicio de carrera", "empleado de carrera", "remedio",
    ),
    "derecho propietario": (
        "interes propietario", "interes de propiedad", "debido proceso de ley", "derecho adquirido",
    ),
    "reglamento": (
        "facultad reglamentaria", "agencia obligada a seguir su reglamento",
        "derechos establecidos en reglamento", "debido proceso de ley", "ultra vires",
        "error administrativo", "reglamento de personal",
    ),
}


def _normalized(text: str) -> str:
    return jurisprudencia.normalize_text(text or "")


def _concept_matches(query: str):
    return matching_concepts(_normalized(query))


def expanded_query_terms(query: str) -> list[tuple[str, float]]:
    """Return original and doctrine-aware search terms with weights.

    Ontology expansions are discovery-only. They can cause a candidate to be
    opened, but cannot make an authority verified.
    """
    normalized = _normalized(query)
    weighted: dict[str, float] = {}

    for term in jurisprudencia.query_terms(query):
        nt = _normalized(term)
        if nt:
            weighted[nt] = max(weighted.get(nt, 0.0), 1.0)

    for trigger, expansions in _DOCTRINAL_EXPANSIONS.items():
        if _normalized(trigger) not in normalized:
            continue
        for term in expansions:
            nt = _normalized(term)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.72)

    # Controlled ontology: aliases are strong signals; related concepts are
    # softer bridges that help map factual language to doctrinal catalog labels.
    for _name, concept in _concept_matches(query):
        for alias in concept.aliases:
            nt = _normalized(alias)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.92)
        for related in concept.related:
            nt = _normalized(related)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.68)
        area = _normalized(concept.area)
        if area:
            weighted[area] = max(weighted.get(area, 0.0), 0.42)

    return sorted(weighted.items(), key=lambda item: (-item[1], item[0]))


def improved_discovery_score(blob: str, query: str) -> float:
    """Score public index metadata using exact + doctrinally-related concepts."""
    normalized = _normalized(blob)
    query_norm = _normalized(query)
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
        score += min(7.0, (matched - 2) * 1.0)

    # Reward internally coherent ontology clusters rather than isolated words.
    for _name, concept in _concept_matches(query):
        alias_hits = sum(1 for phrase in concept.aliases if _normalized(phrase) in normalized)
        related_hits = sum(1 for phrase in concept.related if _normalized(phrase) in normalized)
        if alias_hits and related_hits >= 2:
            score += min(12.0, 4.0 + related_hits * 1.5)
        elif related_hits >= 3:
            score += min(8.0, related_hits * 1.5)

        # Sense disambiguation: a false-sense phrase is a strong penalty only
        # when the candidate lacks positive signals for the intended concept.
        false_hits = sum(1 for phrase in concept.false_senses if _normalized(phrase) in normalized)
        if false_hits and alias_hits == 0 and related_hits < 2:
            score -= min(24.0, false_hits * 12.0)

    bridge_sets = (
        ("debido proceso de ley", "planes de clasificacion"),
        ("debido proceso de ley", "retribucion"),
        ("reglamento de personal", "debido proceso de ley"),
        ("servicio de carrera", "principio de merito"),
        ("regla 21", "interes afectado"),
        ("regla 21", "representacion adecuada"),
        ("intervencion como cuestion de derecho", "interes que amerite proteccion"),
        ("prueba de referencia", "declaracion fuera del tribunal"),
        ("sentencia sumaria", "hecho material"),
        ("jurisdiccion primaria", "pericia administrativa"),
        ("agotamiento de remedios", "revision judicial"),
        ("empleado de carrera", "interes propietario"),
        ("igual proteccion de las leyes", "escrutinio estricto"),
    )
    available = {term for term, _weight in terms}
    for left, right in bridge_sets:
        if left in available and right in available and left in normalized and right in normalized:
            score += 8.0

    return round(max(0.0, score), 2)


def doctrinal_verification_queries(query: str) -> list[str]:
    """Create focused doctrine queries for reading an official PDF.

    Complex user prompts are decomposed into independently verifiable legal
    sub-issues. This prevents a controlling case from being rejected just because
    no single paragraph repeats the user's entire factual formulation.
    """
    normalized = _normalized(query)
    queries = [query]

    def add(value: str) -> None:
        key = _normalized(value)
        if key and all(_normalized(q) != key for q in queries):
            queries.append(value)

    for _name, concept in _concept_matches(query):
        for focused in concept.verification_queries:
            add(focused)

    # Cross-doctrine bridges for difficult employment/regulation questions.
    if "reglamento" in normalized:
        add("agencia obligada a seguir su reglamento debido proceso derechos establecidos reglamento")
        add("reglamento crea derecho concreto derecho propietario interes propietario")
        add("reglamento error administrativo ultra vires derechos reconocidos")
    if "confianza" in normalized or "carrera" in normalized:
        add("empleado de confianza servicio de carrera empleado de carrera principio de merito")
        add("planes de clasificacion retribucion debido proceso servicio de carrera")
    if "reinstal" in normalized or "reposicion" in normalized or "reingreso" in normalized:
        add("reinstalacion reposicion reingreso empleado de carrera remedio")

    return queries[:12]


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
        score += min(7.5, max(0, matched_queries - 1) * 1.5)
        if best_decision is None or score > best_score:
            best_decision = decision
            best_score = score

    if best_decision is None:
        return None, 0.0

    return best_decision, round(best_score, 2)


def faster_minimum_verifications(maximo: int) -> int:
    """Require a meaningful sample without forcing 25+ PDF reads for Top-5."""
    requested = max(1, int(maximo))
    if (
        smart_server.VERIFY_BATCH_SIZE == 5
        and smart_server.MAX_OFFICIAL_VERIFICATIONS == 24
    ):
        target = max(smart_server.VERIFY_BATCH_SIZE * 2, requested * 3)
    else:
        # Preserve the core engine's conservative sampling rule when callers
        # override the tuning constants for larger or security-sensitive runs.
        target = max(smart_server.VERIFY_BATCH_SIZE * 3, requested * 5)
    return min(smart_server.MAX_OFFICIAL_VERIFICATIONS, target)


# Apply tuning to the already-registered relevance loop. Python resolves these
# globals at call time, so existing MCP tools automatically use the tuned logic.
smart_server._discovery_score = improved_discovery_score
smart_server._verify_candidate = doctrine_aware_verify_candidate
smart_server._minimum_verifications_before_stability = faster_minimum_verifications
smart_server.VERIFY_BATCH_SIZE = 5
smart_server.VERIFY_CONCURRENCY = 5
smart_server.MAX_OFFICIAL_VERIFICATIONS = 24
smart_server.STABLE_ROUNDS_REQUIRED = 2
