"""Incremental builder for the local Puerto Rico Supreme Court corpus.

The builder only stores material fetched from the official Poder Judicial source.
It is designed for unattended GitHub Actions runs and manual backfills. Existing
records are merged by normalized TSPR citation, so interrupted or repeated runs
are idempotent.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import corpus_index
import doctrine_ontology
import server as jurisprudencia

MAX_SEARCH_TEXT_CHARS = 6000
MAX_CONCEPTS = 16
MAX_CITATIONS = 40
DEFAULT_CONCURRENCY = 8


def _citation_year(citation: str) -> int | None:
    match = re.match(r"\s*((?:19|20)\d{2})\s+TSPR\s+\d+", citation or "", re.I)
    return int(match.group(1)) if match else None


def _citation_sort_key(value: str) -> tuple[int, int, str]:
    match = re.search(r"((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})", value or "", re.I)
    if not match:
        return (9999, 9999, value)
    return (int(match.group(1)), int(match.group(2)), value)


def _concept_hits(text: str) -> list[tuple[str, str, int]]:
    normalized = jurisprudencia.normalize_text(text)
    hits: list[tuple[str, str, int]] = []
    for name, concept in doctrine_ontology.LEGAL_CONCEPTS.items():
        count = 0
        for alias in concept.aliases:
            needle = jurisprudencia.normalize_text(alias)
            if needle:
                count += normalized.count(needle)
        if count:
            hits.append((name, concept.area, count))
    hits.sort(key=lambda row: (-row[2], row[0]))
    return hits[:MAX_CONCEPTS]


def _subject_and_concepts(text: str) -> tuple[str, list[str]]:
    hits = _concept_hits(text)
    concepts = [name for name, _area, _count in hits]
    areas: list[str] = []
    for _name, area, _count in hits:
        if area not in areas:
            areas.append(area)
    subject = "; ".join(areas[:4])
    return subject, concepts


def _all_tspr_citations(text: str, own_citation: str = "") -> list[str]:
    own_key = jurisprudencia.normalize_citation(own_citation)
    seen: set[str] = set()
    result: list[str] = []
    for year, number in re.findall(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I):
        citation = f"{year} TSPR {int(number)}"
        key = jurisprudencia.normalize_citation(citation)
        if key == own_key or key in seen:
            continue
        seen.add(key)
        result.append(citation)
        if len(result) >= MAX_CITATIONS:
            break
    return result


def _paragraph_score(paragraph: str, concept_names: list[str]) -> float:
    low = jurisprudencia.normalize_text(paragraph)
    if not low or len(low) < 80:
        return -1.0
    score = min(len(paragraph), 900) / 450.0
    legal_cues = (
        "hemos resuelto", "hemos expresado", "concluimos", "resolvemos",
        "doctrina", "norma", "regla general", "requisito", "jurisdiccion",
        "debido proceso", "obligacion", "derecho", "procede", "no procede",
    )
    score += sum(1.2 for cue in legal_cues if jurisprudencia.normalize_text(cue) in low)
    for name in concept_names[:8]:
        concept = doctrine_ontology.LEGAL_CONCEPTS.get(name)
        if not concept:
            continue
        if any(jurisprudencia.normalize_text(alias) in low for alias in concept.aliases):
            score += 2.0
    if low.startswith("en el tribunal supremo") or "numero del caso" in low:
        score -= 8.0
    return score


def _best_exact_excerpt(paragraphs: list[str], concept_names: list[str]) -> tuple[str, int | None]:
    candidates: list[tuple[float, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        score = _paragraph_score(paragraph, concept_names)
        if score > 0:
            candidates.append((score, index, paragraph))
    if not candidates:
        return "", None
    candidates.sort(key=lambda row: (-row[0], row[1]))
    text = candidates[0][2]
    page_match = re.search(r"\[página (\d+)\]\s*", text)
    page = int(page_match.group(1)) if page_match else None
    exact = re.sub(r"^\[página \d+\]\s*", "", text).strip()
    return exact[:2400], page


def _search_text(paragraphs: list[str]) -> str:
    """Build a bounded discovery-only text window from the official PDF.

    We sample across the whole opinion rather than storing only the first pages.
    The field is never surfaced as a quotation by the MCP.
    """
    useful = [re.sub(r"^\[página \d+\]\s*", "", p).strip() for p in paragraphs if len(p) >= 50]
    if not useful:
        return ""
    if len(useful) <= 24:
        chosen = useful
    else:
        step = len(useful) / 24
        indices = sorted({min(len(useful) - 1, int(i * step)) for i in range(24)})
        chosen = [useful[i] for i in indices]
    return jurisprudencia.clean(" ".join(chosen))[:MAX_SEARCH_TEXT_CHARS]


def _record_key(row: dict[str, Any]) -> str:
    return jurisprudencia.normalize_citation(str(row.get("citation", "")))


def merge_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in [*existing, *incoming]:
        key = _record_key(row)
        if not key:
            continue
        current = merged.get(key)
        if current is None:
            merged[key] = row
            continue
        # Prefer the richer record, but never discard a previously captured
        # exact excerpt merely because a later refresh had weaker extraction.
        candidate = dict(current)
        for field, value in row.items():
            if value not in (None, "", [], ()):
                candidate[field] = value
        if current.get("excerpt") and not row.get("excerpt"):
            candidate["excerpt"] = current["excerpt"]
            candidate["page"] = current.get("page")
        merged[key] = candidate
    return sorted(merged.values(), key=lambda row: _citation_sort_key(str(row.get("citation", ""))))


def load_raw_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def write_records(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


async def build_one(decision: jurisprudencia.Decision, semaphore: asyncio.Semaphore) -> dict[str, Any] | None:
    async with semaphore:
        try:
            response = await jurisprudencia.fetch_response(decision.url)
            content_type = response.headers.get("content-type", "").lower()
            is_pdf = "application/pdf" in content_type or decision.url.lower().split("?", 1)[0].endswith(".pdf")
            if is_pdf:
                full_text, paragraphs = jurisprudencia.extract_pdf_document(response.content)
            else:
                full_text, paragraphs = jurisprudencia.extract_html_document(response.text)
            if not full_text:
                return None
            citation = jurisprudencia.extract_citation(full_text) or decision.citation
            if not citation:
                return None
            year = _citation_year(citation)
            if year is None:
                return None
            cover = jurisprudencia.extract_cover_metadata(paragraphs)
            subject, concepts = _subject_and_concepts(full_text)
            excerpt, page = _best_exact_excerpt(paragraphs, concepts)
            case_number = cover.get("case_number") or decision.case_number or jurisprudencia.extract_case_number(full_text)
            title = cover.get("case_name") or decision.title
            record = {
                "citation": citation,
                "year": year,
                "title": title,
                "url": decision.url,
                "case_number": case_number,
                "date": cover.get("date", ""),
                "subject": subject,
                "page": page,
                "excerpt": excerpt,
                "search_text": _search_text(paragraphs),
                "concepts": concepts,
                "citations": _all_tspr_citations(full_text, citation),
                "captured_at": date.today().isoformat(),
                "source": "Poder Judicial de Puerto Rico",
                "verification_level": "cached_official_excerpt" if excerpt else "cached_official_metadata",
            }
            return record
        except Exception:
            return None


async def build_year(year: int, max_docs: int | None = None, concurrency: int = DEFAULT_CONCURRENCY) -> list[dict[str, Any]]:
    decisions = await jurisprudencia.get_year_links(year)
    if max_docs is not None:
        decisions = decisions[: max(0, int(max_docs))]
    semaphore = asyncio.Semaphore(max(1, int(concurrency)))
    rows = await asyncio.gather(*(build_one(decision, semaphore) for decision in decisions))
    return [row for row in rows if isinstance(row, dict)]


async def run(args: argparse.Namespace) -> int:
    target = Path(args.output)
    years = list(range(args.start_year, args.end_year + 1))
    existing = load_raw_records(target)
    incoming: list[dict[str, Any]] = []
    for year in years:
        rows = await build_year(year, max_docs=args.max_docs, concurrency=args.concurrency)
        incoming.extend(rows)
        print(f"year={year} indexed={len(rows)}")
    merged = merge_records(existing, incoming)
    if not args.dry_run:
        write_records(target, merged)
    print(json.dumps({
        "existing": len(existing),
        "captured_this_run": len(incoming),
        "total_after_merge": len(merged),
        "years": years,
        "dry_run": bool(args.dry_run),
    }, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build/update the official TSPR local corpus")
    current_year = date.today().year
    parser.add_argument("--start-year", type=int, default=current_year)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument("--max-docs", type=int, default=None, help="Optional cap per year for smoke/backfill batches")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--output", default=str(corpus_index.CORPUS_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year must be <= --end-year")
    return args


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
