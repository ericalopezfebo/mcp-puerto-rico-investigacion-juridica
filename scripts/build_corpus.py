"""GitHub Actions entrypoint for incremental TSPR corpus refresh.

Environment variables:
- CORPUS_YEARS="2020,2021" refreshes explicit years.
- CORPUS_FULL_REBUILD=1 refreshes 1997..current (manual use; potentially slow).
- CORPUS_MAX_DOCS optionally caps documents per year for smoke tests.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from pathlib import Path

import corpus_builder
import corpus_index


def requested_years() -> list[int]:
    current = date.today().year
    explicit = os.getenv("CORPUS_YEARS", "").strip()
    if explicit:
        values = {int(x.strip()) for x in explicit.split(",") if x.strip().isdigit()}
        return sorted(year for year in values if 1997 <= year <= current)
    if os.getenv("CORPUS_FULL_REBUILD", "").lower() in {"1", "true", "yes"}:
        return list(range(1997, current + 1))
    return [max(1997, current - 1), current]


def max_docs() -> int | None:
    value = os.getenv("CORPUS_MAX_DOCS", "").strip()
    return int(value) if value.isdigit() and int(value) > 0 else None


async def main() -> None:
    target = Path(corpus_index.CORPUS_PATH)
    existing = corpus_builder.load_raw_records(target)
    incoming: list[dict] = []
    years = requested_years()
    for year in years:
        rows = await corpus_builder.build_year(
            year,
            max_docs=max_docs(),
            concurrency=corpus_builder.DEFAULT_CONCURRENCY,
        )
        incoming.extend(rows)
        print(f"year={year} official_records_captured={len(rows)}")

    merged = corpus_builder.merge_records(existing, incoming)
    corpus_builder.write_records(target, merged)
    print(json.dumps({
        "existing": len(existing),
        "captured_this_run": len(incoming),
        "total_after_merge": len(merged),
        "years_refreshed": years,
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
