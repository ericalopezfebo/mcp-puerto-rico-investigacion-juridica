"""Multi-source orchestration layer for Puerto Rico legal research."""
from __future__ import annotations

import asyncio
from typing import Any

import research_server
import smart_server
import search_tuning  # improves doctrinal recall and bounds Top-K verification latency
import authority_reader  # registers leer_autoridad_publica
import jrt_server  # registers verified JRT search
import vigencia_server  # registers single-page legislative currency safeguards
import legislative_graph  # registers automatic SUTRA amendment-history graph

VERSION = "0.12.1"
research_server.VERSION = VERSION
mcp = smart_server.mcp

# Server-level instructions are sent to MCP clients during initialization. This
# makes the routing and currency policies visible even before the model inspects
# individual tool descriptions.
MCP_ROUTING_INSTRUCTIONS = """
REGLA OBLIGATORIA DE ENRUTAMIENTO PARA JURISPRUDENCIA TSPR:
Cuando el usuario pida "las mejores", "las más relevantes", "Top N", "las que
más apoyen mi argumento", "las que más ayuden a mi argumento", "las autoridades
más fuertes", o una expresión equivalente sobre decisiones del Tribunal Supremo
de Puerto Rico, usa `buscar_mejores_sentencias`.

No uses `investigar_sentencias` ni `buscar_sentencias` como herramienta principal
para ese tipo de petición, salvo que el usuario haya pedido expresamente limitar
la investigación a un año o rango de años específico. `buscar_mejores_sentencias`
debe competir candidatos globalmente por relevancia jurídica verificada, sin
bono por recencia y sin recorrer años del más reciente al más antiguo para llenar
un cupo. Si no hay suficientes autoridades verificables y realmente pertinentes,
devuelve menos resultados en vez de completar el Top-N con casos marginales.

Para preguntas doctrinales complejas, el motor puede expandir conceptos de
recuperación (por ejemplo, empleado de confianza/carrera -> debido proceso,
interés propietario, principio de mérito, reglamento de personal) únicamente
para DESCUBRIR candidatos. Esas expansiones nunca sustituyen la verificación del
PDF oficial ni convierten un caso en pertinente por sí solas.

REGLA OBLIGATORIA DE VIGENCIA LEGISLATIVA:
Nunca presentes una ley, código, reglamento o disposición como "vigente",
"actual", "no derogada" o equivalente únicamente porque apareció en CodeXPR,
LexJuris, Microjuris, un PDF histórico o un índice. Cuando la consulta dependa de
la vigencia de una ley o artículo identificable, usa primero
`verificar_vigencia_ley` o `construir_historial_legislativo` para buscar
automáticamente en SUTRA las enmiendas, derogaciones, sustituciones o
reenumeraciones posteriores. Si ya tienes una URL oficial concreta también puedes
usar `verificar_vigencia_legislativa` para inspeccionar esa página específica.

SUTRA / Oficina de Servicios Legislativos y la Biblioteca Jurídica Virtual /
Departamento de Estado son fuentes oficiales preferidas. La ausencia de una
derogación detectada no equivale a prueba positiva de vigencia; si el historial
o el texto oficial aplicable no permiten resolverlo, informa `no_determinada`.
Nunca presumas vigencia por silencio, por ausencia de resultados o por un fallo
de acceso.

CodeXPR puede usarse como capa de descubrimiento cuando su contenido sea público
y accesible, pero no como prueba final de vigencia. No uses cookies personales,
credenciales, extensiones del navegador ni métodos para evadir login/paywalls.
""".strip()

_low_level_server = getattr(mcp, "_mcp_server", None)
if _low_level_server is not None:
    _existing_instructions = getattr(_low_level_server, "instructions", None) or ""
    if MCP_ROUTING_INSTRUCTIONS not in _existing_instructions:
        _low_level_server.instructions = (
            f"{_existing_instructions}\n\n{MCP_ROUTING_INSTRUCTIONS}".strip()
        )

LABOR_QUERY_HINTS = {
    "negociacion colectiva", "convenio colectivo", "practica ilicita", "practicas ilicitas",
    "relaciones del trabajo", "sindicato", "sindical", "union obrera", "organizacion obrera",
    "arbitraje laboral", "laudo", "patrono", "empleado unionado", "unidad apropiada",
    "representacion sindical", "deber de justa representacion", "ley 130",
}


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
    if tipo == "legislacion_reglamentos_ejecutivo":
        item["estado_vigencia"] = "no_determinada"
        item["puede_afirmarse_vigente"] = False
    return item


def _looks_labor_related(argumento: str) -> bool:
    normalized = smart_server.jurisprudencia.normalize_text(argumento)
    return any(smart_server.jurisprudencia.normalize_text(term) in normalized for term in LABOR_QUERY_HINTS)


