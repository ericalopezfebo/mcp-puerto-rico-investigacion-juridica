from __future__ import annotations

import pytest

import authority_reader


class FakeResponse:
    def __init__(self, text: str, content_type: str = "text/html"):
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": content_type}


@pytest.mark.asyncio
async def test_reader_rejects_unknown_host():
    result = await authority_reader.read_public_authority(
        "https://example.com/fake-law", "pensión alimenticia"
    )
    assert result["verificado"] is False
    assert "no permitida" in result["error"].lower()


@pytest.mark.asyncio
async def test_reader_extracts_exact_passage_from_allowed_html(monkeypatch):
    html = """
    <html><body>
      <p>Artículo 1. Esta disposición regula asuntos generales de la agencia.</p>
      <p>Artículo 2. La pensión alimenticia se atenderá conforme a la ley aplicable.</p>
    </body></html>
    """

    async def fake_fetch(url):
        return FakeResponse(html)

    monkeypatch.setattr(authority_reader.research_server, "_fetch", fake_fetch)
    result = await authority_reader.read_public_authority(
        "https://bibliotecavirtual.estado.pr.gov/documento/1",
        "pensión alimenticia",
    )

    assert result["verificado"] is True
    assert result["coincidencia_tematica_verificada"] is True
    assert result["pasajes"]
    assert "pensión alimenticia" in result["pasajes"][0]["texto"].lower()
    assert result["advertencia"]
