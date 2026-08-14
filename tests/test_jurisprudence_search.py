from server import Decision, extract_citation, find_relevant_paragraphs, query_terms, score_document


def test_extracts_tspr_citation_without_invention():
    assert extract_citation("Opinion del Tribunal, 2025 TSPR 146") == "2025 TSPR 146"
    assert extract_citation("No hay cita aquí") == ""


def test_expands_alimentos_terms():
    terms = {term.lower() for term in query_terms("pensión alimenticia")}
    assert "alimentos" in terms
    assert "alimentante" in terms
    assert "obligacion alimentaria" in terms


def test_relevant_passages_are_source_text():
    paragraphs = [
        "Antecedentes generales del caso.",
        "La obligación alimentaria de los padres respecto de sus hijos menores se analiza conforme a la ley.",
        "El Tribunal examinó otros asuntos procesales.",
    ]
    results = find_relevant_paragraphs(paragraphs, "pensión alimenticia", limit=2)
    assert results
    assert "obligación alimentaria" in results[0]["texto"]
    assert results[0]["numero"] == 2


def test_document_score_requires_actual_text_match():
    decision = Decision(
        title="2025 TSPR 146",
        url="https://poderjudicial.pr/example.pdf",
        source="Poder Judicial de Puerto Rico",
        citation="2025 TSPR 146",
        verified=True,
    )
    text = "La obligación alimentaria y la pensión alimenticia fueron discutidas en la opinión."
    paragraphs = ["[página 12] La obligación alimentaria y la pensión alimenticia fueron discutidas en la opinión."]
    score, passage = score_document(decision, text, paragraphs, "pensión alimenticia")
    assert score > 0
    assert passage is not None
    assert "pensión alimenticia" in passage["texto"]
