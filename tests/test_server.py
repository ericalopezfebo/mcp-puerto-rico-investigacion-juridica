"""Fast, network-free tests for server.py (the active MCP entrypoint)."""
import server


def test_sample_evenly_is_deterministic():
    items = [server.Decision(title=str(i), url=f"u{i}", source="s") for i in range(10)]
    first = server.sample_evenly(items, 4)
    second = server.sample_evenly(items, 4)
    assert [d.url for d in first] == [d.url for d in second]
    assert len(first) == 4


def test_sample_evenly_edge_cases():
    items = [server.Decision(title="a", url="u1", source="s")]
    assert server.sample_evenly([], 5) == []
    assert server.sample_evenly(items, 0) == []
    assert server.sample_evenly(items, 5) == items


def test_parse_index_only_extracts_decision_like_links():
    html = """
    <a href="/tribunal-supremo/decisiones-del-tribunal-supremo-2025/">2025</a>
    <a href="https://dts.poderjudicial.pr/ts/2025/2025tspr146.pdf">2025 TSPR 146</a>
    <a href="/contacto">Contacto</a>
    """
    results = server.parse_index(html, "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/")
    urls = [r.url for r in results]
    assert any(u.endswith("2025tspr146.pdf") for u in urls)
    assert not any("contacto" in u for u in urls)


def test_parse_index_no_matches_returns_empty_list():
    html = '<a href="/contacto">Contacto</a><a href="/nosotros">Nosotros</a>'
    results = server.parse_index(html, "https://poderjudicial.pr/")
    assert results == []


def test_query_terms_expands_pension_alimenticia_synonyms():
    terms = [server.normalize_text(t) for t in server.query_terms("pensión alimenticia")]
    assert server.normalize_text("alimentos") in terms
    assert server.normalize_text("manutención") in terms


def _year_index_with(n_decisions: int) -> list:
    """Simulate a full year index: many decisions, all superficially similar,
    as they are on the real site (titles are just the citation string)."""
    return [
        server.Decision(
            title=f"2025 TSPR {n}", url=f"https://dts.poderjudicial.pr/ts/2025/2025tspr{n}.pdf",
            source="Poder Judicial de Puerto Rico", citation=f"2025 TSPR {n}", verified=True,
        )
        for n in range(1, n_decisions + 1)
    ]


def _patch_get_year_links_and_read(monkeypatch, candidates):
    async def fake_get_year_links(year):
        return candidates

    async def fake_read_decision(decision, query):
        return decision  # already "verified" by the fake index; no real fetch

    monkeypatch.setattr(server, "get_year_links", fake_get_year_links)
    monkeypatch.setattr(server, "read_decision", fake_read_decision)


def test_citation_search_finds_two_digit_number(monkeypatch):
    """Regression test: this exact scenario used to raise a NameError and,
    after that was fixed, still silently failed to find low-numbered
    citations because query_terms() drops 1-2 digit tokens as noise, which
    made every decision in the year score identically and truncated "25"
    out before the exact-match check ever ran."""
    import asyncio

    _patch_get_year_links_and_read(monkeypatch, _year_index_with(150))
    found = asyncio.run(server.citation_search("2025 TSPR 25"))
    assert len(found) == 1
    assert found[0].citation == "2025 TSPR 25"


def test_citation_search_finds_three_digit_number(monkeypatch):
    import asyncio

    _patch_get_year_links_and_read(monkeypatch, _year_index_with(150))
    found = asyncio.run(server.citation_search("2025 TSPR 128"))
    assert len(found) == 1
    assert found[0].citation == "2025 TSPR 128"


def test_citation_search_nonexistent_citation_returns_empty(monkeypatch):
    import asyncio

    _patch_get_year_links_and_read(monkeypatch, _year_index_with(150))
    found = asyncio.run(server.citation_search("2025 TSPR 999999"))
    assert found == []


