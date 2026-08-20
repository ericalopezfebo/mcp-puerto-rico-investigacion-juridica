"""Expanded Puerto Rico legal research MCP.

This module preserves the tested Tribunal Supremo logic from ``server.py`` and
exposes it under a broader MCP identity together with public-source research
tools for other Puerto Rico legal authorities.

Integrity rule: discovery is not verification. A result is labelled verified
only when it was found in the identified public source. Secondary-source items
are always identified as secondary and are never presented as primary legal
authority.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import asdict
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

import server as jurisprudencia
import corpus_index

PRODUCT_NAME = "MCP Puerto Rico — Investigación Jurídica"
PRODUCT_SLUG = "puerto-rico-investigacion-juridica"
VERSION = "0.15.0"

# New public server identity. The legacy server module remains untouched and is
# used as a tested implementation library for Tribunal Supremo operations.
mcp = FastMCP(PRODUCT_SLUG)

APPEALS_INDEX = (
    "https://poderjudicial.pr/tribunal-apelaciones/"
    "decisiones-finales-del-tribunal-de-apelaciones/"
)
STATE_LIBRARY = "https://bibliotecavirtual.estado.pr.gov/"
JRT_HOME = "https://www.jrt.pr.gov/"
MICROJURIS_ALDIA = "https://aldia.microjuris.com/"

RESEARCH_ALLOWED_HOSTS = {
    "poderjudicial.pr",
    "www.poderjudicial.pr",
    "dts.poderjudicial.pr",
    "bibliotecavirtual.estado.pr.gov",
    "estado.pr.gov",
    "www.estado.pr.gov",
    "jrt.pr.gov",
    "www.jrt.pr.gov",
    "aldia.microjuris.com",
}

PRIMARY_SOURCE_CATALOG: dict[str, dict[str, Any]] = {
    "constitucion_y_leyes": {
        "nombre": "Biblioteca Jurídica Virtual del Departamento de Estado",
        "url": STATE_LIBRARY,
        "tipos": ["leyes", "resoluciones conjuntas", "reglamentos", "órdenes ejecutivas", "decretos", "proclamas"],
        "nivel": "fuente_primaria_oficial",
    },
    "tribunal_supremo": {
        "nombre": "Poder Judicial — Tribunal Supremo",
        "url": jurisprudencia.OFFICIAL_INDEX,
        "tipos": ["opiniones", "sentencias", "resoluciones"],
        "nivel": "fuente_primaria_oficial",
    },
    "tribunal_apelaciones": {
        "nombre": "Poder Judicial — Tribunal de Apelaciones",
        "url": APPEALS_INDEX,
        "tipos": ["determinaciones finales públicas desde enero de 2015"],
        "nivel": "fuente_primaria_oficial",
    },
    "relaciones_trabajo": {
        "nombre": "Junta de Relaciones del Trabajo de Puerto Rico",
        "url": JRT_HOME,
        "tipos": ["decisiones y órdenes", "órdenes administrativas", "avisos de desestimación"],
        "nivel": "fuente_primaria_oficial",
    },
}

SECONDARY_SOURCE_CATALOG: dict[str, dict[str, Any]] = {
    "microjuris_al_dia": {
        "nombre": "Microjuris Al Día",
        "url": MICROJURIS_ALDIA,
        "tipos": ["noticias legales", "análisis", "actualidad jurídica"],
        "nivel": "fuente_secundaria_publica",
        "regla": "Se usa para descubrimiento y contexto; la proposición jurídica final debe verificarse contra autoridad primaria cuando sea posible.",
    }
}


def _normalize(value: str) -> str:
    return jurisprudencia.normalize_text(value)


def _research_url_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in RESEARCH_ALLOWED_HOSTS
    except Exception:
        return False


async def _fetch(url: str) -> httpx.Response:
    if not _research_url_allowed(url):
        raise ValueError("URL no permitida para investigación pública")
    client = await jurisprudencia.get_http_client()
    response = await client.get(url)
    response.raise_for_status()
    return response


def _terms(query: str) -> list[str]:
    stop = {
        "busca", "buscar", "encuentra", "encontrar", "sobre", "para", "como",
        "puerto", "rico", "derecho", "juridico", "juridica", "legal", "ley",
        "tribunal", "caso", "casos", "dame", "quiero", "necesito", "del", "las",
        "los", "una", "uno", "que", "con", "por", "de", "en", "y",
    }
    raw = [x for x in re.findall(r"[\wÀ-ÿ]+", query.lower()) if len(x) > 2]
    return list(dict.fromkeys(x for x in raw if _normalize(x) not in stop))


def _score_blob(blob: str, query: str) -> int:
    low = _normalize(blob)
    score = 0
    for term in _terms(query):
        nt = _normalize(term)
        if nt and nt in low:
            score += 2 if " " in nt else 1
    q = _normalize(query)
    if q and len(q) >= 6 and q in low:
        score += 5
    return score


def _appeals_month_links(html: str, year: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(APPEALS_INDEX, a["href"])
        low = href.lower()
        if str(year) in low and "decisiones-del-tribunal-de-apelaciones" in low:
            if href not in out:
                out.append(href)
    return out


def _parse_appeals_month(html: str, base_url: str, query: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []
    for row in soup.find_all("tr"):
        cells = [jurisprudencia.clean(td.get_text(" ", strip=True)) for td in row.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        case_number, parties, date = cells[0], cells[1], cells[2]
        if not re.match(r"^[A-Z]{2,8}\d{6,}$", case_number.replace("-", ""), re.I):
            continue
        link = ""
        a = row.find("a", href=True)
        if a:
            candidate = urljoin(base_url, a["href"])
            if _research_url_allowed(candidate):
                link = candidate
        score = _score_blob(f"{case_number} {parties} {date}", query)
        if query and score <= 0:
            continue
        results.append({
            "tipo": "decision_tribunal_apelaciones",
            "numero_caso": case_number,
            "partes": parties,
            "fecha": date,
            "url": link or base_url,
            "fuente": "Poder Judicial de Puerto Rico — Tribunal de Apelaciones",
            "verificado": True,
            "nivel_fuente": "fuente_primaria_oficial",
            "relevancia_indice": score,
            "advertencia": "La base pública contiene determinaciones finales desde enero de 2015 y excluye casos confidenciales.",
        })
    return results


async def _appeals_year_search(query: str, year: int, maximo: int) -> list[dict[str, Any]]:
    root = await _fetch(APPEALS_INDEX)
    month_links = _appeals_month_links(root.text, year)
    if not month_links:
        return []
    sem = asyncio.Semaphore(6)

    async def one(url: str) -> list[dict[str, Any]]:
        async with sem:
            try:
                response = await _fetch(url)
                return _parse_appeals_month(response.text, url, query)
            except Exception:
                return []

    batches = await asyncio.gather(*(one(url) for url in month_links[:12]))
    flat = [item for batch in batches for item in batch]
    flat.sort(key=lambda item: (-int(item["relevancia_indice"]), item["numero_caso"]))
    return flat[:maximo]


def _parse_public_search_results(html: str, base_url: str, query: str, maximo: int) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for article in soup.find_all(["article", "div"]):
        a = article.find("a", href=True)
        if not a:
            continue
        href = urljoin(base_url, a["href"])
        if not _research_url_allowed(href) or href in seen:
            continue
        title = jurisprudencia.clean(a.get_text(" ", strip=True))
        if len(title) < 12:
            continue
        text = jurisprudencia.clean(article.get_text(" ", strip=True))
        score = _score_blob(f"{title} {text}", query)
        if score <= 0:
            continue
        seen.add(href)
        results.append({
            "titulo": title,
            "url": href,
            "extracto_visible": text[:500],
            "relevancia": score,
        })
    results.sort(key=lambda item: -int(item["relevancia"]))
    return results[:maximo]


# ---------------------------------------------------------------------------
# Backward-compatible Tribunal Supremo tools, delegated to the tested core.
# ---------------------------------------------------------------------------

@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 10) -> dict[str, Any]:
    """Busca sentencias y opiniones del Tribunal Supremo de Puerto Rico."""
    return await jurisprudencia.buscar_sentencias(consulta, ano, maximo)


@mcp.tool()
async def investigar_sentencias(consulta: str, anos: str = "2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,2000,1999,1998", maximo: int = 5) -> dict[str, Any]:
    """Encuentra autoridades TSPR verificables por contenido del documento."""
    return await jurisprudencia.investigar_sentencias(consulta, anos, maximo)


@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str, Any]:
    """Localiza una cita TSPR exacta sin sustituir citas inexistentes."""
    return await jurisprudencia.buscar_por_cita(cita)


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_parrafos: int = 8) -> dict[str, Any]:
    """Lee una sentencia pública y devuelve pasajes extraídos de la fuente."""
    return await jurisprudencia.leer_sentencia(url, terminos, max_parrafos)


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Explica las fuentes y filtros del núcleo jurisprudencial."""
    return jurisprudencia.opciones_busqueda(consulta, campo)


