from server import (
    Decision,
    extract_case_number,
    extract_citation,
    find_relevant_paragraphs,
    normalize_citation,
    parse_index,
)


def test_citation_normalization_is_deterministic():
    assert normalize_citation("2024 TSPR-140") == "2024 TSPR 140"


def test_extract_citation_only_accepts_explicit_tspr():
    assert extract_citation("Caso 2024 TSPR 140") == "2024 TSPR 140"
    assert extract_citation("Caso 2024 140") == ""


def test_case_number_is_not_invented():
    assert extract_case_number("No hay número de caso aquí") == ""
    assert extract_case_number("CC-2024-0123") == "CC-2024-0123"


def test_index_parser_does_not_invent_metadata():
    html = '''
    <html><body>
      <a href="https://poderjudicial.pr/example.pdf">2024 TSPR 140</a>
      <a href="https://poderjudicial.pr/other.pdf">Decision without citation</a>
    </body></html>
    '''
    results = parse_index(html, "https://poderjudicial.pr/", None)
    assert len(results) == 2
    assert results[0].citation == "2024 TSPR 140"
    assert results[0].verified is True
    assert results[1].citation == ""
    assert results[1].case_number == ""
    assert results[1].verified is False


def test_relevant_paragraphs_return_source_blocks_not_generated_text():
    paragraphs = [
        "Este párrafo trata sobre jurisdicción.",
        "Este párrafo trata sobre prescripción y daños.",
        "Este párrafo trata sobre arbitraje.",
    ]
    results = find_relevant_paragraphs(paragraphs, "prescripción", 2)
    assert results[0]["numero"] == 2
    assert "prescripción" in results[0]["texto"].lower()
    assert len(results) == 1