def test_extract_cover_metadata_adversarial_case():
    paragraphs = [
        "[página 1] EN EL TRIBUNAL SUPREMO DE PUERTO RICO",
        "[página 1] Maribel Rivera Ortiz",
        "[página 1] Peticionaria",
        "[página 1] v.",
        "[página 1] Melvin Rolón Merced",
        "[página 1] Recurrido",
        "[página 1] Certiorari",
        "[página 1] 2025 TSPR 25",
        "[página 1] 215 DPR ___",
        "[página 1] Número del Caso: CC-2023-0076",
        "[página 1] Fecha: 17 de marzo de 2025",
    ]
    meta = server.extract_cover_metadata(paragraphs)
    assert meta["case_number"] == "CC-2023-0076"
    assert meta["date"] == "17 de marzo de 2025"
    assert meta["case_name"] == "Maribel Rivera Ortiz v. Melvin Rolón Merced"


def test_extract_cover_metadata_in_re_case():
    paragraphs = [
        "[página 1] EN EL TRIBUNAL SUPREMO DE PUERTO RICO",
        "[página 1] In re:",
        "[página 1] Elaine Santos Negrón",
        "[página 1] 2023 TSPR 116",
        "[página 1] Número del Caso: TS-9,614",
        "[página 1] Fecha: 26 de septiembre de 2023",
    ]
    meta = server.extract_cover_metadata(paragraphs)
    assert meta["case_number"] == "TS-9,614"
    assert meta["case_name"] == "In re: Elaine Santos Negrón"


def test_extract_cover_metadata_missing_layout_stays_empty():
    """If the cover page doesn't match the known layout, every field must
    stay empty rather than guessed."""
    paragraphs = ["[página 1] Un documento sin la carátula esperada."]
    meta = server.extract_cover_metadata(paragraphs)
    assert meta == {"case_number": "", "date": "", "case_name": ""}


def test_pension_alimenticia_synonyms_no_longer_include_generic_word():
    """Regression test for the false-positive source: 'sustento' is a common
    word ("earn a living") that matched unrelated attorney-discipline cases
    under a pensión alimenticia search. It must not be a synonym anymore."""
    synonyms = server.LEGAL_SYNONYMS["pension alimenticia"]
    assert "sustento" not in [server.normalize_text(s) for s in synonyms]


def test_query_terms_ignores_institutional_boilerplate_in_complex_question():
    terms = [server.normalize_text(t) for t in server.query_terms(
        "Encuentra las mejores 5 decisiones del Tribunal Supremo de Puerto Rico "
        "que apoyen este argumento sobre pensión alimenticia"
    )]
    for boilerplate in ("tribunal", "supremo", "puerto", "rico", "decisiones"):
        assert boilerplate not in terms
    assert server.normalize_text("alimentos") in terms


def test_passage_is_exact_substring_of_source_document():
    """The returned 'pasaje textual' must be a verbatim excerpt of the
    source, never a paraphrase generated separately."""
    paragraphs = [
        "[página 3] El Tribunal resolvió que la obligación alimentaria "
        "no cesa automáticamente al alcanzar la mayoría de edad.",
    ]
    relevant = server.find_relevant_paragraphs(paragraphs, "obligación alimentaria mayoría de edad")
    assert relevant
    assert relevant[0]["texto"] in paragraphs[0]
    assert relevant[0]["numero"] == 1


def test_single_incidental_term_is_not_confirmed_as_relevant():
    """A lone generic word shared with the query (e.g. one attorney-discipline
    case that happens to mention 'sustento') must not be enough evidence to
    call a document relevant — that is exactly how a false 'authority' would
    get invented."""
    weak = server.Decision(
        title="2022 TSPR 107", url="https://dts.poderjudicial.pr/ts/2022/2022tspr107.pdf",
        source="Poder Judicial de Puerto Rico", citation="2022 TSPR 107",
        snippet="[página 1] Suspensión inmediata del ejercicio de la abogacía; "
                "la licenciada depende de esa profesión para su sustento diario.",
        relevance_score=5.0, verified=True,
    )
    assert server._document_relevance_confirmed(weak, "pensión alimenticia") is False


