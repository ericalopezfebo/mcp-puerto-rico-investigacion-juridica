"""MCP server for verifiable Puerto Rico jurisprudence research.

Design goal: source-first legal research. The server never invents cases,
citations, holdings, dates, party names, judges, docket numbers, or quotations.
It searches public documents, extracts source text, and returns the exact source
URL plus passages that were actually extracted from that source.
"""
from __future__ import annotations

import asyncio
import io
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
ALLOWED_HOSTS = (
    "poderjudicial.pr",
    "www.poderjudicial.pr",
    "dts.poderjudicial.pr",
    "lexjuris.com",
    "www.lexjuris.com",
)
TIMEOUT = 25.0
MAX_DOCUMENT_CHARS = 120_000

# content_search() budget: the official year index carries no topical text
# (confirmed by inspection — each row is just the bare citation), so there is
# no reliable way to rank candidates by topic before opening a PDF, and a
# thin random/even sample of a year (e.g. 20 of ~150) has poor odds of
# hitting the 1-3 decisions that actually match a specific topic — measured
# directly: sampling ~13% of a year missed known-relevant decisions. A full
# year (~150 PDFs), read with a shared keep-alive HTTP client at concurrency
# 20, measured ~30s and found every known-relevant decision. So instead of
# spreading a small budget thin across many years, each round reads ONE
# requested year as close to fully as the remaining budget allows — full
# recall for whichever years actually get processed — and the search stops
# expanding to older years as soon as enough verified results are found.
YEAR_GROUP_SIZE = 1
PDF_READS_PER_ROUND = 160
MAX_TOTAL_PDF_READS = 180
PDF_READ_CONCURRENCY = 20


@dataclass
class Decision:
    title: str
    url: str
    source: str
    citation: str = ""
    case_number: str = ""
    date: str = ""
    judge: str = ""
    subject: str = ""
    snippet: str = ""
    page: int | None = None
    relevance_score: float = 0.0
    verified: bool = False
    verification_status: str = "unverified"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_citation(value: str) -> str:
    return clean(value).upper().replace("-", " ")


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ü", "u")
    value = re.sub(r"[^a-z0-9ñ\s]", " ", value)
    return clean(value)


def extract_citation(text: str) -> str:
    match = re.search(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I)
    return clean(match.group(0)) if match else ""


def extract_case_number(text: str) -> str:
    patterns = (
        r"\b([A-Z]{1,5}-\d{2,5}-\d{1,6})\b",
        r"\b([A-Z]{1,5}\s+\d{2,5}-\d{1,6})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            return clean(match.group(1))
    return ""


# Role/recourse-type words that appear in the standard Poder Judicial cover
# page caption block, alongside the actual party names. Stripped from the
# extracted case name so it contains only the parties; this is a fixed,
# observed vocabulary, never a guess.
_CAPTION_ROLE_WORDS = {
    "peticionario", "peticionaria", "recurrido", "recurrida", "recurrente",
    "apelante", "apelado", "apelada", "querellante", "querellado", "querellada",
    "demandante", "demandado", "demandada", "promovido", "promovida",
}
_CAPTION_RECOURSE_WORDS = {"certiorari", "apelacion", "revision", "mandamus", "habeas corpus"}


def extract_cover_metadata(paragraphs: list[str]) -> dict[str, str]:
    """Parse the standard Poder Judicial cover page (page 1 of every TSPR PDF).

    Every decision opens with a fixed layout: institutional header, party
    caption (or "In re:" for single-party matters), the TSPR citation, then
    labeled "Número del Caso:" and "Fecha:" lines. Only fields that literally
    match this known, observed layout are returned; anything the layout
    doesn't confirm stays empty rather than inferred.
    """
    page1_lines = [
        clean(re.sub(r"^\[página 1\]\s*", "", p))
        for p in paragraphs
        if p.startswith("[página 1]")
    ]
    result = {"case_number": "", "date": "", "case_name": ""}

    for line in page1_lines:
        match = re.match(r"N[uú]mero del [Cc]aso:\s*(.+)", line)
        if match:
            result["case_number"] = clean(match.group(1))
        match = re.match(r"Fecha:\s*(.+)", line)
        if match:
            result["date"] = clean(match.group(1))

    try:
        start = page1_lines.index("EN EL TRIBUNAL SUPREMO DE PUERTO RICO") + 1
    except ValueError:
        start = None
    if start is not None:
        end = None
        for i in range(start, len(page1_lines)):
            if re.match(r"^(?:19|20)\d{2}\s*TSPR\s*\d+$", page1_lines[i], re.I):
                end = i
                break
        if end is not None and end > start:
            caption_lines = page1_lines[start:end]
            has_marker = any(l == "v." for l in caption_lines) or any(
                normalize_text(l).startswith("in re") for l in caption_lines
            )
            if has_marker:
                kept = [
                    l for l in caption_lines
                    if normalize_text(l) not in _CAPTION_ROLE_WORDS
                    and normalize_text(l) not in _CAPTION_RECOURSE_WORDS
                ]
                if kept:
                    result["case_name"] = clean(" ".join(kept))
    return result


def source_name(url: str) -> str:
    return "LexJuris" if "lexjuris.com" in url.lower() else "Poder Judicial de Puerto Rico"


def allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
    except Exception:
        return False


_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """A single shared client, reused for the life of the server process.

    A fresh httpx.AsyncClient per request means a fresh TCP+TLS handshake
    per request. Measured against the real official host: fetching the same
    40 PDFs went from ~10.2s to ~5.7s just by reusing one client (keep-alive
    connection pooling) instead of opening a new one every time — the
    single biggest lever available for staying inside an MCP client's
    request timeout on a multi-document search. Never explicitly closed:
    the OS reclaims the sockets when the server process exits.
    """
    global _http_client
    if _http_client is None:
        headers = {
            "User-Agent": "mcp-puerto-rico-sentencias/1.0 (legal-research client)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
        }
        _http_client = httpx.AsyncClient(
            timeout=TIMEOUT, follow_redirects=True, headers=headers,
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=20),
        )
    return _http_client


