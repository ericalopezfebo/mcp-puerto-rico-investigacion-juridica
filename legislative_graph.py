"""Automatic legislative-history graph for Puerto Rico statutes.

This module uses SUTRA/OSL as the official source of legislative-history facts.
It searches SUTRA's public laws interface for later acts whose titles or
explicit amendment blocks refer to a target law, verifies each candidate by
opening its SUTRA detail page, and builds a bounded graph of amendments,
repeals, substitutions and renumberings.

Important: absence of a repeal signal is not proof that a provision is current.
The graph reports what the official history explicitly shows and leaves
currency undetermined when the evidence is incomplete.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

import research_server
import vigencia_server

mcp = research_server.mcp

SUTRA_LAWS_SEARCH = "https://sutra.oslpr.org/prontuarios/leyes-aprobadas"
MAX_SEARCH_PAGES = 8
MAX_DETAIL_FETCHES = 60
DETAIL_CONCURRENCY = 6


@dataclass(frozen=True)
class LawId:
    number: int
    year: int

    @property
    def canonical(self) -> str:
        return f"Ley {self.number}-{self.year}"


@dataclass
class LegislativeEdge:
    source_law: str
    target_law: str
    relation: str
    provision: str
    title: str
    url: str
    official: bool = True


def parse_law_id(value: str) -> LawId | None:
    """Normalize common Puerto Rico act-number formats to ``Ley N-YYYY``."""
    text = research_server.jurisprudencia.normalize_text(value or "")
    patterns = [
        r"\bley\s+(?:num(?:ero)?\s*)?(\d{1,4})\s*[-/]\s*((?:19|20)\d{2})\b",
        r"\bley\s+(?:num(?:ero)?\s*)?(\d{1,4}).{0,50}\b((?:19|20)\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return LawId(int(match.group(1)), int(match.group(2)))
    return None


def _law_tokens(law: LawId) -> list[str]:
    return [
        law.canonical,
        f"Ley {law.number}-{law.year}",
        f"Ley Núm. {law.number}-{law.year}",
        f"Ley Num. {law.number}-{law.year}",
        f"Ley {law.number} de {law.year}",
    ]


def _detail_links(html: str, base_url: str = SUTRA_LAWS_SEARCH) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if not re.search(r"https://sutra\.oslpr\.org/prontuarios/leyes-aprobadas/\d+/?$", href, re.I):
            continue
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


def _extract_enacted_law(text: str) -> str:
    match = re.search(r"\bLey\s+(\d{1,4})-((?:19|20)\d{2})\b", text, re.I)
    if not match:
        return ""
    return f"Ley {int(match.group(1))}-{int(match.group(2))}"


def _extract_target_relations(text: str, target: LawId) -> list[tuple[str, str]]:
    """Return explicit relation/provision pairs tied to the target law."""
    clean = research_server.jurisprudencia.clean(text or "")
    normalized = research_server.jurisprudencia.normalize_text(clean)
    target_forms = [research_server.jurisprudencia.normalize_text(x) for x in _law_tokens(target)]
    relations: list[tuple[str, str]] = []

    # Find windows surrounding an explicit target-law mention. The official
    # SUTRA detail pages normally place the relation in an Enmienda(s) block.
    for form in target_forms:
        start = 0
        while True:
            idx = normalized.find(form, start)
            if idx < 0:
                break
            window = normalized[max(0, idx - 120): idx + len(form) + 420]
            relation = ""
            if re.search(r"\bderog", window):
                relation = "deroga"
            elif re.search(r"\bsustitu", window):
                relation = "sustituye"
            elif re.search(r"\breenumera", window):
                relation = "reenumera"
            elif re.search(r"\benmiend", window):
                relation = "enmienda"
            if relation:
                provision_match = re.search(
                    r"((?:art[ií]culo|secci[oó]n|inciso|apartado)s?\s+[^.;]{1,160})",
                    clean[max(0, idx - 100): idx + len(form) + 420],
                    re.I,
                )
                provision = research_server.jurisprudencia.clean(provision_match.group(1)) if provision_match else ""
                relations.append((relation, provision[:220]))
            start = idx + len(form)

    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in relations:
        if row not in seen:
            seen.add(row)
            unique.append(row)
    return unique


def parse_sutra_law_detail(html: str, url: str, target: LawId) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = research_server.jurisprudencia.clean(soup.get_text(" ", strip=True))
    enacted = _extract_enacted_law(text)
    title = ""
    title_match = re.search(r"T[ií]tulo:\s*(.+?)(?=Documento\(s\)|Tr[aá]mites|Enmienda\(s\)|$)", text, re.I)
    if title_match:
        title = research_server.jurisprudencia.clean(title_match.group(1))[:1800]
    relations = _extract_target_relations(text, target)
    return {
        "law": enacted,
        "title": title,
        "url": url,
        "relations": [
            {"relation": relation, "provision": provision}
            for relation, provision in relations
        ],
        "mentions_target": bool(relations),
        "source": "SUTRA / Oficina de Servicios Legislativos de Puerto Rico",
    }


def _search_url_variants(target: LawId, page: int = 1) -> list[str]:
    """Generate conservative variants for SUTRA's public title filter.

    SUTRA has changed parameter names across versions. Trying a small set of
    official-portal query variants is safer than depending on an undocumented
    private endpoint. Candidates are never trusted until their detail page is
    opened and the target relationship is explicitly verified there.
    """
    phrases = [f"Ley {target.number}-{target.year}", f"{target.number}-{target.year}"]
    param_names = ["frase", "frase_titulo", "titulo", "search"]
    urls: list[str] = []
    for phrase in phrases:
        for param in param_names:
            query = {param: phrase}
            if page > 1:
                query["page"] = str(page)
            urls.append(f"{SUTRA_LAWS_SEARCH}?{urlencode(query)}")
    return urls


async def _fetch_text(url: str) -> str:
    response = await research_server._fetch(url)
    return response.text


async def _discover_candidate_urls(target: LawId) -> list[str]:
    """Discover candidate SUTRA law-detail URLs using only SUTRA public pages."""
    seen: set[str] = set()
    discovered: list[str] = []

    # First search the public filtered interface using compatible parameter
    # variants. Stop early once a variant produces useful detail links.
    for page in range(1, MAX_SEARCH_PAGES + 1):
        page_found = False
        for url in _search_url_variants(target, page):
            try:
                html = await _fetch_text(url)
            except Exception:
                continue
            links = _detail_links(html)
            if links:
                page_found = True
            for link in links:
                if link not in seen:
                    seen.add(link)
                    discovered.append(link)
                    if len(discovered) >= MAX_DETAIL_FETCHES:
                        return discovered
        if page > 1 and not page_found:
            break
    return discovered


async def _verify_candidates(target: LawId, urls: list[str]) -> list[LegislativeEdge]:
    sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

    async def one(url: str) -> list[LegislativeEdge]:
        async with sem:
            try:
                html = await _fetch_text(url)
                parsed = parse_sutra_law_detail(html, url, target)
            except Exception:
                return []
            if not parsed["mentions_target"] or not parsed["law"]:
                return []
            out: list[LegislativeEdge] = []
            for rel in parsed["relations"]:
                out.append(
                    LegislativeEdge(
                        source_law=parsed["law"],
                        target_law=target.canonical,
                        relation=rel["relation"],
                        provision=rel["provision"],
                        title=parsed["title"],
                        url=url,
                    )
                )
            return out

    batches = await asyncio.gather(*(one(url) for url in urls[:MAX_DETAIL_FETCHES]))
    edges = [edge for batch in batches for edge in batch]
    # Stable chronological ordering when the source-law year/number is parseable.
    def key(edge: LegislativeEdge) -> tuple[int, int, str]:
        parsed = parse_law_id(edge.source_law)
        return (parsed.year if parsed else 9999, parsed.number if parsed else 9999, edge.url)
    return sorted(edges, key=key)


def _article_matches(provision: str, article: str) -> bool:
    if not article:
        return True
    p = research_server.jurisprudencia.normalize_text(provision)
    a = research_server.jurisprudencia.normalize_text(article)
    if a in p:
        return True
    nums_a = re.findall(r"\d+(?:\.\d+)?", a)
    nums_p = re.findall(r"\d+(?:\.\d+)?", p)
    return bool(nums_a and any(n in nums_p for n in nums_a))


def summarize_graph(target: LawId, edges: list[LegislativeEdge], article: str = "") -> dict[str, Any]:
    relevant = [e for e in edges if _article_matches(e.provision, article)] if article else list(edges)
    direct_repeals = [e for e in relevant if e.relation == "deroga"]
    amendments = [e for e in relevant if e.relation in {"enmienda", "reenumera", "sustituye"}]

    if direct_repeals:
        status = "derogacion_detectada_en_fuente_oficial"
    elif amendments:
        status = "enmendada; vigencia_actual_requiere_texto_consolidado"
    else:
        status = "no_determinada"

    return {
        "ley": target.canonical,
        "articulo": article,
        "estado_vigencia": status,
        "puede_afirmarse_vigente": False,
        "derogacion_explicita_detectada": bool(direct_repeals),
        "enmiendas_explicitas_detectadas": len(amendments),
        "afectaciones": [asdict(edge) for edge in relevant],
        "regla": (
            "El historial SUTRA puede demostrar una derogación o enmienda explícita, pero la ausencia de una afectación detectada "
            "no prueba por sí sola que la disposición siga vigente. Para afirmar texto vigente se requiere además confirmar el texto oficial aplicable/consolidado."
        ),
    }


async def build_legislative_history(law: str, article: str = "") -> dict[str, Any]:
    target = parse_law_id(law)
    if target is None:
        return {
            "ley": law,
            "articulo": article,
            "estado_vigencia": "no_determinada",
            "puede_afirmarse_vigente": False,
            "error": "No pude normalizar la ley. Usa un identificador como 'Ley 80-1976'.",
        }

    urls = await _discover_candidate_urls(target)
    edges = await _verify_candidates(target, urls)
    summary = summarize_graph(target, edges, article)
    summary.update({
        "fuente": "SUTRA / Oficina de Servicios Legislativos de Puerto Rico",
        "estrategia": "busqueda_oficial -> verificacion_detalle -> grafo_afectaciones",
        "candidatos_sutra_examinados": min(len(urls), MAX_DETAIL_FETCHES),
        "afectaciones_totales_verificadas": len(edges),
        "consulta_en_vivo": True,
    })
    return summary


@mcp.tool()
async def construir_historial_legislativo(ley: str, articulo: str = "") -> dict[str, Any]:
    """Busca automáticamente en SUTRA leyes posteriores que afecten una ley o artículo.

    Usa el portal público oficial de SUTRA para descubrir candidatos y abre cada
    detalle antes de aceptar una relación de enmienda, derogación, sustitución o
    reenumeración. No necesita una URL semilla del usuario. La ausencia de una
    derogación detectada NO se interpreta automáticamente como vigencia.
    """
    return await build_legislative_history(ley, articulo)


@mcp.tool()
async def verificar_vigencia_ley(ley: str, articulo: str = "") -> dict[str, Any]:
    """Ejecuta el historial automático de SUTRA y devuelve un estado conservador.

    Si encuentra derogación explícita, la reporta. Si encuentra enmiendas, las
    enumera. Si no encuentra evidencia suficiente, devuelve ``no_determinada``.
    Nunca afirma vigencia positiva solo por ausencia de resultados.
    """
    return await build_legislative_history(ley, articulo)