def _authority_sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
    tipo = row.get("tipo_autoridad", "")
    hierarchy = {
        "jurisprudencia_tribunal_supremo": 100.0,
        "decision_administrativa_laboral": 60.0,
    }.get(tipo, 40.0)
    relevance = float(row.get("ranking_relevancia", row.get("relevance_score", 0)) or 0)
    title = str(row.get("citation") or row.get("titulo") or row.get("title") or "")
    return (-hierarchy, -relevance, title)


async def mixed_authority_research(
    argumento: str,
    maximo: int = 8,
    incluir_actualidad: bool = False,
    ano_apelaciones: int | None = None,
) -> dict[str, Any]:
    """Coordinate verified and discovery-only legal sources with strict tiers."""
    maximo = max(1, min(int(maximo), 12))
    tspr_limit = min(maximo, 6)

    tasks: list[Any] = [
        smart_server.relevance_first_search(argumento, maximo=tspr_limit),
        research_server.buscar_biblioteca_juridica(argumento, maximo=maximo),
    ]
    labels = ["tspr", "biblioteca"]

    labor_enabled = _looks_labor_related(argumento)
    if labor_enabled:
        tasks.append(jrt_server.search_jrt_fulltext(argumento, maximo=min(maximo, 5)))
        labels.append("laboral_verificado")

    if ano_apelaciones is not None:
        tasks.append(research_server.buscar_decisiones_apelaciones(argumento, int(ano_apelaciones), maximo))
        labels.append("apelaciones")
    if incluir_actualidad:
        tasks.append(research_server.buscar_actualidad_juridica(argumento, maximo=maximo))
        labels.append("actualidad")

    raw = await asyncio.gather(*tasks, return_exceptions=True)
    by_label: dict[str, Any] = dict(zip(labels, raw))

    verified: list[dict[str, Any]] = []
    tspr = by_label.get("tspr")
    if isinstance(tspr, dict):
        for row in tspr.get("resultados", []):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["tipo_autoridad"] = "jurisprudencia_tribunal_supremo"
            item["estado_verificacion"] = "texto_fuente_primaria_verificado"
            item["puede_citarse_como_proposicion_juridica"] = True
            verified.append(item)

    labor = by_label.get("laboral_verificado")
    if isinstance(labor, dict):
        for row in labor.get("resultados", []):
            if isinstance(row, dict) and row.get("estado_verificacion") == "texto_fuente_primaria_verificado":
                verified.append(dict(row))

    candidates: list[dict[str, Any]] = []
    for row in _safe_results(by_label.get("biblioteca")):
        candidates.append(_mark_discovery_candidate(row, "legislacion_reglamentos_ejecutivo"))
    for row in _safe_results(by_label.get("apelaciones")):
        candidates.append(_mark_discovery_candidate(row, "decision_tribunal_apelaciones"))

    secondary: list[dict[str, Any]] = []
    if incluir_actualidad:
        for row in _safe_results(by_label.get("actualidad")):
            item = dict(row)
            item["tipo_fuente"] = "fuente_secundaria_publica"
            item["uso"] = "descubrimiento_contexto; no sustituye autoridad primaria"
            secondary.append(item)

    verified.sort(key=_authority_sort_key)

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
        "busqueda_laboral_activada": labor_enabled,
        "herramienta_verificacion_candidatos": "leer_autoridad_publica",
        "herramientas_vigencia_legislativa": [
            "verificar_vigencia_ley",
            "construir_historial_legislativo",
            "verificar_vigencia_legislativa",
        ],
        "regla_ranking": (
            "El ranking principal admite solo texto de fuente primaria verificado. Entre clases distintas se conserva "
            "jerarquía de autoridad y dentro de cada clase se usa relevancia textual."
        ),
        "regla_integridad": (
            "No convertir descubrimiento de índice en holding, texto estatutario, vigencia o proposición jurídica. "
            "Si un dato no se verificó en el documento fuente, permanece pendiente de verificar."
        ),
        "regla_vigencia": (
            "Las autoridades legislativas/reglamentarias descubiertas no se presumen vigentes. Para leyes identificables se usa el historial automático de SUTRA; "
            "si la vigencia positiva no puede resolverse con evidencia oficial suficiente, el estado sigue siendo no_determinada."
        ),
        "errores_fuente": errors,
        "siguiente_etapa": (
            "Profundizar búsqueda estructurada y lectura directa de legislación/reglamentos y Tribunal de Apelaciones."
        ),
    }


@mcp.tool()
async def buscar_mejores_autoridades(
    argumento: str,
    maximo: int = 8,
    incluir_actualidad: bool = False,
    ano_apelaciones: int | None = None,
) -> dict[str, Any]:
    """Investiga una cuestión jurídica en varias fuentes con niveles estrictos de verificación."""
    return await mixed_authority_research(argumento, maximo, incluir_actualidad, ano_apelaciones)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