def test_multi_concept_match_is_confirmed_as_relevant():
    strong = server.Decision(
        title="2024 TSPR 27", url="https://dts.poderjudicial.pr/ts/2024/2024tspr27.pdf",
        source="Poder Judicial de Puerto Rico", citation="2024 TSPR 27",
        snippet="[página 12] la obligación de proveer alimentos no cesa automáticamente; "
                "la pensión alimenticia continúa hasta que un tribunal decrete un relevo.",
        relevance_score=40.0, verified=True,
    )
    assert server._document_relevance_confirmed(strong, "pensión alimenticia") is True


def test_two_generic_words_without_a_specific_phrase_is_rejected():
    """Regression test found via a real search: an attorney-discipline
    opinion mentioning a client's alimony claim only as background context
    ("fue contratado para solicitar alimentos y/o pensión excónyuge") hit two
    generic query words ("pensión", "alimentos") without the specific phrase
    "pensión alimenticia"/"alimentaria" or any other precise legal term ever
    appearing — that must not be enough to call the case relevant."""
    false_positive = server.Decision(
        title="2025 TSPR 9", url="https://dts.poderjudicial.pr/ts/2025/2025tspr9.pdf",
        source="Poder Judicial de Puerto Rico", citation="2025 TSPR 9",
        snippet="[página 6] fue contratado única y exclusivamente para solicitar "
                "alimentos y/o pensión excónyuge, sin relación con la custodia.",
        relevance_score=14.2, verified=True,
    )
    assert server._document_relevance_confirmed(false_positive, "pensión alimenticia") is False


def test_attorney_discipline_matter_rejected_despite_exact_phrase_match():
    """Regression test found via a real search: an "In re:" attorney
    discipline complaint (CP- case number) that literally says "revisión de
    pensión alimentaria" and "la pensión alimentaria se fijó" — an exact
    phrase match, which would otherwise pass — is not a ruling on pensión
    alimenticia; it's the Tribunal disciplining a lawyer. Must be rejected
    unless the query itself is about attorney conduct."""
    discipline_case = server.Decision(
        title="In re: Sharon M. Hernández López (TS-16,345)",
        url="https://dts.poderjudicial.pr/ts/2025/2025tspr87.pdf",
        source="Poder Judicial de Puerto Rico", citation="2025 TSPR 87",
        case_number="CP-2020-0003 CP-2020-0008",
        snippet="[página 11] para que lo representara en un caso sobre revisión de "
                "pensión alimentaria... la pensión alimentaria se fijó previo a que "
                "esta asumiera su representación, conducta profesional impropia.",
        relevance_score=12.7, verified=True,
    )
    assert server._looks_like_discipline_matter(discipline_case) is True
    assert server._document_relevance_confirmed(discipline_case, "pensión alimenticia") is False
    # But a query actually about attorney conduct should still be able to reach it
    # (the veto only guards against unrelated topical searches, not conduct ones).
    assert server._document_relevance_confirmed(discipline_case, "conducta profesional") is True


def test_long_generic_word_from_query_is_not_treated_as_specific():
    """Regression test found via a real complex-question search: "obligación"
    (10 chars) is a raw word from the user's own question, not from the
    curated synonym dictionary — it's generic legal vocabulary (contracts,
    trusts, torts...) and must not alone unlock the co-occurrence bypass,
    even though it's long enough to look "specific" by length alone. It
    matched an unrelated trust/estate case for real."""
    trust_case = server.Decision(
        title="Michael Allio v. Carmen Santiago Chardón",
        url="https://dts.poderjudicial.pr/ts/2026/2026tspr13.pdf",
        source="Poder Judicial de Puerto Rico", citation="2026 TSPR 13",
        snippet="[página 4] el fiduciario tiene la obligación de administrar los "
                "bienes del fideicomiso conforme a sus términos.",
        relevance_score=20.0, verified=True,
    )
    long_question = (
        "Encuentra las mejores decisiones que apoyen un argumento sobre la "
        "obligación de proveer alimentos a hijos menores."
    )
    assert server._is_specific_term("obligación") is False
    assert server._document_relevance_confirmed(trust_case, long_question) is False