@mcp.tool()
def estado() -> dict[str, Any]:
    """Compatibilidad con el diagnóstico histórico del núcleo de sentencias."""
    base = jurisprudencia.estado()
    base["producto_actual"] = PRODUCT_NAME
    base["version_producto"] = VERSION
    return base


# ---------------------------------------------------------------------------
# Expanded research tools.
# ---------------------------------------------------------------------------

@mcp.tool()
def catalogo_fuentes_juridicas() -> dict[str, Any]:
    """Lista las colecciones públicas integradas y su jerarquía de fuente."""
    return {
        "producto": PRODUCT_NAME,
        "version": VERSION,
        "fuentes_primarias": PRIMARY_SOURCE_CATALOG,
        "fuentes_secundarias": SECONDARY_SOURCE_CATALOG,
        "principio": "La fuente secundaria puede descubrir un desarrollo; la autoridad jurídica se verifica contra fuente primaria cuando sea posible.",
        "anti_alucinacion": True,
    }


@mcp.tool()
async def buscar_decisiones_apelaciones(consulta: str, ano: int = 2026, maximo: int = 10) -> dict[str, Any]:
    """Busca determinaciones finales públicas del Tribunal de Apelaciones."""
    maximo = max(1, min(int(maximo), 25))
    ano = int(ano)
    if ano < 2015 or ano > 2100:
        return {
            "consulta": consulta,
            "ano": ano,
            "resultados": [],
            "mensaje": "La colección pública indicada por el Poder Judicial comienza en enero de 2015.",
            "fuente": APPEALS_INDEX,
        }
    try:
        results = await _appeals_year_search(consulta, ano, maximo)
        return {
            "consulta": consulta,
            "ano": ano,
            "resultados": results,
            "total": len(results),
            "fuente": APPEALS_INDEX,
            "nivel_fuente": "fuente_primaria_oficial",
            "integridad": "No se inventan casos; los resultados se extraen del índice público del Poder Judicial.",
        }
    except Exception as exc:
        return {"consulta": consulta, "ano": ano, "resultados": [], "error": str(exc), "fuente": APPEALS_INDEX}


