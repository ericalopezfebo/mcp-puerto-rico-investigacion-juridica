import pytest

import search_tuning
import server
import smart_server


def test_confidential_employee_query_expands_to_due_process_and_career_concepts():
    terms = dict(search_tuning.expanded_query_terms(
        "reglamento crea un derecho propietario sobre la reinstalación de un empleado de confianza a uno de carrera"
    ))
    assert "debido proceso de ley" in terms
    assert "servicio de carrera" in terms
    assert "interes propietario" in terms
    assert "reglamento de personal" in terms


def test_doctrinal_expansion_can_surface_rivera_padilla_style_catalog_metadata():
    query = "reglamento crea un derecho propietario sobre la reinstalación de un empleado de confianza a uno de carrera"
    catalog_blob = (
        "Debido proceso de ley; igual paga por igual trabajo; "
        "aplicado a los Planes de Clasificación y Retribución"
    )
    assert search_tuning.improved_discovery_score(catalog_blob, query) >= 20


def test_verification_queries_split_combined_argument_into_doctrinal_questions():
    queries = search_tuning.doctrinal_verification_queries(
        "derecho administrativo: un reglamento crea un derecho propietario sobre la reinstalación de un empleado de confianza a uno de carrera"
    )
    normalized = [server.normalize_text(q) for q in queries]
    assert any("agencia obligada a seguir su reglamento" in q for q in normalized)
    assert any("planes de clasificacion" in q and "debido proceso" in q for q in normalized)
    assert any("empleado de confianza" in q and "servicio de carrera" in q for q in normalized)


@pytest.mark.asyncio
async def test_doctrine_aware_verifier_can_accept_case_when_exact_fact_pattern_is_absent(monkeypatch):
    candidate = smart_server.DiscoveryCandidate(
        citation="2013 TSPR 87",
        year=2013,
        title="Candidato doctrinal",
        context="Debido proceso de ley; Planes de Clasificación y Retribución",
        discovery_url="https://example.test/discovery",
        discovery_score=25.0,
    )
    base = server.Decision(
        title="Caso",
        url="https://dts.poderjudicial.pr/ts/2013/2013tspr87.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2013 TSPR 87",
        verified=True,
        verification_status="verified_source_identifier",
    )

    async def fake_citation_search(citation):
        assert citation == "2013 TSPR 87"
        return [base]

    async def fake_read_decision(decision, focused_query):
        if "agencia obligada a seguir su reglamento" in server.normalize_text(focused_query):
            decision.snippet = (
                "[página 20] Cuando una agencia promulga un reglamento, por imperativo del debido proceso de ley, "
                "está obligada a seguirlo y reconocer los derechos establecidos en éste."
            )
            decision.relevance_score = 12.0
        elif "planes de clasificacion" in server.normalize_text(focused_query):
            decision.snippet = "[página 4] Debido proceso de ley aplicado a los Planes de Clasificación y Retribución."
            decision.relevance_score = 8.0
        else:
            decision.snippet = "[página 1] Texto sin el patrón fáctico combinado solicitado por el usuario."
            decision.relevance_score = 0.0
        return decision

    def fake_confirm(decision, focused_query):
        snippet = server.normalize_text(decision.snippet)
        return "obligada a seguirlo" in snippet or "planes de clasificacion" in snippet

    monkeypatch.setattr(server, "citation_search", fake_citation_search)
    monkeypatch.setattr(server, "read_decision", fake_read_decision)
    monkeypatch.setattr(server, "_document_relevance_confirmed", fake_confirm)

    decision, score = await search_tuning.doctrine_aware_verify_candidate(
        candidate,
        "un reglamento crea un derecho propietario sobre la reinstalación de un empleado de confianza a uno de carrera",
    )
    assert decision is not None
    assert decision.citation == "2013 TSPR 87"
    assert score > 0


def test_unrelated_catalog_entry_still_scores_zero():
    query = "empleado de confianza a uno de carrera"
    assert search_tuning.improved_discovery_score("Derecho penal; registro y allanamiento", query) == 0


def test_top_five_verification_budget_is_bounded():
    assert smart_server.MAX_OFFICIAL_VERIFICATIONS == 24
    assert smart_server.VERIFY_BATCH_SIZE == 5
    assert smart_server._minimum_verifications_before_stability(5) == 15
