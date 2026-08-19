"""Legislative currency / amendment verification for Puerto Rico legal research.

This module adds a conservative verification layer for statutes and specific
provisions. SUTRA/OSL is treated as the official legislative-history source.
CodeXPR may be useful for discovery, but it is never sufficient by itself to
mark a law or provision as currently effective.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import research_server

mcp = research_server.mcp

SUTRA_HOME = "https://sutra.oslpr.org/"
CODEXPR_HOME = "https://www.codexpr.ai/"
OFFICIAL_CURRENCY_HOSTS = {
    "sutra.oslpr.org",
    "www.oslpr.org",
    "oslpr.org",
    "bibliotecavirtual.estado.pr.gov",
    "estado.pr.gov",
    "www.estado.pr.gov",
}


def _official_currency_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in OFFICIAL_CURRENCY_HOSTS
    except Exception:
        return False


def _clean(text: str) -> str:
    return research_server.jurisprudencia.clean(text or "")


def parse_sutra_amendment_page(html: str, ley_objetivo: str = "", articulo: str = "") -> dict[str, Any]:
    """Extract only explicit amendment/repeal signals visible on a SUTRA page.

    This parser is intentionally conservative. It does not infer that a law is
    fully current merely because SUTRA lists an amendment. It reports the
    explicit signals it can see and otherwise leaves currency undetermined.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = _clean(soup.get_text(" ", strip=True))
    normalized = research_server.jurisprudencia.normalize_text(text)
    target = research_server.jurisprudencia.normalize_text(ley_objetivo)
    article = research_server.jurisprudencia.normalize_text(articulo)

    signals: list[dict[str, str]] = []
    patterns = [
        ("deroga", r"\bderog(?:a|an|ado|ada|ar)\b[^.;]{0,180}"),
        ("enmienda", r"\benmienda(?:n|da|do|r)?\b[^.;]{0,180}"),
        ("sustituye", r"\bsustitu(?:ye|yen|ido|ida|ir)\b[^.;]{0,180}"),
        ("reenumera", r"\breenumera(?:n|do|da|r)?\b[^.;]{0,180}"),
    ]
    for kind, pattern in patterns:
        for match in re.finditer(pattern, normalized, re.I):
            snippet = _clean(text[max(0, match.start() - 40): match.end() + 40])
            snorm = research_server.jurisprudencia.normalize_text(snippet)
            if target and target not in snorm and target not in normalized[max(0, match.start()-240):match.end()+240]:
                continue
            if article and article not in snorm:
                # Keep law-level signals if an article was requested, but mark scope.
                scope = "ley; articulo solicitado no confirmado en este fragmento"
            else:
                scope = "articulo" if article else "ley"
            signals.append({"tipo": kind, "alcance": scope, "texto_visible": snippet[:500]})

    # Deduplicate visible signals without inventing chronology or legal effect.
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in signals:
        key = (item["tipo"], item["texto_visible"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return {
        "ley_consultada": ley_objetivo,
        "articulo_consultado": articulo,
        "senales_explicitas": unique,
        "total_senales": len(unique),
        "estado_vigencia": "no_determinado_por_esta_pagina",
        "puede_afirmarse_vigente": False,
        "regla": (
            "Una página de trámite o una sola ley enmendatoria no basta para afirmar vigencia total. "
            "Las señales se reportan literalmente; la conclusión de vigencia exige revisar el historial oficial completo y el texto aplicable."
        ),
    }


@mcp.tool()
async def verificar_vigencia_legislativa(
    ley: str,
    url_oficial: str,
    articulo: str = "",
) -> dict[str, Any]:
    """Verifica señales de enmienda/derogación en una URL oficial, sin adivinar vigencia.

    USA ESTA HERRAMIENTA antes de presentar una ley, código o artículo como
    "vigente", "actual" o "no derogado". La URL debe pertenecer a SUTRA/OSL,
    Departamento de Estado u otra fuente oficial permitida. CodeXPR, LexJuris,
    Microjuris y otros índices secundarios pueden descubrir una autoridad, pero
    nunca bastan por sí solos para marcarla vigente.

    Si la evidencia oficial disponible no resuelve la vigencia, devuelve
    `estado_vigencia = no_determinada` y `puede_afirmarse_vigente = false`.
    """
    if not _official_currency_url(url_oficial):
        return {
            "ley": ley,
            "articulo": articulo,
            "url": url_oficial,
            "estado_vigencia": "no_determinada",
            "puede_afirmarse_vigente": False,
            "error": "La URL suministrada no pertenece a una fuente oficial permitida para verificar vigencia.",
            "regla": "Fuentes secundarias sirven para descubrimiento, no para afirmar vigencia.",
        }

    try:
        response = await research_server._fetch(url_oficial)
        parsed = parse_sutra_amendment_page(response.text, ley, articulo)
        parsed.update({
            "ley": ley,
            "articulo": articulo,
            "url": url_oficial,
            "fuente_verificacion": "fuente_oficial",
            "fecha_verificacion": "consulta_en_vivo_al_momento_de_la_llamada",
        })
        if not parsed["senales_explicitas"]:
            parsed["estado_vigencia"] = "no_determinada"
            parsed["puede_afirmarse_vigente"] = False
            parsed["advertencia"] = (
                "No se detectaron señales explícitas suficientes en esta página. "
                "No interpretar ausencia de señal como prueba de vigencia."
            )
        return parsed
    except Exception as exc:
        return {
            "ley": ley,
            "articulo": articulo,
            "url": url_oficial,
            "estado_vigencia": "no_determinada",
            "puede_afirmarse_vigente": False,
            "error": str(exc),
            "regla": "Un fallo de acceso nunca se convierte en una presunción de vigencia.",
        }


@mcp.tool()
def politica_vigencia_fuentes() -> dict[str, Any]:
    """Explica la jerarquía usada para vigencia y el rol de SUTRA/CodeXPR."""
    return {
        "fuentes_oficiales_preferidas": [
            "SUTRA / Oficina de Servicios Legislativos",
            "Biblioteca Jurídica Virtual / Departamento de Estado",
        ],
        "fuentes_secundarias_descubrimiento": ["CodeXPR", "LexJuris", "Microjuris"],
        "regla_obligatoria": (
            "No presentar una ley, código, reglamento o disposición como vigente/no derogada basándose únicamente en una fuente secundaria o en un PDF histórico."
        ),
        "estados_permitidos": [
            "vigente_verificado",
            "enmendada",
            "parcialmente_derogada",
            "derogada",
            "sustituida",
            "vigencia_futura",
            "no_determinada",
        ],
        "estado_por_defecto": "no_determinada",
        "cookie_policy": "No se requieren ni almacenan cookies personales o credenciales para esta capa.",
    }