@mcp.tool()
async def buscar_biblioteca_juridica(consulta: str, maximo: int = 10) -> dict[str, Any]:
    """Busca enlaces visibles en la Biblioteca Jurídica Virtual del Departamento de Estado."""
    maximo = max(1, min(int(maximo), 25))
    try:
        response = await _fetch(STATE_LIBRARY)
        soup = BeautifulSoup(response.text, "html.parser")
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            title = jurisprudencia.clean(a.get_text(" ", strip=True))
            href = urljoin(STATE_LIBRARY, a["href"])
            if not title or href in seen or not _research_url_allowed(href):
                continue
            score = _score_blob(f"{title} {href}", consulta)
            if consulta and score <= 0:
                continue
            seen.add(href)
            hits.append({
                "titulo": title,
                "url": href,
                "fuente": "Biblioteca Jurídica Virtual — Departamento de Estado de Puerto Rico",
                "nivel_fuente": "fuente_primaria_oficial",
                "relevancia_indice": score,
                "verificado": True,
            })
        hits.sort(key=lambda item: -int(item["relevancia_indice"]))
        return {
            "consulta": consulta,
            "resultados": hits[:maximo],
            "total": min(len(hits), maximo),
            "fuente": STATE_LIBRARY,
            "colecciones": ["leyes", "resoluciones conjuntas", "reglamentos", "órdenes ejecutivas", "decretos", "proclamas"],
            "nota": "La Biblioteca Jurídica Virtual es fuente oficial; este método descubre enlaces visibles y no presume vigencia por mera aparición.",
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "error": str(exc), "fuente": STATE_LIBRARY}


