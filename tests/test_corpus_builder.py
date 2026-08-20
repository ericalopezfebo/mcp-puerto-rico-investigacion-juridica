import corpus_builder


def test_concept_hits_classifies_jurisdiccion_primaria():
    text = (
        "La jurisdicción primaria concurrente presupone que el foro judicial y el foro "
        "administrativo tienen jurisdicción, y puede requerir la pericia administrativa."
    )
    hits = corpus_builder._concept_hits(text)
    names = [name for name, _area, _count in hits]
    assert "jurisdiccion_primaria" in names


def test_search_text_samples_across_document_and_is_bounded():
    paragraphs = [f"[página {i}] párrafo jurídico número {i} con suficiente contenido para indexación local." for i in range(1, 80)]
    value = corpus_builder._search_text(paragraphs)
    assert "número 1" in value
    assert "número 40" in value or "número 41" in value
    assert len(value) <= corpus_builder.MAX_SEARCH_TEXT_CHARS


def test_merge_records_is_idempotent_and_preserves_old_excerpt():
    old = [{
        "citation": "2012 TSPR 66",
        "year": 2012,
        "url": "https://dts.poderjudicial.pr/ts/2012/2012tspr66.pdf",
        "excerpt": "pasaje oficial previamente capturado",
        "page": 12,
        "search_text": "texto viejo",
    }]
    fresh = [{
        "citation": "2012 TSPR 66",
        "year": 2012,
        "url": "https://dts.poderjudicial.pr/ts/2012/2012tspr66.pdf",
        "excerpt": "",
        "search_text": "texto de búsqueda actualizado",
        "captured_at": "2026-08-20",
    }]
    once = corpus_builder.merge_records(old, fresh)
    twice = corpus_builder.merge_records(once, fresh)
    assert len(once) == 1
    assert len(twice) == 1
    assert once[0]["excerpt"] == "pasaje oficial previamente capturado"
    assert once[0]["page"] == 12
    assert once[0]["search_text"] == "texto de búsqueda actualizado"


def test_citation_graph_excludes_own_citation_and_deduplicates():
    text = "2012 TSPR 66 cita 2011 TSPR 79 y nuevamente 2011 TSPR 79; también 1999 TSPR 10."
    values = corpus_builder._all_tspr_citations(text, "2012 TSPR 66")
    assert values == ["2011 TSPR 79", "1999 TSPR 10"]
