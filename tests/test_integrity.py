from mcp_server.extraction import ExtractedText, find_passages
from mcp_server.verification import allowed_url, exact_citation_match, extract_citation


def test_missing_citation_is_not_accepted():
    assert exact_citation_match("2024 TSPR 140", "2024 TSPR 141") is False


def test_citation_extraction_is_conservative():
    assert extract_citation("Caso X, 2024 TSPR 140") == "2024 TSPR 140"
    assert extract_citation("caso inventado 2024-140") == ""


def test_only_allowed_https_sources():
    assert allowed_url("https://poderjudicial.pr/foo")
    assert allowed_url("https://www.lexjuris.com/foo")
    assert not allowed_url("http://poderjudicial.pr/foo")
    assert not allowed_url("https://example.com/foo")


def test_passage_comes_from_source_text():
    document = ExtractedText(
        text="El Tribunal resolvió sobre prescripción y jurisdicción.",
        pages=[],
        content_type="text/html",
    )
    passages = find_passages(document, "prescripción")
    assert passages
    assert "prescripción" in passages[0]["texto"].lower()
