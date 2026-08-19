"""Public-source expansion for MCP Puerto Rico Sentencias.

This module adds Microjuris-like discovery across PUBLIC legal sources without
copying subscription databases, bypassing authentication, or redistributing
proprietary annotations. Primary authority remains the preferred source.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

import server

mcp = server.mcp

PUBLIC_COLLECTIONS: dict[str, dict[str, str]] = {
    "tribunal_supremo": {
        "nombre": "Decisiones del Tribunal Supremo de Puerto Rico",
        "url": "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/",
        "tipo": "fuente_primaria",
    },
    "tribunal_apelaciones": {
        "nombre": "Decisiones finales del Tribunal de Apelaciones",
        "url": "https://poderjudicial.pr/tribunal-apelaciones/decisiones-finales-del-tribunal-de-apelaciones/",
        "tipo": "fuente_primaria",
    },
    "biblioteca_juridica_estado": {
        "nombre": "Biblioteca Jurídica Virtual del Departamento de Estado",
        "url": "https://www.estado.pr.gov/",
        "tipo": "fuente_primaria",
    },
    "reglamentos": {
        "nombre": "Registro de Reglamentos del Departamento de Estado",
        "url": "https://www.estado.pr.gov/documentos-administrativos",
        "tipo": "fuente_primaria",
    },
    "ordenes_ejecutivas": {
        "nombre": "Órdenes Ejecutivas del Gobernador de Puerto Rico",
        "url": "https://www.estado.pr.gov/ordenes-ejecutivas",
        "tipo": "fuente_primaria",
    },
    "junta_relaciones_trabajo": {
        "nombre": "Junta de Relaciones del Trabajo - Decisiones y Órdenes",
        "url": "https://www.jrt.pr.gov/",
        "tipo": "fuente_primaria",
    },
    "microjuris_aldia": {
        "nombre": "Microjuris Al Día",
        "url": "https://aldia.microjuris.com/",
        "tipo": "fuente_secundaria_noticias",
    },
}

PUBLIC_HOSTS = {
    "poderjudicial.pr", "www.poderjudicial.pr", "dts.poderjudicial.pr",
    "estado.pr.gov", "www.estado.pr.gov", "jrt.pr.gov", "www.jrt.pr.gov",
    "aldia.microjuris.com",
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _norm(value: str) -> str:
    value = _clean(value).lower()
    return value.translate(str.maketrans("áéíóúü", "aeiouu"))


def _public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in PUBLIC_HOSTS
    except Exception:
        return False


async def _fetch(url: str) -> str:
    if not _public_url(url):
        raise ValueError("URL fuera de las fuentes públicas permitidas")
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "mcp-puerto-rico-sentencias/0.6 public-legal-research"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _extract_links(html: str, base_url: str, consulta: str, maximo: int) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    terms = [t for t in re.findall(r"[\wÀ-ÿ]+", _norm(consulta)) if len(t) > 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        title = _clean(a.get_text(" ", strip=True))
        href = urljoin(base_url, a.get("href", ""))
        if not title or not _public_url(href) or href in seen:
            continue
        seen.add(href)
        haystack = _norm(f"{title} {href}")
        score = sum(1 for term in terms if term in haystack)
        if consulta and score == 0:
            continue
        scored.append((score, {"titulo": title, "url": href, "coincidencias": score}))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["titulo"]))
    return [item for _, item in scored[:maximo]]


@mcp.tool()
def colecciones_juridicas() -> dict[str, Any]:
    """Lista las colecciones públicas disponibles y distingue autoridad primaria de noticias."""
    return {
        "colecciones": PUBLIC_COLLECTIONS,
        "principio": "Las fuentes primarias oficiales tienen prioridad. Las noticias se usan para descubrir desarrollos, no como sustituto de la autoridad primaria.",
        "limites": "No accede a contenido de suscripción, no usa credenciales, no evade paywalls y no replica anotaciones propietarias de terceros.",
    }


@mcp.tool()
async def buscar_ordenes_ejecutivas(consulta: str = "", maximo: int = 10) -> dict[str, Any]:
    """Busca órdenes ejecutivas en la página pública oficial del Departamento de Estado."""
    maximo = max(1, min(int(maximo), 30))
    source = PUBLIC_COLLECTIONS["ordenes_ejecutivas"]
    try:
        html = await _fetch(source["url"])
        return {
            "consulta": consulta,
            "coleccion": source["nombre"],
            "tipo_fuente": source["tipo"],
            "fuente": source["url"],
            "resultados": _extract_links(html, source["url"], consulta, maximo),
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "error": "No fue posible consultar la fuente oficial.", "detalle_tecnico": str(exc)}


@mcp.tool()
async def buscar_apelaciones(consulta: str = "", maximo: int = 10) -> dict[str, Any]:
    """Descubre enlaces públicos del índice oficial del Tribunal de Apelaciones.

    El Poder Judicial indica que esta colección contiene determinaciones finales
    desde enero de 2015, salvo asuntos confidenciales. Esta herramienta es de
    descubrimiento; una futura etapa puede añadir lectura/ranking de cada PDF.
    """
    maximo = max(1, min(int(maximo), 30))
    source = PUBLIC_COLLECTIONS["tribunal_apelaciones"]
    try:
        html = await _fetch(source["url"])
        return {
            "consulta": consulta,
            "coleccion": source["nombre"],
            "tipo_fuente": source["tipo"],
            "fuente": source["url"],
            "resultados": _extract_links(html, source["url"], consulta, maximo),
            "nota": "La disponibilidad oficial comienza en 2015 y excluye casos confidenciales.",
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "error": "No fue posible consultar el índice oficial.", "detalle_tecnico": str(exc)}


@mcp.tool()
async def buscar_actualidad_juridica(consulta: str, maximo: int = 10) -> dict[str, Any]:
    """Busca noticias jurídicas públicas en Microjuris Al Día.

    Solo consulta la búsqueda pública del sitio y devuelve título/enlace. No
    accede al producto de suscripción de Microjuris ni copia su base de datos.
    Las noticias son fuentes secundarias: cualquier proposición jurídica debe
    verificarse después contra sentencia, ley, reglamento u otra fuente primaria.
    """
    maximo = max(1, min(int(maximo), 20))
    url = f"https://aldia.microjuris.com/?s={quote_plus(consulta)}"
    try:
        html = await _fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for selector in ("article h2 a", "article h3 a", "h2.entry-title a", "h3.entry-title a"):
            for a in soup.select(selector):
                href = urljoin(url, a.get("href", ""))
                title = _clean(a.get_text(" ", strip=True))
                if title and _public_url(href) and href not in seen:
                    seen.add(href)
                    results.append({"titulo": title, "url": href, "tipo_fuente": "secundaria"})
                    if len(results) >= maximo:
                        break
            if len(results) >= maximo:
                break
        if not results:
            results = [
                {"titulo": r["titulo"], "url": r["url"], "tipo_fuente": "secundaria"}
                for r in _extract_links(html, url, consulta, maximo)
            ]
        return {
            "consulta": consulta,
            "fuente": "https://aldia.microjuris.com/",
            "resultados": results[:maximo],
            "advertencia": "Noticias/análisis secundarios. Verifica la regla jurídica contra la autoridad primaria antes de citarla como derecho vigente.",
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "error": "No fue posible consultar la búsqueda pública de actualidad jurídica.", "detalle_tecnico": str(exc)}


@mcp.tool()
def mapa_fuentes_publicas(tema: str = "") -> dict[str, Any]:
    """Orienta qué colección pública consultar para una investigación jurídica."""
    return {
        "tema": tema,
        "jurisprudencia_supremo": PUBLIC_COLLECTIONS["tribunal_supremo"],
        "jurisprudencia_apelaciones": PUBLIC_COLLECTIONS["tribunal_apelaciones"],
        "leyes_resoluciones_reglamentos": PUBLIC_COLLECTIONS["biblioteca_juridica_estado"],
        "ordenes_ejecutivas": PUBLIC_COLLECTIONS["ordenes_ejecutivas"],
        "laboral_administrativo": PUBLIC_COLLECTIONS["junta_relaciones_trabajo"],
        "actualidad": PUBLIC_COLLECTIONS["microjuris_aldia"],
        "metodo_recomendado": [
            "1. Descubrir el tema o desarrollo reciente.",
            "2. Identificar la autoridad primaria citada.",
            "3. Recuperar el documento oficial.",
            "4. Extraer pasaje/página exactos.",
            "5. Informar cualquier dato que no pudo verificarse en vez de inferirlo.",
        ],
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
