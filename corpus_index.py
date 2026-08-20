"""Persistent local jurisprudence corpus used before live-network discovery.

The corpus is a resilience/cache layer built only from previously retrieved
primary-source material. It is not a substitute for the official source: every
record keeps its official URL, provenance, capture date, and verification level.
Live verification is preferred when available; cached official excerpts allow
research to continue when the public websites are temporarily unavailable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import doctrine_ontology
import server as jurisprudencia

CORPUS_PATH = Path(__file__).resolve().parent / "data" / "jurisprudence_corpus.jsonl"


@dataclass(frozen=True)
class CorpusRecord:
    citation: str
    year: int
    title: str
    url: str
    case_number: str = ""
    date: str = ""
    subject: str = ""
    page: int | None = None
    excerpt: str = ""
    # Search-only text is a bounded extract from the official document. It
    # improves discovery recall but is never returned as a quotation. Only the
    # exact `excerpt` field may be used by cached_decision as quoted source text.
    search_text: str = ""
    concepts: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    captured_at: str = ""
    source: str = "Poder Judicial de Puerto Rico"
    verification_level: str = "cached_official_metadata"


def _record_from_dict(row: dict[str, Any]) -> CorpusRecord | None:
    try:
        return CorpusRecord(
            citation=str(row["citation"]),
            year=int(row["year"]),
            title=str(row.get("title", "")),
            url=str(row["url"]),
            case_number=str(row.get("case_number", "")),
            date=str(row.get("date", "")),
            subject=str(row.get("subject", "")),
            page=int(row["page"]) if row.get("page") is not None else None,
            excerpt=str(row.get("excerpt", "")),
            search_text=str(row.get("search_text", "")),
            concepts=tuple(str(x) for x in row.get("concepts", [])),
            citations=tuple(str(x) for x in row.get("citations", [])),
            captured_at=str(row.get("captured_at", "")),
            source=str(row.get("source", "Poder Judicial de Puerto Rico")),
            verification_level=str(row.get("verification_level", "cached_official_metadata")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def load_corpus(path: Path | None = None) -> list[CorpusRecord]:
    target = path or CORPUS_PATH
    if not target.exists():
        return []
    out: list[CorpusRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        record = _record_from_dict(row)
        if record is not None:
            out.append(record)
    return out


def _query_vocabulary(query: str) -> list[tuple[str, float]]:
    normalized = jurisprudencia.normalize_text(query)
    weighted: dict[str, float] = {}
    for term in jurisprudencia.query_terms(query):
        nt = jurisprudencia.normalize_text(term)
        if nt:
            weighted[nt] = max(weighted.get(nt, 0.0), 1.0)
    for _name, concept in doctrine_ontology.matching_concepts(normalized):
        for alias in concept.aliases:
            nt = jurisprudencia.normalize_text(alias)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 1.35)
        for related in concept.related:
            nt = jurisprudencia.normalize_text(related)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.85)
    return list(weighted.items())


def score_record(record: CorpusRecord, query: str) -> float:
    blob = jurisprudencia.normalize_text(
        " ".join((
            record.title,
            record.subject,
            record.excerpt,
            record.search_text,
            " ".join(record.concepts),
        ))
    )
    score = 0.0
    matched = 0
    for term, weight in _query_vocabulary(query):
        if term and term in blob:
            matched += 1
            # Phrase matches are much stronger than isolated token matches.
            score += weight * (3.0 if " " in term else 1.5)
    if matched >= 3:
        score += min(8.0, float(matched - 2) * 1.5)
    return round(score, 2)


def search_corpus(query: str, years: list[int] | None = None, limit: int = 80) -> list[tuple[CorpusRecord, float]]:
    allowed_years = set(years or [])
    scored: list[tuple[CorpusRecord, float]] = []
    for record in load_corpus():
        if allowed_years and record.year not in allowed_years:
            continue
        score = score_record(record, query)
        if score > 0:
            scored.append((record, score))
    scored.sort(key=lambda item: (-item[1], item[0].citation))
    return scored[: max(1, int(limit))]


def get_record(citation: str) -> CorpusRecord | None:
    key = jurisprudencia.normalize_citation(citation)
    for record in load_corpus():
        if jurisprudencia.normalize_citation(record.citation) == key:
            return record
    return None


def cached_decision(citation: str, query: str = "") -> jurisprudencia.Decision | None:
    record = get_record(citation)
    if record is None or not record.excerpt:
        return None
    decision = jurisprudencia.Decision(
        title=record.title,
        url=record.url,
        source=record.source,
        citation=record.citation,
        case_number=record.case_number,
        date=record.date,
        subject=record.subject,
        snippet=(f"[página {record.page}] {record.excerpt}" if record.page else record.excerpt),
        page=record.page,
        relevance_score=max(1.0, score_record(record, query)),
        verified=True,
        verification_status=record.verification_level,
    )
    return decision
