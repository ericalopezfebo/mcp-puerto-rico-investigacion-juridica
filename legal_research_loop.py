"""Bounded, auditable legal-research orchestration for Puerto Rico authority.

This module sits above ``smart_server.relevance_first_search``.  The lower
layer discovers and verifies official TSPR documents.  This layer broadens the
research plan, accumulates candidates, tests Top-K stability, forces an adverse
search pass, and reports gaps without pretending that lexical similarity proves
a holding, current validity, or factual equivalence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import smart_server

mcp = smart_server.mcp

DEFAULT_MAX_ROUNDS = 4
MAX_ALLOWED_ROUNDS = 6
MAX_RESULTS_PER_ROUND = 10
STABLE_ROUNDS_REQUIRED = 2


@dataclass
class ResearchState:
    target: int
    adverse_required: bool = True
    candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    search_log: list[dict[str, Any]] = field(default_factory=list)
    previous_top: tuple[str, ...] = ()
    stable_rounds: int = 0
    adverse_pass_completed: bool = False


def _norm(value: str) -> str:
    return smart_server.jurisprudencia.normalize_text(value or "")


def _terms(*values: str) -> list[str]:
    stop = {
        "para", "como", "porque", "puerto", "rico", "derecho", "legal",
        "caso", "casos", "sentencia", "sentencias", "mejores", "ayuda",
        "ayudan", "parte", "esta", "este", "estos", "estas", "sobre",
    }
    words: list[str] = []
    for value in values:
        words.extend(re.findall(r"[A-Za-zÀ-ÿ0-9]+", _norm(value)))
    return list(dict.fromkeys(w for w in words if len(w) >= 4 and w not in stop))


def build_queries(
    pregunta_juridica: str,
    proposicion_a_sostener: str,
    hechos_materiales: list[str],
    incluir_contrarias: bool,
) -> list[tuple[str, str]]:
    """Create distinct research passes; labels describe purpose, not outcome."""
    facts = " ".join(hechos_materiales)
    key_terms = _terms(pregunta_juridica, proposicion_a_sostener, facts)[:12]
    focused = " ".join(key_terms)
    queries: list[tuple[str, str]] = [
        ("proposicion_directa", f"{proposicion_a_sostener} {focused}".strip()),
        ("controversia_juridica", f"{pregunta_juridica} {focused}".strip()),
        ("aplicacion_a_hechos", f"{proposicion_a_sostener} {facts}".strip()),
    ]
    if incluir_contrarias:
        queries.append((
            "potencialmente_adversa",
            (
                f"posición contraria excepción improcedente error revoca "
                f"{pregunta_juridica} {proposicion_a_sostener} {focused}"
            ).strip(),
        ))
    seen: set[str] = set()
    output: list[tuple[str, str]] = []
    for purpose, query in queries:
        normalized = _norm(query)
        if normalized and normalized not in seen:
            seen.add(normalized)
            output.append((purpose, query[:1800]))
    return output


def _citation_key(row: dict[str, Any]) -> str:
    raw = str(row.get("citation") or row.get("cita") or row.get("url") or row.get("title") or "")
    return smart_server.jurisprudencia.normalize_citation(raw) or _norm(raw)


def _score_candidate(
    row: dict[str, Any],
    proposicion: str,
    hechos: list[str],
    purposes: set[str],
) -> dict[str, Any]:
    snippet = str(row.get("snippet") or row.get("extracto") or "")
    haystack = _norm(f"{row.get('title', '')} {snippet}")
    proposition_terms = _terms(proposicion)
    fact_terms = _terms(" ".join(hechos))
    proposition_hits = sum(1 for term in proposition_terms if term in haystack)
    fact_hits = sum(1 for term in fact_terms if term in haystack)
    verified = bool(row.get("verified") or row.get("verificado"))
    source_status = str(row.get("verification_status") or row.get("estado_verificacion") or "")
    official = verified or "verified" in source_status.lower() or "verific" in source_status.lower()
    underlying = float(row.get("ranking_relevancia") or row.get("relevance_score") or 0.0)
    score = underlying + proposition_hits * 3.0 + fact_hits * 1.25 + (15.0 if official else 0.0)
    return {
        **row,
        "evaluacion_loop": {
            "puntaje_total": round(score, 2),
            "coincidencias_proposicion": proposition_hits,
            "coincidencias_hechos": fact_hits,
            "documento_oficial_verificado": official,
            "rutas_descubrimiento": sorted(purposes),
            "holding": "REQUIERE_ANALISIS_JURIDICO_DEL_TEXTO",
            "vigencia": "NO_CONFIRMADA_POR_ESTE_LOOP",
            "comparacion_factica": "PRELIMINAR_POR_COINCIDENCIA_TEXTUAL",
        },
    }


def _rank(state: ResearchState) -> list[dict[str, Any]]:
    return sorted(
        state.candidates.values(),
        key=lambda row: (
            -float(row["evaluacion_loop"]["puntaje_total"]),
            _citation_key(row),
        ),
    )


def _completion(state: ResearchState) -> tuple[bool, list[str]]:
    ranked = _rank(state)
    qualified = [r for r in ranked if r["evaluacion_loop"]["documento_oficial_verificado"]]
    missing: list[str] = []
    if len(qualified) < state.target:
        missing.append(f"Solo {len(qualified)} de {state.target} autoridades tienen documento oficial verificado.")
    if state.adverse_required and not state.adverse_pass_completed:
        missing.append("No se completó la búsqueda potencialmente adversa.")
    if state.stable_rounds < STABLE_ROUNDS_REQUIRED:
        missing.append("El Top-K aún no permaneció estable durante dos evaluaciones.")
    return not missing, missing


async def legal_research_loop(
    pregunta_juridica: str,
    proposicion_a_sostener: str,
    hechos_materiales: list[str] | None = None,
    postura_procesal: str = "",
    parte_representada: str = "",
    maximo: int = 5,
    incluir_contrarias: bool = True,
    max_rondas: int = DEFAULT_MAX_ROUNDS,
    ano_desde: int = smart_server.MIN_PUBLIC_DISCOVERY_YEAR,
    ano_hasta: int = 2026,
) -> dict[str, Any]:
    """Run bounded multi-pass research over the verified TSPR retrieval loop."""
    facts = [str(x).strip() for x in (hechos_materiales or []) if str(x).strip()]
    target = max(1, min(int(maximo), 10))
    round_budget = max(1, min(int(max_rondas), MAX_ALLOWED_ROUNDS))
    queries = build_queries(pregunta_juridica, proposicion_a_sostener, facts, incluir_contrarias)
    state = ResearchState(target=target, adverse_required=incluir_contrarias)
    purposes_by_key: dict[str, set[str]] = {}
    stop_reason = "PRESUPUESTO_AGOTADO"

    for round_number in range(1, round_budget + 1):
        purpose, query = queries[(round_number - 1) % len(queries)]
        result = await smart_server.relevance_first_search(
            query=query,
            maximo=MAX_RESULTS_PER_ROUND,
            ano_desde=ano_desde,
            ano_hasta=ano_hasta,
        )
        rows = list(result.get("resultados") or [])
        if purpose == "potencialmente_adversa":
            state.adverse_pass_completed = True
        added = 0
        for row in rows:
            key = _citation_key(row)
            if not key:
                continue
            purposes_by_key.setdefault(key, set()).add(purpose)
            evaluated = _score_candidate(row, proposicion_a_sostener, facts, purposes_by_key[key])
            current = state.candidates.get(key)
            if current is None or evaluated["evaluacion_loop"]["puntaje_total"] > current["evaluacion_loop"]["puntaje_total"]:
                state.candidates[key] = evaluated
                added += 1

        ranked = _rank(state)
        top = tuple(_citation_key(row) for row in ranked[:target])
        if len(top) >= target and top == state.previous_top:
            state.stable_rounds += 1
        else:
            state.stable_rounds = 0
        state.previous_top = top
        state.search_log.append({
            "ronda": round_number,
            "proposito": purpose,
            "consulta": query,
            "resultados_recibidos": len(rows),
            "candidatos_nuevos_o_mejorados": added,
            "top_actual": list(top),
            "rondas_estables": state.stable_rounds,
        })
        complete, _ = _completion(state)
        if complete:
            stop_reason = "CRITERIOS_CUMPLIDOS"
            break

    complete, gaps = _completion(state)
    ranked = _rank(state)
    qualified = [r for r in ranked if r["evaluacion_loop"]["documento_oficial_verificado"]][:target]
    return {
        "estado": "COMPLETO_PARA_REVISION_HUMANA" if complete else "PARCIAL_REQUIERE_REVISION",
        "motivo_parada": stop_reason,
        "pregunta_juridica": pregunta_juridica,
        "proposicion_a_sostener": proposicion_a_sostener,
        "postura_procesal": postura_procesal,
        "parte_representada": parte_representada,
        "hechos_materiales": facts,
        "autoridades_solicitadas": target,
        "autoridades_calificadas": len(qualified),
        "resultados": qualified,
        "busqueda_potencialmente_adversa_completada": state.adverse_pass_completed,
        "registro_busqueda": state.search_log,
        "vacios": gaps,
        "limitaciones": [
            "La puntuación jurídica es preliminar y no sustituye la lectura profesional del caso completo.",
            "Este loop no afirma por sí solo cuál es el holding ni la vigencia posterior de una autoridad.",
            "Una búsqueda potencialmente adversa identifica candidatos; no clasifica automáticamente un caso como contrario.",
            "La cobertura pública principal del índice TSPR comienza en 1997.",
        ],
    }


@mcp.tool()
async def investigar_argumento_juridico(
    pregunta_juridica: str,
    proposicion_a_sostener: str,
    hechos_materiales: list[str] | None = None,
    postura_procesal: str = "",
    parte_representada: str = "",
    maximo: int = 5,
    incluir_contrarias: bool = True,
    max_rondas: int = DEFAULT_MAX_ROUNDS,
    ano_desde: int = smart_server.MIN_PUBLIC_DISCOVERY_YEAR,
    ano_hasta: int = 2026,
) -> dict[str, Any]:
    """Investiga un argumento con un loop limitado, auditable y source-first.

    Úsala cuando no baste una búsqueda puntual y sea necesario comparar varias
    formulaciones, acumular autoridades verificadas, ejecutar una búsqueda
    potencialmente adversa y detenerse por criterios de suficiencia/estabilidad
    o por un presupuesto explícito. El resultado siempre requiere revisión
    profesional del holding, la vigencia y la aplicación a los hechos.
    """
    return await legal_research_loop(
        pregunta_juridica=pregunta_juridica,
        proposicion_a_sostener=proposicion_a_sostener,
        hechos_materiales=hechos_materiales,
        postura_procesal=postura_procesal,
        parte_representada=parte_representada,
        maximo=maximo,
        incluir_contrarias=incluir_contrarias,
        max_rondas=max_rondas,
        ano_desde=ano_desde,
        ano_hasta=ano_hasta,
    )
