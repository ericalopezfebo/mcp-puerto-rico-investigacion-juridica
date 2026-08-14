from __future__ import annotations

import re
from collections import Counter


def _tokens(value: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", value or "") if len(t) > 2]


def score(query: str, decision: dict) -> float:
    q = Counter(_tokens(query))
    blob = " ".join(str(decision.get(key, "")) for key in ("title", "citation", "case_number", "subject", "snippet")).lower()
    words = Counter(_tokens(blob))
    overlap = sum(min(count, words[token]) for token, count in q.items())
    exact_bonus = 2.0 if query.strip().lower() in blob else 0.0
    verified_bonus = 3.0 if decision.get("verified") else -10.0
    return overlap + exact_bonus + verified_bonus


def rank(query: str, decisions: list[dict]) -> list[dict]:
    ranked = [dict(item, relevance_score=score(query, item)) for item in decisions]
    return sorted(ranked, key=lambda item: item["relevance_score"], reverse=True)
