import pytest

import legal_research_loop as loop


def _row(citation: str, score: float = 10.0):
    return {
        "citation": citation,
        "title": f"Caso {citation}",
        "snippet": "reclasificación puesto funciones principio mérito",
        "verified": True,
        "verification_status": "VERIFIED",
        "ranking_relevancia": score,
        "url": f"https://poderjudicial.pr/{citation.replace(' ', '-')}.pdf",
    }


def test_build_queries_includes_adverse_pass():
    queries = loop.build_queries(
        "Cuándo procede reclasificar un puesto",
        "Funciones adicionales no obligan automáticamente a reclasificar",
        ["No consta cuándo comenzaron las funciones"],
        True,
    )
    purposes = [purpose for purpose, _ in queries]
    assert "proposicion_directa" in purposes
    assert "potencialmente_adversa" in purposes


def test_round_budget_is_bounded():
    assert loop.MAX_ALLOWED_ROUNDS == 6
    assert loop.DEFAULT_MAX_ROUNDS <= loop.MAX_ALLOWED_ROUNDS


@pytest.mark.asyncio
async def test_loop_stops_and_returns_audit_log(monkeypatch):
    calls = []

    async def fake_search(query, maximo, ano_desde, ano_hasta):
        calls.append(query)
        return {"resultados": [_row(f"2020 TSPR {n}", 20 - n) for n in range(1, 8)]}

    monkeypatch.setattr(loop.smart_server, "relevance_first_search", fake_search)
    monkeypatch.setattr(loop, "STABLE_ROUNDS_REQUIRED", 0)
    result = await loop.legal_research_loop(
        pregunta_juridica="Cuándo procede reclasificar",
        proposicion_a_sostener="Funciones adicionales no obligan automáticamente",
        hechos_materiales=["No existe fecha de comienzo"],
        maximo=5,
        incluir_contrarias=False,
        max_rondas=3,
    )
    assert result["estado"] == "COMPLETO_PARA_REVISION_HUMANA"
    assert result["motivo_parada"] == "CRITERIOS_CUMPLIDOS"
    assert len(result["resultados"]) == 5
    assert result["registro_busqueda"]
    assert len(calls) <= 3


@pytest.mark.asyncio
async def test_loop_reports_partial_instead_of_padding(monkeypatch):
    async def fake_search(query, maximo, ano_desde, ano_hasta):
        return {"resultados": [_row("2020 TSPR 1")]}

    monkeypatch.setattr(loop.smart_server, "relevance_first_search", fake_search)
    result = await loop.legal_research_loop(
        pregunta_juridica="Pregunta",
        proposicion_a_sostener="Proposición",
        maximo=5,
        incluir_contrarias=True,
        max_rondas=4,
    )
    assert result["estado"] == "PARCIAL_REQUIERE_REVISION"
    assert result["autoridades_calificadas"] == 1
    assert result["vacios"]
    assert len(result["registro_busqueda"]) == 4
