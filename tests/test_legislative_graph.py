import legislative_graph


def test_parse_law_id_common_formats():
    assert legislative_graph.parse_law_id("Ley 80-1976").canonical == "Ley 80-1976"
    assert legislative_graph.parse_law_id("Ley Núm. 55-2020").canonical == "Ley 55-2020"


def test_parse_sutra_detail_extracts_amendment_edge():
    html = """
    <html><body>
      <h1>Ley 122-2026</h1>
      <div>Título: Para enmendar el Artículo 1343 de la Ley Núm. 55-2020, según enmendada.</div>
      <h2>Enmienda(s)</h2>
      <p>Enmienda Ley 55-2020</p>
      <p>Enmienda artículo 1343</p>
    </body></html>
    """
    target = legislative_graph.parse_law_id("Ley 55-2020")
    parsed = legislative_graph.parse_sutra_law_detail(
        html,
        "https://sutra.oslpr.org/prontuarios/leyes-aprobadas/160207",
        target,
    )
    assert parsed["law"] == "Ley 122-2026"
    assert parsed["mentions_target"] is True
    assert any(r["relation"] == "enmienda" for r in parsed["relations"])


def test_parse_sutra_detail_extracts_repeal_edge():
    html = """
    <html><body>
      <h1>Ley 74-2025</h1>
      <div>Título: Para derogar la Ley Núm. 63-1986 por ser obsoleta.</div>
      <h2>Enmienda(s)</h2>
      <p>Deroga Ley 63-1986</p>
      <p>Se deroga la Ley 63-1986.</p>
    </body></html>
    """
    target = legislative_graph.parse_law_id("Ley 63-1986")
    parsed = legislative_graph.parse_sutra_law_detail(
        html,
        "https://sutra.oslpr.org/prontuarios/leyes-aprobadas/999",
        target,
    )
    assert any(r["relation"] == "deroga" for r in parsed["relations"])


def test_summary_never_equates_silence_with_currency():
    target = legislative_graph.parse_law_id("Ley 80-1976")
    result = legislative_graph.summarize_graph(target, [])
    assert result["estado_vigencia"] == "no_determinada"
    assert result["puede_afirmarse_vigente"] is False
    assert result["derogacion_explicita_detectada"] is False


def test_summary_reports_explicit_repeal():
    target = legislative_graph.parse_law_id("Ley 63-1986")
    edge = legislative_graph.LegislativeEdge(
        source_law="Ley 74-2025",
        target_law="Ley 63-1986",
        relation="deroga",
        provision="",
        title="Para derogar la Ley 63-1986",
        url="https://sutra.oslpr.org/prontuarios/leyes-aprobadas/999",
    )
    result = legislative_graph.summarize_graph(target, [edge])
    assert result["estado_vigencia"] == "derogacion_detectada_en_fuente_oficial"
    assert result["derogacion_explicita_detectada"] is True
    assert result["puede_afirmarse_vigente"] is False


def test_article_filter_limits_unrelated_amendments():
    target = legislative_graph.parse_law_id("Ley 55-2020")
    edges = [
        legislative_graph.LegislativeEdge(
            source_law="Ley 122-2026",
            target_law=target.canonical,
            relation="enmienda",
            provision="Enmienda artículo 1343",
            title="",
            url="https://sutra.oslpr.org/prontuarios/leyes-aprobadas/1",
        ),
        legislative_graph.LegislativeEdge(
            source_law="Ley 123-2026",
            target_law=target.canonical,
            relation="enmienda",
            provision="Enmienda artículo 1500",
            title="",
            url="https://sutra.oslpr.org/prontuarios/leyes-aprobadas/2",
        ),
    ]
    result = legislative_graph.summarize_graph(target, edges, "Artículo 1343")
    assert len(result["afectaciones"]) == 1
    assert result["afectaciones"][0]["source_law"] == "Ley 122-2026"
