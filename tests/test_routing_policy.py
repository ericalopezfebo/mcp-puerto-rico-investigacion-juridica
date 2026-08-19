from __future__ import annotations

import mixed_server
import smart_server


def test_server_instructions_route_top_n_to_relevance_first_tool():
    instructions = getattr(getattr(mixed_server.mcp, "_mcp_server", None), "instructions", "") or ""
    low = instructions.lower()
    assert "buscar_mejores_sentencias" in instructions
    assert "las mejores" in low
    assert "más relevantes" in low or "mas relevantes" in low
    assert "top n" in low
    assert "sin bono por recencia" in low
    assert "investigar_sentencias" in instructions
    assert "buscar_sentencias" in instructions


def test_tool_description_itself_contains_routing_signal():
    doc = smart_server.buscar_mejores_sentencias.__doc__ or ""
    low = doc.lower()
    assert "usa esta herramienta" in low
    assert "las mejores" in low
    assert "top n" in low
    assert "no busca año por año" in low
