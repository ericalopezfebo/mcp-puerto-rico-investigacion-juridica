import pytest

import server
import smart_server


def test_parse_public_lexjuris_menu_extracts_candidate_and_topic_signal():
    html = """
    <html><body>
      <p><a href="lexj2015042.htm">2015 DTS 042 CASO A V. CASO B, 2015TSPR042</a></p>
      <p>Alimentos; pensión alimenticia</p>
      <p>Resumen: Regla sobre la obligación alimentaria y capacidad económica.</p>
      <p><a href="lexj2015043.htm">2015 DTS 043 OTRO CASO, 2015TSPR043</a></p>
      <p>Derecho penal</p>
    </body></html>
    """
    results = smart_server._parse_lexjuris_year_menu(
        html,
        2015,
        "pensión alimenticia",
        "https://www.lexjuris.com/LexJuris/tspr2015/lexj2015Menu.htm",
    )
    assert results
    assert results[0].citation == "2015 TSPR 42"
    assert results[0].year == 2015
    assert results[0].discovery_score > 0


def test_verified_rank_has_no_recency_bonus():
    old = server.Decision(
        title="Caso antiguo",
        url="https://dts.poderjudicial.pr/ts/2001/2001tspr10.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2001 TSPR 10",
        snippet="[página 5] La pensión alimenticia responde a la obligación alimentaria.",
        relevance_score=10.0,
        verified=True,
    )
    recent = server.Decision(
        title="Caso reciente",
        url="https://dts.poderjudicial.pr/ts/2026/2026tspr10.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2026 TSPR 10",
        snippet="[página 5] La pensión alimenticia responde a la obligación alimentaria.",
        relevance_score=10.0,
        verified=True,
    )
    assert smart_server._verified_rank(old, 5.0, "pensión alimenticia") == smart_server._verified_rank(
        recent, 5.0, "pensión alimenticia"
    )


def test_tangential_language_is_penalized():
    direct = server.Decision(
        title="Directo",
        url="https://dts.poderjudicial.pr/ts/2024/2024tspr1.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2024 TSPR 1",
        snippet="[página 4] La pensión alimenticia es la controversia que resolvemos.",
        relevance_score=6.0,
        verified=True,
    )
    tangential = server.Decision(
        title="Tangencial",
        url="https://dts.poderjudicial.pr/ts/2024/2024tspr2.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2024 TSPR 2",
        snippet="[página 4] La pensión alimenticia no es relevante para la controversia ante nuestra consideración.",
        relevance_score=6.0,
        verified=True,
    )
    assert smart_server._verified_rank(direct, 5.0, "pensión alimenticia") > smart_server._verified_rank(
        tangential, 5.0, "pensión alimenticia"
    )


@pytest.mark.asyncio
async def test_relevance_loop_can_rank_older_case_above_recent_case(monkeypatch):
    candidates = [
        smart_server.DiscoveryCandidate(
            citation="2015 TSPR 50",
            year=2015,
            title="Caso doctrinal",
            context="pensión alimenticia obligación alimentaria",
            discovery_url="https://www.lexjuris.com/x",
            discovery_score=20.0,
        ),
        smart_server.DiscoveryCandidate(
            citation="2026 TSPR 20",
            year=2026,
            title="Caso reciente",
            context="pensión alimenticia",
            discovery_url="https://www.lexjuris.com/y",
            discovery_score=10.0,
        ),
    ]

    async def fake_discovery(query, years):
        return list(candidates)

    async def fake_verify(candidate, query):
        rel = 12.0 if candidate.year == 2015 else 4.0
        decision = server.Decision(
            title=candidate.title,
            url=f"https://dts.poderjudicial.pr/ts/{candidate.year}/{candidate.year}tspr1.pdf",
            source="Poder Judicial de Puerto Rico",
            citation=candidate.citation,
            snippet="[página 3] La pensión alimenticia y la obligación alimentaria son materia de la controversia.",
            relevance_score=rel,
            verified=True,
            verification_status="verified_source_identifier",
        )
        return decision, smart_server._verified_rank(decision, candidate.discovery_score, query)

    monkeypatch.setattr(smart_server, "_global_discovery", fake_discovery)
    monkeypatch.setattr(smart_server, "_verify_candidate", fake_verify)
    monkeypatch.setattr(smart_server, "STABLE_ROUNDS_REQUIRED", 0)

    result = await smart_server.relevance_first_search(
        "pensión alimenticia", maximo=2, ano_desde=1997, ano_hasta=2026
    )
    assert result["total"] == 2
    assert result["resultados"][0]["citation"] == "2015 TSPR 50"
    assert result["resultados"][1]["citation"] == "2026 TSPR 20"
    assert result["orden"] == "relevancia verificada; sin bono por recencia"


def test_citation_chain_extractor_deduplicates():
    text = "Véase 2012 TSPR 160 y 2012 TSPR 160; también 2009 TSPR 187."
    assert smart_server._all_tspr_citations(text) == ["2012 TSPR 160", "2009 TSPR 187"]
