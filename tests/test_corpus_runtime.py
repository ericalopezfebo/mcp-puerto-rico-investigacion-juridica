import pytest

import corpus_index
import corpus_runtime
import smart_server


def test_local_corpus_surfaces_jurisdiccion_primaria_without_network():
    rows = corpus_index.search_corpus(
        "jurisdicción primaria exclusiva y concurrente, pericia administrativa y cuestión estrictamente de derecho",
        years=list(range(1997, 2027)),
        limit=10,
    )
    citations = [record.citation for record, _score in rows]
    assert "2020 TSPR 26" in citations
    assert "2014 TSPR 123" in citations
    assert len(citations) >= 3


def test_cached_decision_preserves_official_provenance_and_status():
    decision = corpus_index.cached_decision("2020 TSPR 26", "jurisdicción primaria")
    assert decision is not None
    assert decision.verified is True
    assert decision.url.startswith("https://dts.poderjudicial.pr/")
    assert decision.verification_status == "cached_official_excerpt"
    assert decision.page is not None


def test_estado_corpus_reports_persistent_local_runtime_without_network():
    result = corpus_runtime.estado_corpus_jurisprudencia()
    assert result["corpus_disponible"] is True
    assert result["corpus_persistente_local"] is True
    assert result["corpus_first_activo"] is True
    assert result["registros"] >= 5
    assert result["busqueda_local_sin_red"] is True


def test_buscar_corpus_local_returns_candidates_and_zero_external_access():
    result = corpus_runtime.buscar_corpus_jurisprudencia(
        "jurisdicción primaria exclusiva concurrente pericia administrativa",
        maximo=10,
    )
    citations = [row["citation"] for row in result["resultados"]]
    assert result["accesos_externos"] == 0
    assert result["estrategia"] == "persistent_local_corpus_only_no_network"
    assert "2020 TSPR 26" in citations
    assert "2014 TSPR 123" in citations


@pytest.mark.asyncio
async def test_corpus_first_discovery_does_not_need_live_source_when_local_pool_is_sufficient(monkeypatch):
    async def should_not_run(*_args, **_kwargs):
        raise AssertionError("live discovery should not run")

    monkeypatch.setattr(corpus_runtime, "_live_global_discovery", should_not_run)
    rows = await corpus_runtime.corpus_first_global_discovery(
        "jurisdicción primaria exclusiva concurrente pericia administrativa",
        list(range(1997, 2027)),
    )
    assert len(rows) >= 3
    assert all(row.discovered_by == "local_primary_source_corpus" for row in rows)


@pytest.mark.asyncio
async def test_cached_official_excerpt_is_fallback_when_live_verification_times_out(monkeypatch):
    async def fail_live(*_args, **_kwargs):
        raise TimeoutError("simulated public source outage")

    monkeypatch.setattr(corpus_runtime, "_live_verify_candidate", fail_live)
    candidate = smart_server.DiscoveryCandidate(
        citation="2020 TSPR 26",
        year=2020,
        title="Beltrán Cintrón",
        context="jurisdicción primaria",
        discovery_url="https://dts.poderjudicial.pr/ts/2020/2020tspr26.pdf",
        discovery_score=20.0,
        discovered_by="local_primary_source_corpus",
    )
    decision, score = await corpus_runtime.resilient_verify_candidate(candidate, "jurisdicción primaria")
    assert decision is not None
    assert decision.verification_status == "cached_official_excerpt"
    assert score > 0
