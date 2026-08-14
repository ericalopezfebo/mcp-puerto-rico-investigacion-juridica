from __future__ import annotations

import re
from urllib.parse import urlparse

TSPR_RE = re.compile(r"\b((?:19|20)\d{2}\s*TSPR\s*\d{1,4})\b", re.I)

ALLOWED_HOSTS = {
    "poderjudicial.pr",
    "www.poderjudicial.pr",
    "lexjuris.com",
    "www.lexjuris.com",
}


def normalize_citation(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().upper().replace("-", " "))


def extract_citation(text: str) -> str:
    match = TSPR_RE.search(text or "")
    return match.group(1).strip() if match else ""


def allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
    except Exception:
        return False


def exact_citation_match(requested: str, candidate: str) -> bool:
    return bool(candidate) and normalize_citation(requested) == normalize_citation(candidate)


def verified_metadata(*, url: str, citation: str, source_identifier_present: bool) -> bool:
    """Conservative verification gate; never infers missing legal metadata."""
    return allowed_url(url) and bool(citation) and source_identifier_present
