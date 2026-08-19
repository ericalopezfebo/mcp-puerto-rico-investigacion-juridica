import search_tuning
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
    assert search_tuning.improved_discovery_score(catalog_blob, query) > 0


def test_unrelated_catalog_entry_still_scores_zero():
    query = "empleado de confianza a uno de carrera"
    assert search_tuning.improved_discovery_score("Derecho penal; registro y allanamiento", query) == 0


def test_top_five_verification_budget_is_bounded():
    assert smart_server.MAX_OFFICIAL_VERIFICATIONS == 24
    assert smart_server.VERIFY_BATCH_SIZE == 5
    assert smart_server._minimum_verifications_before_stability(5) == 15