@mcp.tool()
async def buscar_actualidad_juridica(consulta: str, maximo: int = 10) -> dict[str, Any]:
    """Busca contenido público de Microjuris Al Día como fuente secundaria de actualidad."""
    maximo = max(1, min(int(maximo), 25))
    search_url = f"{MICROJURIS_ALDIA}?s={quote_plus(consulta)}"
    try:
        response = await _fetch(search_url)
        results = _parse_public_search_results(response.text, MICROJURIS_ALDIA, consulta, maximo)
        return {
            "consulta": consulta,
            "resultados": results,
            "total": len(results),
            "fuente": "Microjuris Al Día",
            "url_busqueda": search_url,
            "nivel_fuente": "fuente_secundaria_publica",
            "uso": "descubrimiento, contexto y alerta de desarrollos; verificar autoridad primaria antes de citar una proposición jurídica",
            "sin_acceso_premium": True,
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "error": str(exc), "fuente": MICROJURIS_ALDIA, "sin_acceso_premium": True}


@mcp.tool()
async def investigar_derecho_pr(consulta: str, ano: int | None = None, maximo: int = 5) -> dict[str, Any]:
    """Investigación multi-fuente conservadora para Puerto Rico.

    Coordina jurisprudencia del Tribunal Supremo, decisiones públicas del
    Tribunal de Apelaciones y catálogos oficiales. No fusiona ni inventa una
    conclusión jurídica; entrega candidatos separados por fuente y jerarquía
    para que el cliente MCP analice la cuestión con trazabilidad.
    """
    maximo = max(1, min(int(maximo), 10))
    year = int(ano) if ano is not None else 2026

    supreme_task = jurisprudencia.official_search(consulta, ano, maximo)
    appeals_task = _appeals_year_search(consulta, year, maximo)
    results = await asyncio.gather(supreme_task, appeals_task, return_exceptions=True)

    supreme_raw = [] if isinstance(results[0], Exception) else [asdict(x) for x in results[0]]
    appeals_raw = [] if isinstance(results[1], Exception) else results[1]

    return {
        "consulta": consulta,
        "ano_prioritario": year,
        "autoridades_primarias": {
            "tribunal_supremo": supreme_raw,
            "tribunal_apelaciones": appeals_raw,
        },
        "fuentes_adicionales_disponibles": {
            "legislacion_reglamentos_ejecutivo": STATE_LIBRARY,
            "decisiones_administrativas_laborales": JRT_HOME,
        },
        "fuente_secundaria_para_actualidad": MICROJURIS_ALDIA,
        "regla_integridad": "Descubrimiento no equivale a holding. Cite solo proposiciones verificadas contra la autoridad primaria correspondiente.",
        "nota": "Para legislación, reglamentos, órdenes ejecutivas o decisiones laborales use las herramientas especializadas del MCP y verifique el documento fuente antes de concluir vigencia o alcance.",
    }


@mcp.tool()
def estado_investigacion_juridica() -> dict[str, Any]:
    """Diagnóstico de la investigación jurídica, incluyendo el corpus local persistente."""
    records = corpus_index.load_corpus()
    years = sorted({record.year for record in records})
    return {
        "producto": PRODUCT_NAME,
        "slug": PRODUCT_SLUG,
        "version": VERSION,
        "servidor_mcp": PRODUCT_SLUG,
        "servidor_base_interno": "puerto-rico-sentencias (núcleo de compatibilidad)",
        "arquitectura_busqueda": "corpus_local_first_then_live_expansion_and_verification",
        "corpus": {
            "disponible": bool(records),
            "persistente_local": True,
            "registros": len(records),
            "anos_cubiertos": years,
            "ruta": str(corpus_index.CORPUS_PATH),
            "busqueda_local_sin_red": True,
            "herramienta_diagnostico": "estado_corpus_jurisprudencia",
            "herramienta_busqueda_local": "buscar_corpus_jurisprudencia",
        },
        "colecciones": [
            "Corpus jurisprudencial local construido desde fuentes primarias oficiales",
            "Tribunal Supremo",
            "Tribunal de Apelaciones",
            "Biblioteca Jurídica Virtual del Departamento de Estado",
            "Junta de Relaciones del Trabajo",
            "Microjuris Al Día (solo contenido público/secundario)",
        ],
        "garantias": {
            "no_autoridades_inventadas": True,
            "no_texto_premium_microjuris": True,
            "no_elusion_de_paywall": True,
            "corpus_first": True,
            "fuente_primaria_preferida": True,
            "fuente_secundaria_etiquetada": True,
            "cache_oficial_identificada_como_cache": True,
        },
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
