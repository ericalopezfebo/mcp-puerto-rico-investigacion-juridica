import asyncio

import vigencia_server


def test_parse_sutra_explicit_amendment_signal():
    html = """
    <html><body>
      <h2>Enmienda(s)</h2>
      <p>Enmienda Ley 55-2020</p>
      <p>Enmienda artículo 1343</p>
    </body></html>
    """
    result = vigencia_server.parse_sutra_amendment_page(html, "Ley 55-2020", "artículo 1343")
    assert result["total_senales"] >= 1
    assert result["puede_afirmarse_vigente"] is False
    assert result["estado_vigencia"] == "no_determinado_por_esta_pagina"


def test_parse_sutra_derogation_signal_does_not_overclaim_currency():
    html = """
    <html><body>
      <h2>Enmienda(s)</h2>
      <p>Enmienda Ley 129-2020</p>
      <p>Derogan artículos 68 y 69.</p>
    </body></html>
    """
    result = vigencia_server.parse_sutra_amendment_page(html, "Ley 129-2020")
    kinds = {item["tipo"] for item in result["senales_explicitas"]}
    assert "deroga" in kinds or "enmienda" in kinds
    assert result["puede_afirmarse_vigente"] is False


def test_secondary_source_cannot_verify_currency():
    result = asyncio.run(
        vigencia_server.verificar_vigencia_legislativa(
            "Ley 80-1976",
            "https://www.codexpr.ai/ley/1976-80",
            "Artículo 2",
        )
    )
    assert result["estado_vigencia"] == "no_determinada"
    assert result["puede_afirmarse_vigente"] is False
    assert "fuente oficial" in result["error"].lower()


def test_policy_defaults_to_undetermined():
    policy = vigencia_server.politica_vigencia_fuentes()
    assert policy["estado_por_defecto"] == "no_determinada"
    assert "SUTRA / Oficina de Servicios Legislativos" in policy["fuentes_oficiales_preferidas"]
    assert "CodeXPR" in policy["fuentes_secundarias_descubrimiento"]
