"""Incrementally refresh the persistent TSPR discovery corpus from official PDFs.

Default: refresh current and previous year. Set CORPUS_YEARS="2020,2021" for
specific years or CORPUS_FULL_REBUILD=1 to request 1997..current year.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

import doctrine_ontology
import server

OUT = Path("data/jurisprudence_corpus.jsonl")
MAX_EXCERPT_CHARS = 5000
CONCURRENCY = 8


def requested_years() -> list[int]:
    current = date.today().year
    explicit = os.getenv("CORPUS_YEARS", "").strip()
    if explicit:
        return sorted({int(x.strip()) for x in explicit.split(",") if x.strip().isdigit()})
    if os.getenv("CORPUS_FULL_REBUILD", "").lower() in {"1", "true", "yes"}:
        return list(range(1997, current + 1))
    return [max(1997, current - 1), current]


def load_existing() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not OUT.exists():
        return rows
    for line in OUT.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        citation = str(row.get("citation", "")).strip()
        if citation:
            rows[server.normalize_citation(citation)] = row
    return rows


def classify(paragraphs: list[str]) -> tuple[list[str], str]:
    concepts: list[str] = []
    selected: list[str] = []
    seen_paragraphs: set[str] = set()
    for name, concept in doctrine_ontology.LEGAL_CONCEPTS.items():
        needles = [server.normalize_text(x) for x in (*concept.aliases, *concept.related)]
        matched_concept = False
        for paragraph in paragraphs:
            normalized = server.normalize_text(paragraph)
            if any(needle and needle in normalized for needle in needles):
                matched_concept = True
                if paragraph not in seen_paragraphs and len("\n\n".join(selected)) < MAX_EXCERPT_CHARS:
                    seen_paragraphs.add(paragraph)
                    selected.append(paragraph)
        if matched_concept:
            concepts.append(name)
    excerpt = "\n\n".join(selected)[:MAX_EXCERPT_CHARS]
    return concepts, excerpt


def cited_tspr(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for year, number in re.findall(r"\b((?:19|20)\d{2})\s*TSPR\s*0*(\d{1,4})\b", text, re.I):
        citation = f"{year} TSPR {int(number)}"
        key = server.normalize_citation(citation)
        if key not in seen:
            seen.add(key)
            found.append(citation)
    return found[:80]


async def build_one(decision: server.Decision, year: int, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        try:
            response = await server.fetch_response(decision.url)
            text, paragraphs = server.extract_pdf_document(response.content)
        except Exception:
            return None
    if not text:
        return None
    cover = server.extract_cover_metadata(paragraphs)
    concepts, excerpt = classify(paragraphs)
    if not concepts:
        # Keep metadata-only rows too: they can later be found through citation chains.
        excerpt = ""
    citation = server.extract_citation(text) or decision.citation
    if not citation:
        return None
    page = None
    if excerpt:
        match = re.search(r"\[página (\d+)\]", excerpt)
        page = int(match.group(1)) if match else None
    return {
        "citation": citation,
        "year": year,
        "title": cover.get("case_name") or decision.title,
        "url": decision.url,
        "case_number": cover.get("case_number") or decision.case_number,
        "date": cover.get("date") or decision.date,
        "subject": decision.subject,
        "page": page,
        "excerpt": excerpt,
        "concepts": concepts,
        "citations": cited_tspr(text),
        "captured_at": date.today().isoformat(),
        "source": "Poder Judicial de Puerto Rico",
        "verification_level": "cached_official_excerpt" if excerpt else "cached_official_metadata",
        "sha256": hashlib.sha256(response.content).hexdigest(),
    }


async def main() -> None:
    rows = load_existing()
    semaphore = asyncio.Semaphore(CONCURRENCY)
    for year in requested_years():
        decisions = await server.get_year_links(year)
        built = await asyncio.gather(*(build_one(d, year, semaphore) for d in decisions))
        for row in built:
            if row:
                rows[server.normalize_citation(row["citation"])] = row
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (int(r.get("year", 0)), str(r.get("citation", ""))))
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in ordered) + "\n", encoding="utf-8")
    print(f"corpus rows: {len(ordered)}; years refreshed: {requested_years()}")


if __name__ == "__main__":
    asyncio.run(main())
