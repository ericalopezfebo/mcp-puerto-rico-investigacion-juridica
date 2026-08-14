from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from mcp_server.models import Decision
from mcp_server.verification import extract_citation

INDEX_URL = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
TIMEOUT = 20.0


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


async def fetch(url: str) -> str:
    headers = {"User-Agent": "mcp-puerto-rico-sentencias/0.5", "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def parse_index(html: str, year: int | None = None) -> list[Decision]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[Decision] = []
    for anchor in soup.find_all("a", href=True):
        title = clean(anchor.get_text(" ", strip=True))
        url = urljoin(INDEX_URL, anchor["href"])
        haystack = f"{title} {url}"
        citation = extract_citation(haystack)
        if not citation and not any(word in haystack.upper() for word in ("TSPR", "SENTENCIA", "OPINIÓN", "OPINION", "PDF")):
            continue
        found_year = None
        match = re.search(r"\b((?:19|20)\d{2})\b", citation or haystack)
        if match:
            found_year = int(match.group(1))
        if year is not None and found_year is not None and found_year != year:
            continue
        verified = bool(citation and url.startswith("https://poderjudicial.pr/"))
        results.append(Decision(
            title=title,
            url=url,
            source="Poder Judicial de Puerto Rico",
            citation=citation,
            verified=verified,
            verification_status="verified_source_identifier" if verified else "identifier_not_confirmed",
        ))
    unique: dict[str, Decision] = {}
    for item in results:
        unique.setdefault(item.url, item)
    return list(unique.values())


async def search(query: str, year: int | None = None, limit: int = 20) -> list[Decision]:
    html = await fetch(INDEX_URL)
    candidates = parse_index(html, year)
    terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", query) if len(t) > 2]
    if terms:
        scored: list[tuple[int, Decision]] = []
        for item in candidates:
            blob = f"{item.title} {item.citation} {item.case_number} {item.subject}".lower()
            score = sum(term in blob for term in terms)
            if score:
                scored.append((score, item))
        candidates = [item for _, item in sorted(scored, key=lambda pair: -pair[0])]
    return candidates[:max(1, min(limit, 50))]


async def exact_citation(citation: str) -> list[Decision]:
    normalized = re.sub(r"\s+", " ", citation.strip().upper())
    year_match = re.search(r"\b((?:19|20)\d{2})\b", normalized)
    year = int(year_match.group(1)) if year_match else None
    results = await search(citation, year=year, limit=50)
    return [item for item in results if item.verified and item.citation and re.sub(r"\s+", " ", item.citation.upper()) == normalized]