async def fetch_response(url: str) -> httpx.Response:
    if not allowed_url(url):
        raise ValueError("URL no permitida")
    client = await get_http_client()
    response = await client.get(url)
    response.raise_for_status()
    return response


async def fetch_text(url: str) -> str:
    response = await fetch_response(url)
    return response.text


def looks_like_year_page(url: str) -> bool:
    return bool(re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})/?$", url.lower()))


def year_from_url(url: str) -> int | None:
    match = re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})", url.lower())
    return int(match.group(1)) if match else None


def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    """Extract only facts visible in an index page; never infer metadata."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[Decision] = []
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        haystack = f"{text} {href}"
        citation = extract_citation(haystack)
        href_lower = href.lower()
        looks_like_decision = bool(
            citation
            or href_lower.endswith(".pdf")
            or any(token in haystack.upper() for token in ("SENTENCIA", "OPINIÓN", "OPINION", "TSPR"))
        )
        if not looks_like_decision:
            continue
        citation_year = int(re.search(r"\d{4}", citation).group(0)) if citation else year_from_url(href)
        if year is not None and citation_year is not None and citation_year != year:
            continue
        verified = bool(href and citation)
        results.append(
            Decision(
                title=text,
                url=href,
                source=source_name(href),
                citation=citation,
                case_number=extract_case_number(haystack),
                verified=verified,
                verification_status="verified_source_identifier" if verified else "source_found_identifier_unconfirmed",
            )
        )
    seen: set[str] = set()
    unique: list[Decision] = []
    for result in results:
        if result.url not in seen:
            seen.add(result.url)
            unique.append(result)
    return unique


_year_index_cache: dict[int, list[Decision]] = {}


async def get_year_links(year: int) -> list[Decision]:
    """Fetch the official Tribunal Supremo index for one year.

    The year page contains the authoritative TSPR citation, matter/subject,
    case number and link to the decision PDF. We fetch that page directly.
    Cached in memory for the life of the process: the index page is large
    (~600KB) and fetching it is the single slowest step in a search, so a
    session that runs several searches or looks up several citations should
    not re-download the same year's index every time.
    """
    if year in _year_index_cache:
        return _year_index_cache[year]
    year_url = (
        f"https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
        f"decisiones-del-tribunal-supremo-{year}/"
    )
    result: list[Decision] = []
    try:
        year_html = await fetch_text(year_url)
        result = dedupe_decisions(parse_index(year_html, year_url, year))
    except Exception:
        # Conservative fallback: discover the year page from the official root.
        try:
            main_html = await fetch_text(OFFICIAL_INDEX)
            main_links = parse_index(main_html, OFFICIAL_INDEX)
            page_links = [
                r for r in main_links
                if looks_like_year_page(r.url) and year_from_url(r.url) == year
            ]
            if page_links:
                year_html = await fetch_text(page_links[0].url)
                result = dedupe_decisions(parse_index(year_html, page_links[0].url, year))
        except Exception:
            pass
    if result:
        _year_index_cache[year] = result
    return result


def sample_evenly(items: list[Decision], count: int) -> list[Decision]:
    """Deterministically pick `count` items spread across the list order.

    Uses fixed-step index selection (no randomness) so that identical inputs
    always produce identical selections, matching the project's verifiability
    requirement of reproducible search results.
    """
    n = len(items)
    if count <= 0 or n == 0:
        return []
    if count >= n:
        return list(items)
    step = n / count
    indices = sorted({int(i * step) for i in range(count)})
    i = 0
    while len(indices) < count and i < n:
        if i not in indices:
            indices.append(i)
        i += 1
    return [items[i] for i in sorted(indices)[:count]]


def dedupe_decisions(items: list[Decision]) -> list[Decision]:
    seen: set[str] = set()
    out: list[Decision] = []
    for item in items:
        if item.url not in seen:
            seen.add(item.url)
            out.append(item)
    return out


# Small, deliberately conservative expansion dictionary. It improves recall;
# it does not create authorities or legal conclusions.
LEGAL_SYNONYMS = {
    "pension alimenticia": [
        "pension alimenticia", "pensión alimenticia", "pension alimentaria", "pensión alimentaria",
        "alimentos", "obligacion alimentaria", "obligación alimentaria", "obligaciones alimentarias",
        "alimentante", "alimentista", "manutencion", "manutención", "cuota alimentaria", "child support",
    ],
    "alimentos": [
        "alimentos", "pension alimenticia", "pensión alimenticia", "pension alimentaria",
        "pensión alimentaria", "obligacion alimentaria", "obligación alimentaria",
        "alimentante", "alimentista", "manutencion", "manutención",
    ],
    "custodia": ["custodia", "guarda", "patria potestad", "relaciones paterno filiales"],
    "divorcio": ["divorcio", "divorciado", "disolucion matrimonial", "disolución matrimonial"],
    "menor": ["menor", "menores", "niño", "niña", "hijo", "hija"],
}


QUERY_STOPWORDS = {
    "busca", "buscar", "encuentra", "encontrar", "dame", "dame", "mejores", "mejor",
    "sentencia", "sentencias", "casos", "caso", "ayuden", "ayuda", "apoyar",
    "apoye", "apoyen", "argumento", "argumentos", "sobre", "para", "con", "una",
    "las", "los", "del", "que", "como", "esta", "este", "estas", "estos",
    "quiero", "necesito", "relevante", "relevantes", "jurisprudencia",
    # Institutional/boilerplate words present in essentially every decision
    # regardless of topic (e.g. "EN EL TRIBUNAL SUPREMO DE PUERTO RICO" is on
    # every cover page); useless as thematic signal, so they don't count as
    # distinct matches for a complex natural-language question.
    "tribunal", "supremo", "puerto", "rico", "decision", "decisiones",
    "corte", "autoridad", "autoridades", "opinion", "opiniones",
}

def query_terms(query: str) -> list[str]:
    raw = [
        t for t in re.findall(r"[\wÀ-ÿ]+", query.lower())
        if len(t) > 2 and t not in QUERY_STOPWORDS
    ]
    expanded: list[str] = list(raw)
    qnorm = normalize_text(query)
    for key, synonyms in LEGAL_SYNONYMS.items():
        if normalize_text(key) in qnorm or any(normalize_text(s) in qnorm for s in synonyms):
            expanded.extend(synonyms)
    # Preserve order, remove duplicates.
    seen: set[str] = set()
    return [x for x in expanded if not (normalize_text(x) in seen or seen.add(normalize_text(x)))]


def extract_html_document(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    blocks: list[str] = []
    for tag in soup.find_all(["p", "blockquote", "li"]):
        value = clean(tag.get_text(" ", strip=True))
        if value and len(value) >= 20:
            blocks.append(value)
    if blocks:
        return "\n\n".join(blocks), blocks
    text = clean(soup.get_text(" ", strip=True))
    return text, [text] if text else []


def extract_pdf_document(content: bytes) -> tuple[str, list[str]]:
    reader = PdfReader(io.BytesIO(content))
    page_blocks: list[str] = []
    paragraphs: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.replace("\r", "\n")
        raw_blocks = re.split(r"\n\s*\n+", page_text)
        page_paragraphs = [clean(block) for block in raw_blocks if clean(block)]
        for block in page_paragraphs:
            paragraphs.append(f"[página {page_number}] {block}")
        if page_paragraphs:
            page_blocks.append("\n\n".join(page_paragraphs))
    return "\n\n".join(page_blocks), paragraphs


def find_relevant_paragraphs(paragraphs: list[str], terms: str | list[str], limit: int = 8) -> list[dict[str, Any]]:
    terms_list = terms if isinstance(terms, list) else query_terms(terms)
    normalized_terms = [(normalize_text(t), 1.0) for t in terms_list if normalize_text(t)]
    scored: list[tuple[float, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        low = normalize_text(paragraph)
        score = 0.0
        hits = 0
        for term, weight in normalized_terms:
            if term and term in low:
                score += weight
                hits += 1
        if hits:
            # Strong bonus when multiple concepts occur in the same passage.
            if hits >= 2:
                score += 2.0
            scored.append((score, index, paragraph))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"numero": index + 1, "texto": paragraph, "coincidencias": round(score, 2)}
        for score, index, paragraph in scored[:limit]
    ]


def score_document(decision: Decision, text: str, paragraphs: list[str], query: str) -> tuple[float, dict[str, Any] | None]:
    terms = query_terms(query)
    low = normalize_text(text[:MAX_DOCUMENT_CHARS])
    score = 0.0
    for term in terms:
        nt = normalize_text(term)
        if nt:
            count = min(low.count(nt), 8)
            if count:
                score += 1.0 + min(count, 4) * 0.7
    citation_bonus = 2.0 if decision.citation else 0.0
    score += citation_bonus
    relevant = find_relevant_paragraphs(paragraphs, terms, limit=6)
    if relevant:
        score += min(10.0, sum(float(x["coincidencias"]) for x in relevant) / 2)
    snippet = relevant[0] if relevant else None
    return score, snippet


async def read_decision(decision: Decision, query: str) -> Decision:
    try:
        response = await fetch_response(decision.url)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or decision.url.lower().split("?", 1)[0].endswith(".pdf")
        if is_pdf:
            text, paragraphs = extract_pdf_document(response.content)
        else:
            text, paragraphs = extract_html_document(response.text)
        if not text:
            return decision
        score, best = score_document(decision, text, paragraphs, query)
        decision.relevance_score = round(score, 2)
        if best:
            decision.snippet = best["texto"]
            page_match = re.search(r"\[página (\d+)\]", best["texto"])
            decision.page = int(page_match.group(1)) if page_match else None
        citation = extract_citation(text)
        if citation:
            decision.citation = citation
            decision.verified = True
            decision.verification_status = "verified_source_identifier"
        cover = extract_cover_metadata(paragraphs)
        if cover["case_number"]:
            decision.case_number = cover["case_number"]
        elif not decision.case_number:
            decision.case_number = extract_case_number(text)
        if cover["date"]:
            decision.date = cover["date"]
        if cover["case_name"]:
            decision.title = cover["case_name"]
        return decision
    except Exception:
        return decision


_DISCIPLINE_QUERY_HINTS = {
    "conducta", "abogacia", "notaria", "etica", "disciplina", "colegiacion",
    "suspension", "querella", "comisionado", "comisionada", "reglamento",
    "reglas", "aprobacion", "honorarios",
}


def _looks_like_discipline_matter(decision: Decision) -> bool:
    """Attorney/notary discipline proceedings, and Court rule-making dockets
    ("In re: [name]" with case numbers prefixed CP-/TS-/AB-, or "In re:
    Aprobación de las Reglas..." prefixed ER-), routinely narrate or quote a
    party's underlying legal matter as background or as an example clause —
    not as a ruling on it. Confirmed against two real cases: a disciplinary
    complaint whose client's "revisión de pensión alimentaria" was quoted
    verbatim as background, and the Reglas de Conducta Profesional
    themselves, which mention "pensión de alimentos" only inside a rule
    about contingent attorney fees in family cases. Neither is the Tribunal
    ruling on pensión alimenticia. Word matching alone can't tell those
    apart since the exact phrase is genuinely present — this checks the
    document's own structural caption instead (self-reported by the cover
    page, not guessed)."""
    title_norm = normalize_text(decision.title)
    if not title_norm.startswith("in re"):
        return False
    case_number_norm = normalize_text(decision.case_number)
    return bool(re.match(r"^(cp|ts|ab|er)\b", case_number_norm))


# A term counts as "specific" only if it's a value from the curated
# LEGAL_SYNONYMS dictionary AND is itself a multi-word phrase or a
# sufficiently long, distinctive single word (e.g. "alimentante",
# "manutención") — never an arbitrary word pulled straight from a user's
# free-text question. A long word from the query itself ("obligación") is
# not reliably domain-specific just because it's long: "obligación" alone
# is generic legal vocabulary used in contracts, trusts, torts — everywhere
# — and matched an unrelated estate/trust case in a real complex-question
# search. Only vocabulary this project has deliberately curated as
# distinctive to a legal topic gets to short-circuit the co-occurrence
# check; anything else still has to clear the distinct-hits bar below.
_CURATED_SPECIFIC_TERMS = {
    normalize_text(s)
    for synonyms in LEGAL_SYNONYMS.values()
    for s in synonyms
    if " " in normalize_text(s) or len(normalize_text(s)) >= 10
}

# Which curated LEGAL_SYNONYMS family a term belongs to (first key found
# wins on overlap). Plural/singular/gender variants of the same word (e.g.
# "menor"/"menores"/"niño"/"niña"/"hijo"/"hija" are all one dictionary
# entry) are one concept, not independent evidence — a document merely
# mentioning children ("hijos") is common to custody, adoption, criminal,
# and inheritance cases alike, so hitting several of those variants must
# not by itself look like 3 unrelated confirmations of relevance.
_SYNONYM_FAMILY_OF: dict[str, str] = {}
for _family, _synonyms in LEGAL_SYNONYMS.items():
    for _s in _synonyms:
        _SYNONYM_FAMILY_OF.setdefault(normalize_text(_s), _family)


def _is_specific_term(term: str) -> bool:
    return normalize_text(term) in _CURATED_SPECIFIC_TERMS


def _document_relevance_confirmed(decision: Decision, query: str) -> bool:
    """Require real topical signal in the returned passage before trusting
    it as evidence of relevance — not just any two words in common.

    Confirmed against real documents, twice: (1) two generic single words
    matching ("pensión" + "alimentos" inside an unrelated attorney-discipline
    case that mentions a client's alimony claim only as background), and
    (2) morphological variants of one broad concept ("hijos"/"hijo"/"hija",
    all meaning "children") piling up to 3+ raw string hits inside an
    unrelated trust or criminal case. Neither is real evidence. A match is
    trusted only when it includes at least one specific curated term (a
    multi-word legal phrase, or the literal query phrase itself), or hits
    span at least two *distinct* curated topic families — concept diversity,
    not word-form repetition of the same concept. Raw words straight from
    the user's own sentence (not in the curated dictionary at all, e.g.
    "obligación") don't count toward either — they're too generic and
    unpredictable to serve as independent signal on their own.
    """
    if not decision.snippet:
        return False
    query_words = {normalize_text(w) for w in re.findall(r"[\wÀ-ÿ]+", query.lower())}
    if _looks_like_discipline_matter(decision) and not (query_words & _DISCIPLINE_QUERY_HINTS):
        return False
    terms = query_terms(query)
    snippet_norm = normalize_text(decision.snippet)
    hits = [term for term in terms if normalize_text(term) and normalize_text(term) in snippet_norm]
    if any(_is_specific_term(term) for term in hits):
        return True
    curated_families = {
        _SYNONYM_FAMILY_OF[normalize_text(term)]
        for term in hits
        if normalize_text(term) in _SYNONYM_FAMILY_OF
    }
    if len(curated_families) >= 2:
        return True
    query_norm = normalize_text(query)
    return bool(query_norm) and query_norm in snippet_norm


def _metadata_match_score(item: Decision, terms: list[str]) -> int:
    blob = normalize_text(f"{item.title} {item.citation} {item.case_number} {item.subject}")
    return sum(1 for term in terms if normalize_text(term) in blob)


async def content_search(query: str, years: list[int], limit: int) -> tuple[list[Decision], dict[str, Any]]:
    """Search the actual official decision PDFs, two years at a time.

    Two-stage, round-based search:
      Stage 1 (per round): fetch the official index for the next small group
      of requested years — cheap, no PDF reads, and never skips a year.
      Stage 2 (per round): from that round's candidates, read/verify against
      the official PDF only a bounded batch — index-metadata matches first
      (a free, high-precision signal when it exists), then even coverage of
      the rest — and stop as soon as `limit` verified results are confirmed.

    The search stops expanding once results are sufficient, the year list is
    exhausted, or the total-PDF-read budget is spent — never by silently
    dropping a requested year. `anos_explorados` in the returned metadata
    reports exactly how far the search actually got, so a caller can tell
    "no evidence found" apart from "not all years were checked".
    """
    terms = query_terms(query)
    confirmed: list[Decision] = []
    confirmed_urls: set[str] = set()
    years_explored: list[int] = []
    pdfs_read = 0
    remaining_years = list(years)

    while remaining_years and pdfs_read < MAX_TOTAL_PDF_READS and len(confirmed) < limit:
        year_group = remaining_years[:YEAR_GROUP_SIZE]
        remaining_years = remaining_years[YEAR_GROUP_SIZE:]
        years_explored.extend(year_group)

        group_indexes = await asyncio.gather(
            *(get_year_links(y) for y in year_group), return_exceptions=True
        )
        group_candidates: list[Decision] = []
        for entry in group_indexes:
            if isinstance(entry, list):
                group_candidates.extend(entry)
        group_candidates = [
            c for c in dedupe_decisions(group_candidates)
            if c.url.lower().split("?", 1)[0].endswith(".pdf") and c.url not in confirmed_urls
        ]
        if not group_candidates:
            continue

        # Prioritize candidates whose index metadata already matches the
        # query (free — no PDF read needed to know); fill any remaining
        # budget with an even spread of the rest for unbiased coverage.
        strong = [c for c in group_candidates if _metadata_match_score(c, terms) > 0]
        weak = [c for c in group_candidates if c not in strong]
        round_budget = min(PDF_READS_PER_ROUND, MAX_TOTAL_PDF_READS - pdfs_read)
        batch = strong[:round_budget]
        if len(batch) < round_budget:
            batch += sample_evenly(weak, round_budget - len(batch))

        semaphore = asyncio.Semaphore(PDF_READ_CONCURRENCY)

        async def one(item: Decision) -> Decision:
            async with semaphore:
                return await read_decision(item, query)

        read_results = await asyncio.gather(*(one(item) for item in batch))
        pdfs_read += len(batch)

        for r in read_results:
            if (
                r.url not in confirmed_urls
                and r.relevance_score > 0
                and r.verified
                and _document_relevance_confirmed(r, query)
            ):
                confirmed.append(r)
                confirmed_urls.add(r.url)

    confirmed.sort(key=lambda r: (-r.relevance_score, r.citation or r.title))
    meta = {
        "anos_explorados": years_explored,
        "anos_pendientes": remaining_years,
        "pdfs_verificados": pdfs_read,
    }
    return confirmed[:limit], meta


async def official_search(query: str, year: int | None, limit: int) -> list[Decision]:
    if year is not None:
        candidates = await get_year_links(year)
    else:
        html = await fetch_text(OFFICIAL_INDEX)
        candidates = parse_index(html, OFFICIAL_INDEX)
    terms = query_terms(query)
    scored: list[tuple[int, Decision]] = []
    for item in candidates:
        blob = normalize_text(f"{item.title} {item.citation} {item.case_number} {item.subject}")
        score = sum(1 for term in terms if normalize_text(term) in blob)
        if score:
            scored.append((score, item))
    if scored:
        return [item for _, item in sorted(scored, key=lambda pair: -pair[0])[:limit]]
    # If the index itself has no topical language, search document contents.
    years = [year] if year is not None else [2026, 2025, 2024, 2023, 2022]
    results, _meta = await content_search(query, years, limit)
    return results


async def citation_search(citation: str) -> list[Decision]:
    """Locate an exact TSPR citation via direct structured match.

    This deliberately bypasses official_search's word-scoring pipeline.
    query_terms() drops short numeric tokens (e.g. the "25" in "2025 TSPR
    25") as thematic noise, which is correct for topic search but wrong for
    citation lookup: it made every decision in a year score identically,
    so a citation could be truncated out by the results-limit before an
    exact-match check ever saw it. Citation lookup is a different, stricter
    problem — match the citation field precisely against the full official
    index, with no truncation and no fuzzy scoring, so it can't produce a
    false positive.
    """
    requested = normalize_citation(citation)
    if not requested:
        return []
    year_match = re.search(r"\b((?:19|20)\d{2})\b", requested)
    year = int(year_match.group(1)) if year_match else None
    try:
        if year is not None:
            candidates = await get_year_links(year)
        else:
            html = await fetch_text(OFFICIAL_INDEX)
            candidates = parse_index(html, OFFICIAL_INDEX)
    except Exception:
        return []
    candidates = dedupe_decisions(candidates)
    matches = [
        item for item in candidates
        if item.citation and normalize_citation(item.citation) == requested
    ]
    if not matches:
        return []
    # Confirm each index match against the source document itself and
    # enrich it with metadata only the document can verify. If the document
    # can't be fetched, fall back to the index-level verification (the
    # official index already lists this exact citation against this URL).
    confirmed: list[Decision] = []
    for item in matches:
        enriched = await read_decision(item, "")
        if enriched.citation and normalize_citation(enriched.citation) == requested and enriched.verified:
            confirmed.append(enriched)
    return confirmed


@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int | None = None, maximo: int = 10) -> dict[str, Any]:
    """Busca sentencias y opiniones del Tribunal Supremo de Puerto Rico.

    Para consultas temáticas, el servidor intenta buscar dentro del texto de los
    PDFs oficiales y devuelve solo documentos realmente encontrados y verificables.
    Para obtener las mejores autoridades para un argumento, usa esta herramienta
    y luego leer_sentencia sobre los resultados relevantes.
    """
    maximo = max(1, min(int(maximo), 20))
    try:
        results = await official_search(consulta, ano, maximo)
        return {
            "consulta": consulta,
            "ano": ano,
            "resultados": [asdict(r) for r in results],
            "fuente": OFFICIAL_INDEX,
            "regla_integridad": "Solo se devuelven documentos encontrados en fuentes permitidas; los campos no disponibles quedan vacíos.",
        }
    except Exception as exc:
        return {"error": "No fue posible consultar las fuentes públicas.", "detalle_tecnico": str(exc), "resultados": []}


@mcp.tool()
async def investigar_sentencias(consulta: str, anos: str = "2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,2000,1999,1998", maximo: int = 5) -> dict[str, Any]:
    """Encuentra las mejores autoridades verificables para una cuestión jurídica.

    Busca en el contenido de PDFs públicos del Tribunal Supremo, puntúa coincidencias
    temáticas y devuelve cita TSPR, URL oficial, pasaje textual extraído y página
    cuando está disponible. El servidor NO decide que una sentencia 'apoya' una
    posición jurídica: entrega evidencia fuente para que el modelo la evalúe.
    """
    try:
        years = [int(x.strip()) for x in anos.split(",") if x.strip().isdigit()]
        years = list(dict.fromkeys(years))
        if not years:
            years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
        maximo = max(1, min(int(maximo), 10))
        results, meta = await content_search(consulta, years, maximo)
        return {
            "consulta": consulta,
            "anos_consultados": years,
            "anos_explorados": meta["anos_explorados"],
            "anos_no_explorados": meta["anos_pendientes"],
            "pdfs_verificados": meta["pdfs_verificados"],
            "resultados": [asdict(r) for r in results],
            "total": len(results),
            "verificacion": "Cada resultado incluye una URL de fuente permitida y fue leído desde el documento fuente; los pasajes no son generados por el modelo.",
            "limitacion": "La puntuación mide coincidencia textual/temática y no sustituye el análisis jurídico de holding, ratio decidendi o precedentes posteriores.",
            "cobertura": (
                "La búsqueda se detiene en cuanto encuentra suficientes resultados verificados "
                "o al agotar el presupuesto de lectura de PDFs, para responder dentro de un tiempo "
                "razonable. 'anos_no_explorados' indica qué años no llegaron a revisarse en esta "
                "llamada — no significa que no existan decisiones relevantes ahí."
            ),
        }
    except Exception as exc:
        return {"consulta": consulta, "resultados": [], "total": 0, "error": "No fue posible completar la investigación documental.", "detalle_tecnico": str(exc)}


@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str, Any]:
    """Localiza una cita TSPR exacta; nunca sustituye una cita no encontrada."""
    try:
        results = await citation_search(cita)
        if not results:
            return {
                "cita": cita,
                "encontrado": False,
                "resultados": [],
                "verificado": False,
                "mensaje": "La cita exacta no fue encontrada en la fuente oficial consultada. No se generará ni sustituirá por otra cita.",
                "fuente": OFFICIAL_INDEX,
            }
        return {"cita": cita, "encontrado": True, "verificado": True, "resultados": [asdict(r) for r in results]}
    except Exception as exc:
        return {"cita": cita, "encontrado": False, "verificado": False, "resultados": [], "error": "No fue posible verificar la cita.", "detalle_tecnico": str(exc)}


@mcp.tool()
async def leer_sentencia(url: str, terminos: str = "", max_parrafos: int = 8) -> dict[str, Any]:
    """Lee una sentencia/documento público y devuelve pasajes extraídos de la fuente."""
    if not allowed_url(url):
        return {"error": "Por seguridad, solo se permiten URLs HTTPS de las fuentes públicas configuradas.", "verificado": False}
    try:
        response = await fetch_response(url)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf")
        if is_pdf:
            text, paragraphs = extract_pdf_document(response.content)
            document_type = "PDF"
        else:
            text, paragraphs = extract_html_document(response.text)
            document_type = "HTML"
        if not text:
            return {"url": url, "verificado": False, "error": "La fuente no contiene texto extraíble; no se generará contenido sustitutivo."}
        max_parrafos = max(1, min(int(max_parrafos), 30))
        relevantes = find_relevant_paragraphs(paragraphs, terminos, max_parrafos)
        citation = extract_citation(text)
        cover = extract_cover_metadata(paragraphs)
        case_number = cover["case_number"] or extract_case_number(text)
        return {
            "url": url,
            "fuente": source_name(url),
            "tipo_documento": document_type,
            "cita_tspr": citation,
            "numero_caso": case_number,
            "nombre_caso": cover["case_name"],
            "fecha": cover["date"],
            "parrafos": relevantes,
            "total_parrafos_extraidos": len(paragraphs),
            "procedencia": "Texto extraído directamente del documento fuente; no generado por el modelo.",
            "verificado": True,
        }
    except Exception as exc:
        return {"error": "No fue posible leer o extraer el documento; no se hará ninguna inferencia sobre su contenido.", "detalle_tecnico": str(exc), "url": url, "verificado": False}


@mcp.tool()
def opciones_busqueda(consulta: str = "", campo: str = "fuentes") -> dict[str, Any]:
    """Explica las fuentes y filtros disponibles."""
    return {
        "consulta": consulta,
        "campo": campo,
        "fuentes": {"tribunal_supremo": OFFICIAL_INDEX, "lexjuris": LEXJURIS_SEARCH},
        "herramientas_recomendadas": {
            "investigar_sentencias": "Para encontrar autoridades por el contenido de las sentencias.",
            "buscar_por_cita": "Para verificar una cita TSPR exacta.",
            "leer_sentencia": "Para recuperar pasajes y páginas directamente de una sentencia.",
        },
        "filtros": ["año", "cita TSPR", "número de caso", "términos del asunto"],
        "regla_integridad": "Si una autoridad o cita no se encuentra en una fuente permitida, se informa como no encontrada.",
    }


@mcp.tool()
def estado() -> dict[str, Any]:
    """Devuelve diagnóstico y garantías de integridad."""
    return {
        "servidor": "puerto-rico-sentencias",
        "version": "0.5.1",
        "fuentes": [OFFICIAL_INDEX, LEXJURIS_SEARCH],
        "citation_integrity": {
            "no_casos_inventados": True,
            "no_citas_inventadas": True,
            "no_nombres_inventados": True,
            "no_fechas_o_ponentes_inferidos": True,
            "no_citas_aproximadas_en_buscar_por_cita": True,
            "no_citas_textuales_generadas": True,
            "source_required": True,
        },
        "documentos": {"pdf": True, "html": True, "pasajes_con_procedencia": True, "pagina_pdf": True},
        "privacidad": "No se almacenan consultas ni documentos por defecto.",
        "anti_bot": "No se eluden CAPTCHA, autenticación ni controles de acceso.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
