import pytest

import doctrine_ontology
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


def test_intervention_query_expands_to_rule21_doctrinal_concepts():
    terms = dict(search_tuning.expanded_query_terms(
        "figura del interventor, intervención como cuestión de derecho e intervención permisible bajo la Regla 21"
    ))
    assert "regla 21" in terms
    assert "interes que amerite proteccion" in terms
    assert "representacion adecuada" in terms
    assert "economia procesal" in terms


def test_civil_intervention_beats_administrative_false_sense_for_rule21_query():
    query = "figura del interventor bajo la Regla 21"
    admin_blob = "Intervención administrativa ante una agencia, procedimiento adjudicativo e interés legítimo."
    civil_blob = "Regla 21 intervención de terceros; interés afectado; representación adecuada; parte interventora."
    assert search_tuning.improved_discovery_score(civil_blob, query) > search_tuning.improved_discovery_score(admin_blob, query)


def test_administrative_intervention_expands_differently_from_rule21():
    terms = dict(search_tuning.expanded_query_terms(
        "solicitud de intervención ante agencia en un procedimiento adjudicativo por interés legítimo"
    ))
    assert "procedimiento adjudicativo" in terms
    assert "interes legitimo" in terms
    assert "expediente completo" in terms


def test_jurisdiction_primary_and_exhaustion_are_distinct_but_related():
    primary = dict(search_tuning.expanded_query_terms("jurisdicción primaria exclusiva de una agencia"))
    exhaustion = dict(search_tuning.expanded_query_terms("agotamiento de remedios administrativos antes de revisión judicial"))
    assert "pericia administrativa" in primary
    assert "foro administrativo" in primary
    assert "futilidad" in exhaustion
    assert "revision judicial" in exhaustion


def test_evidence_ontology_distinguishes_hearsay_from_authentication():
    hearsay = dict(search_tuning.expanded_query_terms("prueba de referencia bajo la Regla 801"))
    auth = dict(search_tuning.expanded_query_terms("autenticación de evidencia bajo la Regla 901"))
    assert "declaracion fuera del tribunal" in hearsay
    assert "verdad de lo aseverado" in hearsay
    assert "cadena de custodia" in auth
    assert "caracteristicas distintivas" in auth


def test_constitutional_ontology_distinguishes_due_process_and_equal_protection():
    due = dict(search_tuning.expanded_query_terms("debido proceso de ley por privación de interés propietario"))
    equal = dict(search_tuning.expanded_query_terms("igual protección de las leyes y clasificación sospechosa"))
    assert "oportunidad de ser oido" in due
    assert "interes propietario" in due
    assert "clasificacion sospechosa" in equal
    assert "escrutinio estricto" in equal


def test_civil_ontology_distinguishes_indispensable_party_and_intervenor():
    indispensable = dict(search_tuning.expanded_query_terms("parte indispensable con interés real e inmediato"))
    intervenor = dict(search_tuning.expanded_query_terms("interventor Regla 21 interés afectado"))
    assert "persona ausente" in indispensable
    assert "multiplicidad de pleitos" in indispensable
    assert "representacion adecuada" in intervenor


def test_ontology_contains_multiple_areas_without_case_names():
    areas = {concept.area for concept in doctrine_ontology.LEGAL_CONCEPTS.values()}
    assert any("administrativo" in area for area in areas)
    assert any("procedimiento civil" in area for area in areas)
    assert any("evidencia" in area for area in areas)
    assert any("constitucional" in area for area in areas)
    blob = repr(doctrine_ontology.LEGAL_CONCEPTS).lower()
    assert "rivera padilla" not in blob
    assert "ig builders" not in blob


def test_unrelated_catalog_entry_still_scores_zero():
    query = "empleado de confianza a uno de carrera"
    assert search_tuning.improved_discovery_score("Derecho penal; registro y allanamiento", query) == 0


def test_top_five_verification_budget_is_bounded():
    assert smart_server.MAX_OFFICIAL_VERIFICATIONS == 24
    assert smart_server.VERIFY_BATCH_SIZE == 5
    assert smart_server._minimum_verifications_before_stability(5) == 15