def test_morphological_variants_of_one_concept_are_not_three_signals():
    """Regression test found via a real complex-question search: "hijos",
    "hijo", "hija" are all the SAME curated synonym family ("menor" —
    children in general), so a document that only mentions children in
    passing (a trust/estate case naming heirs) hit all three as distinct
    strings, crossing the old flat distinct_hits>=3 bar. They must collapse
    to one family and not be trusted alone."""
    trust_case = server.Decision(
        title="Michael Allio v. Carmen Santiago Chardón",
        url="https://dts.poderjudicial.pr/ts/2026/2026tspr13.pdf",
        source="Poder Judicial de Puerto Rico", citation="2026 TSPR 13",
        snippet="[página 4] instituyó a sus hijos como herederos del caudal; "
                "cada hijo e hija recibirá una porción del fideicomiso.",
        relevance_score=20.0, verified=True,
    )
    assert server._document_relevance_confirmed(trust_case, "hijos menores") is False


def test_two_distinct_curated_families_are_confirmed_as_relevant():
    """Genuine concept diversity — hits from two different curated topic
    families, not just word-form repeats of one — is real signal."""
    custody_and_children = server.Decision(
        title="X v. Y", url="https://dts.poderjudicial.pr/ts/2025/2025tspr1.pdf",
        source="Poder Judicial de Puerto Rico", citation="2025 TSPR 1",
        snippet="[página 3] el tribunal otorgó la custodia de los hijos menores a la madre.",
        relevance_score=15.0, verified=True,
    )
    assert server._document_relevance_confirmed(custody_and_children, "custodia de hijos menores") is True


def test_rule_making_docket_rejected_despite_exact_phrase_match():
    """Regression test found via a real search: "In re: Aprobación de las
    Reglas de Conducta Profesional..." (case number ER-2025-0002) is the
    Court adopting attorney-conduct rules, not deciding a pensión
    alimenticia dispute — even though one rule, about contingent fees in
    family cases, literally mentions "pensión de alimentos"."""
    rule_docket = server.Decision(
        title="In re: Aprobación de las Reglas de Conducta Profesional de Puerto Rico",
        url="https://dts.poderjudicial.pr/ts/2025/2025tspr64.pdf",
        source="Poder Judicial de Puerto Rico", citation="2025 TSPR 64",
        case_number="ER-2025-0002",
        snippet="[página 118] prohíbe que una persona que ejerce la abogacía cobre "
                "honorarios contingentes en una controversia sobre pensión de alimentos.",
        relevance_score=27.5, verified=True,
    )
    assert server._looks_like_discipline_matter(rule_docket) is True
    assert server._document_relevance_confirmed(rule_docket, "pensión alimenticia") is False


def test_pension_alimentaria_variant_phrase_is_confirmed_as_relevant():
    """"Pensión alimentaria" (not just "alimenticia") is the other common
    phrasing used across real TSPR opinions and must be recognized as a
    specific term on its own, without needing 3 separate generic hits."""
    tangential = server.Decision(
        title="2023 TSPR 83", url="https://dts.poderjudicial.pr/ts/2023/2023tspr83.pdf",
        source="Poder Judicial de Puerto Rico", citation="2023 TSPR 83",
        snippet="[página 7] el foro a quo incurrió en error al condicionar la "
                "pensión alimentaria a la presentación del certificado de nacimiento.",
        relevance_score=14.9, verified=True,
    )
    assert server._document_relevance_confirmed(tangential, "pensión alimenticia") is True


def test_topical_search_with_no_real_matches_returns_empty_list(monkeypatch):
    import asyncio

    candidates = [
        server.Decision(
            title="2025 TSPR 1", url="https://dts.poderjudicial.pr/ts/2025/2025tspr1.pdf",
            source="Poder Judicial de Puerto Rico", citation="2025 TSPR 1", verified=True,
        )
    ]

    async def fake_get_year_links(year):
        return candidates

    async def fake_read_decision(decision, query):
        decision.relevance_score = 0.0
        decision.snippet = ""
        return decision

    monkeypatch.setattr(server, "get_year_links", fake_get_year_links)
    monkeypatch.setattr(server, "read_decision", fake_read_decision)

    results, meta = asyncio.run(server.content_search("xyzxyzqwertyinexistente12345", [2025], 5))
    assert results == []
    assert meta["pdfs_verificados"] == 1
    assert meta["anos_explorados"] == [2025]


