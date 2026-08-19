from __future__ import annotations

import research_server


def test_product_brand_and_source_hierarchy():
    status = research_server.estado_investigacion_juridica()
    assert status["producto"] == "MCP Puerto Rico — Investigación Jurídica"
    assert status["garantias"]["fuente_primaria_preferida"] is True
    assert status["garantias"]["fuente_secundaria_etiquetada"] is True


def test_catalog_marks_microjuris_as_secondary():
    catalog = research_server.catalogo_fuentes_juridicas()
    mj = catalog["fuentes_secundarias"]["microjuris_al_dia"]
    assert mj["nivel"] == "fuente_secundaria_publica"
    assert "primaria" in mj["regla"]


def test_appeals_parser_extracts_only_real_table_rows():
    html = """
    <table>
      <tr><th>NÚMERO CASO</th><th>PARTES</th><th>FECHA SENTENCIA</th></tr>
      <tr>
        <td>KLAN202400005</td>
        <td>IRIZARRY GUASCH, DAMIAN VS IRIZARRY GUASCH, WILMA IVONNE</td>
        <td>19 May 2026</td>
      </tr>
      <tr><td>texto</td><td>no es caso</td><td>hoy</td></tr>
    </table>
    """
    results = research_server._parse_appeals_month(
        html,
        "https://poderjudicial.pr/tribunal-apelaciones/decisiones-finales-del-tribunal-de-apelaciones/decisiones-del-tribunal-de-apelaciones-mayo-2026/",
        "Irizarry",
    )
    assert len(results) == 1
    assert results[0]["numero_caso"] == "KLAN202400005"
    assert results[0]["verificado"] is True
    assert results[0]["nivel_fuente"] == "fuente_primaria_oficial"


def test_research_host_allowlist_rejects_subscription_or_unknown_hosts():
    assert research_server._research_url_allowed("https://poderjudicial.pr/x")
    assert research_server._research_url_allowed("https://aldia.microjuris.com/x")
    assert not research_server._research_url_allowed("https://pr.microjuris.com/productos/buscador")
    assert not research_server._research_url_allowed("http://poderjudicial.pr/x")
    assert not research_server._research_url_allowed("https://example.com/x")


def test_public_search_results_require_query_signal():
    html = """
    <article><h2><a href="https://aldia.microjuris.com/2024/06/28/chevron/">Supremo federal anula doctrina de Chevron</a></h2></article>
    <article><h2><a href="https://aldia.microjuris.com/otra/">Tema sin relación</a></h2></article>
    """
    results = research_server._parse_public_search_results(
        html, "https://aldia.microjuris.com/", "Chevron", 10
    )
    assert len(results) == 1
    assert "Chevron" in results[0]["titulo"]
