from __future__ import annotations

import pytest

import jrt_server


def test_parse_jrt_page_keeps_official_docs_and_scores_topic():
    html = """
    <html><body>
      <a href="https://docs.pr.gov/files/JRT/AvisosDesestimacion/2023/mayo/CA-2021-30.pdf">
        CA-2021-30 Unión X y Empleado Y deber de justa representación Ley 130 2023 DJRT 4
      </a>
      <a href="https://example.com/not-official.pdf">Otro documento</a>
    </body></html>
    """
    rows = jrt_server._parse_jrt_reference_page(html, "deber de justa representación", 2)
    assert len(rows) == 1
    assert rows[0].url.startswith("https://docs.pr.gov/files/JRT/")
    assert rows[0].metadata_score > 0
    assert rows[0].kind == "aviso_desestimacion"


@pytest.mark.asyncio
async def test_jrt_search_only_returns_source_text_matches(monkeypatch):
    candidates = [
        jrt_server.JRTCandidate(
            title="CA-1 negociación colectiva",
            url="https://docs.pr.gov/files/JRT/Decisiones/ca1.pdf",
            page=1,
            metadata_score=5,
            kind="decision_y_orden",
        ),
        jrt_server.JRTCandidate(
            title="CA-2 otro asunto",
            url="https://docs.pr.gov/files/JRT/Decisiones/ca2.pdf",
            page=2,
            metadata_score=0,
            kind="decision_y_orden",
        ),
    ]

    async def fake_discover(query, paginas=25):
        return candidates

    async def fake_read(url, query, max_pasajes=6):
        if url.endswith("ca1.pdf"):
            return {
                "verificado": True,
                "coincidencia_tematica_verificada": True,
                "pasajes": [{"texto": "[página 4] negociación colectiva", "coincidencias": 2, "pagina": 4}],
                "advertencia": "verificar tratamiento posterior",
            }
        return {
            "verificado": True,
            "coincidencia_tematica_verificada": False,
            "pasajes": [],
        }

    monkeypatch.setattr(jrt_server, "_discover_jrt_candidates", fake_discover)
    monkeypatch.setattr(jrt_server.authority_reader, "read_public_authority", fake_read)

    result = await jrt_server.search_jrt_fulltext("negociación colectiva", maximo=5)
    assert result["total"] == 1
    row = result["resultados"][0]
    assert row["estado_verificacion"] == "texto_fuente_primaria_verificado"
    assert row["puede_citarse_como_proposicion_juridica"] is True
    assert row["pasajes"][0]["pagina"] == 4


def test_mixed_labor_classifier_is_conservative():
    import mixed_server

    assert mixed_server._looks_labor_related("práctica ilícita y negociación colectiva") is True
    assert mixed_server._looks_labor_related("pensión alimenticia de menores") is False