def test_content_search_stops_early_once_enough_results_found(monkeypatch):
    """Regression test for the timeout fix: content_search must not keep
    indexing/reading years once it already has `limit` verified results."""
    import asyncio

    # One decision per year, every year "matches" strongly and cheaply.
    def year_candidates(year):
        return [
            server.Decision(
                title=f"{year} TSPR 1", url=f"https://dts.poderjudicial.pr/ts/{year}/{year}tspr1.pdf",
                source="Poder Judicial de Puerto Rico", citation=f"{year} TSPR 1", verified=True,
            )
        ]

    years_indexed: list[int] = []

    async def fake_get_year_links(year):
        years_indexed.append(year)
        return year_candidates(year)

    async def fake_read_decision(decision, query):
        decision.relevance_score = 10.0
        decision.snippet = "pensión alimenticia pensión alimenticia obligación alimentaria"
        decision.verified = True
        return decision

    monkeypatch.setattr(server, "get_year_links", fake_get_year_links)
    monkeypatch.setattr(server, "read_decision", fake_read_decision)

    many_years = list(range(2025, 1995, -1))  # 30 years available
    results, meta = asyncio.run(server.content_search("pensión alimenticia", many_years, 2))
    assert len(results) == 2
    # Must not have indexed anywhere near all 30 years once 2 results were found.
    assert len(years_indexed) < len(many_years)
    assert meta["anos_pendientes"]  # some years were legitimately left unexplored


def test_content_search_respects_total_pdf_budget_when_nothing_matches(monkeypatch):
    """When no candidate is ever relevant, the search must still stop at the
    documented PDF-read ceiling instead of grinding through every year."""
    import asyncio

    def year_candidates(year):
        return [
            server.Decision(
                title=f"{year} TSPR 1", url=f"https://dts.poderjudicial.pr/ts/{year}/{year}tspr1.pdf",
                source="Poder Judicial de Puerto Rico", citation=f"{year} TSPR 1", verified=True,
            )
        ]

    async def fake_get_year_links(year):
        return year_candidates(year)

    pdfs_opened = 0

    async def fake_read_decision(decision, query):
        nonlocal pdfs_opened
        pdfs_opened += 1
        decision.relevance_score = 0.0
        decision.snippet = ""
        return decision

    monkeypatch.setattr(server, "get_year_links", fake_get_year_links)
    monkeypatch.setattr(server, "read_decision", fake_read_decision)

    many_years = list(range(2025, 1995, -1))  # 30 years available
    results, meta = asyncio.run(server.content_search("consulta sin coincidencias", many_years, 5))
    assert results == []
    assert pdfs_opened <= server.MAX_TOTAL_PDF_READS
    assert meta["pdfs_verificados"] <= server.MAX_TOTAL_PDF_READS


def test_get_year_links_is_cached(monkeypatch):
    import asyncio

    server._year_index_cache.clear()
    calls = {"n": 0}

    async def fake_fetch_text(url):
        calls["n"] += 1
        return '<a href="https://dts.poderjudicial.pr/ts/2025/2025tspr1.pdf">2025 TSPR 1</a>'

    monkeypatch.setattr(server, "fetch_text", fake_fetch_text)
    asyncio.run(server.get_year_links(2025))
    asyncio.run(server.get_year_links(2025))
    assert calls["n"] == 1
    server._year_index_cache.clear()


def test_mcp_server_module_initializes():
    assert server.mcp.name == "puerto-rico-sentencias"
    assert callable(server.buscar_sentencias)
    assert callable(server.investigar_sentencias)
    assert callable(server.buscar_por_cita)
