from __future__ import annotations

import pytest

import mixed_server


@pytest.mark.asyncio
async def test_mixed_research_keeps_index_discovery_out_of_verified_ranking(monkeypatch):
    async def fake_tspr(query, maximo=5, **kwargs):
        return {
            "resultados": [
                {
                    "citation": "2012 TSPR 160",
                    "title": "Caso verificado",
                    "url": "https://dts.poderjudicial.pr/ts/2012/2012tspr160.pdf",
                    "ranking_relevancia": 91.0,
                    "verified": True,
                }
            ]
        }

    async def fake_library(query, maximo=8):
        return {
            "resultados": [
                {
                    "titulo": "Ley de ejemplo",
                    "url": "https://bibliotecavirtual.estado.pr.gov/ejemplo",
                    "nivel_fuente": "fuente_primaria_oficial",
                    "verificado": True,
                }
            ]
        }

    async def fake_labor(query, maximo=8):
        return {"resultados": []}

    monkeypatch.setattr(mixed_server.smart_server, "relevance_first_search", fake_tspr)
    monkeypatch.setattr(mixed_server.research_server, "buscar_biblioteca_juridica", fake_library)
    monkeypatch.setattr(mixed_server.research_server, "buscar_decisiones_laborales", fake_labor)

    result = await mixed_server.mixed_authority_research("pensión alimenticia", maximo=5)

    assert len(result["autoridades_verificadas"]) == 1
    assert result["autoridades_verificadas"][0]["citation"] == "2012 TSPR 160"
    assert result["autoridades_verificadas"][0]["puede_citarse_como_proposicion_juridica"] is True

    assert len(result["candidatos_primarios_por_verificar"]) == 1
    candidate = result["candidatos_primarios_por_verificar"][0]
    assert candidate["tipo_autoridad"] == "legislacion_reglamentos_ejecutivo"
    assert candidate["puede_citarse_como_proposicion_juridica"] is False
    assert "pendiente_de_verificar" in candidate["estado_verificacion"]


@pytest.mark.asyncio
async def test_secondary_news_never_enters_authority_ranking(monkeypatch):
    async def fake_tspr(query, maximo=5, **kwargs):
        return {"resultados": []}

    async def empty(query, maximo=8):
        return {"resultados": []}

    async def news(query, maximo=8):
        return {"resultados": [{"titulo": "Nueva doctrina", "url": "https://aldia.microjuris.com/x"}]}

    monkeypatch.setattr(mixed_server.smart_server, "relevance_first_search", fake_tspr)
    monkeypatch.setattr(mixed_server.research_server, "buscar_biblioteca_juridica", empty)
    monkeypatch.setattr(mixed_server.research_server, "buscar_decisiones_laborales", empty)
    monkeypatch.setattr(mixed_server.research_server, "buscar_actualidad_juridica", news)

    result = await mixed_server.mixed_authority_research(
        "doctrina Chevron", maximo=5, incluir_actualidad=True
    )

    assert result["autoridades_verificadas"] == []
    assert len(result["actualidad_secundaria"]) == 1
    assert result["actualidad_secundaria"][0]["tipo_fuente"] == "fuente_secundaria_publica"
