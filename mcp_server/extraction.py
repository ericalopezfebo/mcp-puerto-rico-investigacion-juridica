from __future__ import annotations

import io
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from pypdf import PdfReader


@dataclass
class ExtractedText:
    text: str
    pages: list[tuple[int, str]]
    content_type: str


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_html(raw: bytes) -> ExtractedText:
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = clean(soup.get_text(" ", strip=True))
    return ExtractedText(text=text, pages=[], content_type="text/html")


def extract_pdf(raw: bytes) -> ExtractedText:
    reader = PdfReader(io.BytesIO(raw))
    pages: list[tuple[int, str]] = []
    for number, page in enumerate(reader.pages, start=1):
        text = clean(page.extract_text() or "")
        if text:
            pages.append((number, text))
    return ExtractedText(
        text="\n\n".join(text for _, text in pages),
        pages=pages,
        content_type="application/pdf",
    )


def find_passages(document: ExtractedText, terms: str, window: int = 900, max_passages: int = 8) -> list[dict]:
    tokens = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", terms or "") if len(t) > 2]
    if not tokens:
        return []
    passages: list[dict] = []
    for page, text in document.pages or [(None, document.text)]:
        lower = text.lower()
        for token in tokens:
            start = lower.find(token)
            if start < 0:
                continue
            passages.append({
                "texto": text[max(0, start - window): start + window],
                "termino": token,
                "pagina": page,
            })
            if len(passages) >= max_passages:
                return passages
    return passages
