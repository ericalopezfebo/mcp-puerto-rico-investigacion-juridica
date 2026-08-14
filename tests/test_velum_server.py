from pathlib import Path

import pytest

import velum


def test_unified_server_exposes_privacy_tools():
    tools = velum.mcp._tool_manager._tools
    assert {
        "listar_documentos_locales",
        "huella_documento_local",
        "preparar_documento_para_ia",
        "crear_copia_anonimizada",
        "estado_privacidad",
    }.issubset(tools)


def test_copy_anonymized_document_stays_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "demanda.txt"
    source.write_text("Cliente: Jane Doe\nEmail: jane@example.com", encoding="utf-8")
    monkeypatch.setenv("VELUM_DOCUMENT_ROOT", str(root))

    result = velum.crear_copia_anonimizada("demanda.txt", "sanitizado.txt", '{"Jane Doe":"[CLIENTE]"}')

    target = root / "sanitizado.txt"
    assert result["ok"] is True
    assert target.exists()
    assert "Jane Doe" not in target.read_text(encoding="utf-8")
    assert "jane@example.com" not in target.read_text(encoding="utf-8")
    assert source.read_text(encoding="utf-8") == "Cliente: Jane Doe\nEmail: jane@example.com"
    assert result["original_modificado"] is False
