"""Multi-source orchestration layer for Puerto Rico legal research.

This module adds a single MCP tool for a legal-research question that may need
more than case law. It deliberately keeps two buckets separate:

1. authorities verified against source text (currently the mature TSPR path),
2. candidates discovered in official public portals that still require content
   verification before they can be cited for a legal proposition.

That separation prevents a link found in an official index from being ranked as
if its legal holding or statutory text had already been verified.
"""
from __future__ import annotations

import asyncio
from typing import Any

import research_server
import smart_server

VERSION = "0.9.0"
# The shared status tools live in research_server; align their runtime version
# with the package entrypoint without rewriting the mature source collectors.
research_server.VERSION = VERSION
mcp = smart_server.mcp


def _safe_results(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows = value.get("resultados", [])
        return rows if isinstance(rows, list) else []
    return []


def _mark_discovery_candidate(row: dict[str, Any], tipo: str) -> dict[str, Any]:
    item = dict(row)
    item["tipo_autoridad"] = tipo
    item["estado_verificacion"] = "descubierto_en_fuente_oficial; contenido_juridico_pendiente_de_verificar"
    item["puede_citarse_como_proposicion_juridica"] = False
    return item


async def mixed_authority_research(
    argumento: str,
    maximo: int = 8,
    incluir_actualidad: bool = False,
    ano_apelaciones: int | None = None,
) -> dict[str, Any]:
    """Coordinate the mature TSPR loop with other public-source collectors.

    Only source-text-verified authorities enter ``autoridades_verificadas``.
    Official-index discoveries are returned separately until a later collector
    verifies their actual document text. This is intentional: source hierarchy
    must not be confused with evidentiary verification depth.
    """
    maximo = max(1, min(int(maximo), 12))
    tspr_limit = min(maximo, 6)

    tasks: list[Any] = [
        smart_server.relevance_first_search(argumento, maximo=tspr_limit),
        research_server.buscar_biblioteca_juridica(argumento, maximo=maximo),
        research_server.buscar_decisiones_laborales(argumento, maximo=maximo),
    ]
    labels = ["tspr", "biblioteca", "laboral"]

    if ano_apelaciones is not None:
        tasks.append(research_server.buscar_decisiones_apelaciones(argumento, int(ano_apelaciones), maximo))
        labels.append("apelaciones")
    if incluir_actualidad:
        tasks.append(research_server.buscar_actualidad_juridica(argumento, maximo=maximo))
        labels.append("actualidad")

    raw = await asyncio.gather(*tasks, return_exceptions=True)
    by_label: dict[str, Any] = dict(zip(labels, raw))

    tspr = by_label.get("tspr")
    verified: list[dict[str, Any]] = []
    if isinstance(tspr, dict):
        for row in tspr.get("resultados", []):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["tipo_autoridad"] = "jurisprudencia_tribunal_supremo"
            item["estado_verificacion"] = "texto_fuente_primaria_verificado"
            item["puede_citarse_como_proposicion_juridica"] = True
            verified.append(item)

    candidates: list[dict[str, Any]] = []
    for row in _safe_results(by_label.get("biblioteca")):
        candidates.append(_mark_discovery_candidate(row, "legislacion_reglamentos_ejecutivo"))
    for row in _safe_results(by_label.get("laboral")):
        candidates.append(_mark_discovery_candidate(row, "decision_administrativa_laboral"))
    for row in _safe_results(by_label.get("apelaciones")):
        candidates.append(_mark_discovery_candidate(row, "decision_tribunal_apelaciones"))

    secondary: list[dict[str, Any]] = []
    if incluir_actualidad:
        for row in _safe_results(by_label.get("actualidad")):
            item = dict(row)
            item["tipo_fuente"] = "fuente_secundaria_publica"
            item["uso"] = "descubrimiento_contexto; no sustituye autoridad primaria"
            secondary.append(item)

    verified.sort(key=lambda row: -float(row.get("ranking_relevancia", row.get("relevance_score", 0)) or 0))

    errors: dict[str, str] = {}
    for label, value in by_label.items():
        if isinstance(value, Exception):
            errors[label] = str(value)
        elif isinstance(value, dict) and value.get("error"):
            errors[label] = str(value["error"])

    return {
        "producto": research_server.PRODUCT_NAME,
        "version": VERSION,
        "consulta": argumento,
        "estrategia": "multi_source_with_verification_tiers",
        "autoridades_verificadas": verified[:maximo],
        "candidatos_primarios_por_verificar": candidates[: maximo * 2],
        "actualidad_secundaria": secondary[:maximo],
        "regla_ranking": (
            "Solo las autoridades con texto de fuente primaria verificado entran al ranking principal. "
            "Los resultados hallados únicamente en índices o portales oficiales se mantienen como candidatos separados."
        ),
        "regla_integridad": (
            "No convertir descubrimiento de índice en holding, texto estatutario, vigencia o proposición jurídica. "
            "Si un dato no se verificó en el documento fuente, permanece pendiente de verificar."
        ),
        "errores_fuente": errors,
        "siguiente_etapa": (
            "Profundizar lectores de legislación, reglamentos, Tribunal de Apelaciones y decisiones administrativas "
            "para que sus documentos también puedan competir en el ranking verificado."
        ),
    }


@mcp.tool()
async def buscar_mejores_autoridades(
    argumento: str,
    maximo: int = 8,
    incluir_actualidad: bool = False,
    ano_apelaciones: int | None = None,
) -> dict[str, Any]:
    """Investiga una cuestión jurídica en varias fuentes sin mezclar niveles de verificación.

    Úsala cuando el usuario pida las mejores autoridades para una cuestión y la
    respuesta pueda requerir jurisprudencia, leyes, reglamentos o decisiones
    administrativas. El ranking principal contiene solo autoridades cuyo texto
    fuente ya fue verificado. Las demás fuentes oficiales aparecen como
    candidatos pendientes de verificación de contenido, nunca como holdings o
    reglas de derecho confirmadas.
    """
    return await mixed_authority_research(argumento, maximo, incluir_actualidad, ano_apelaciones)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
