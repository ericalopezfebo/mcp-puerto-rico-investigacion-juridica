from pathlib import Path

import pytest

from mcp_server.local_privacy import (
    anonymize_document,
    document_fingerprint,
    redact_text,
)


def test_redaction_removes_common_identifiers():
    text = "Correo: jane@example.com Tel: 787-555-1234 SSN: 123-45-6789"
    sanitized, counts = redact_text(text, {})
    assert "jane@example.com" not in sanitized
    assert "787-555-1234" not in sanitized
    assert "123-45-6789" not in sanitized
    assert counts["email"] == 1
    assert counts["telefono"] == 1
    assert counts["ssn"] == 1


def test_custom_redaction_is_deterministic():
    sanitized, counts = redact_text("Cliente: Jane Doe", {"Jane Doe": "[CLIENTE]"})
    assert sanitized == "Cliente: [CLIENTE]"
    assert counts["personalizado"] == 1


def test_anonymize_returns_only_sanitized_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "contrato.txt"
    source.write_text("Cliente: Jane Doe\nCorreo: jane@example.com", encoding="utf-8")
    monkeypatch.setenv("VELUM_DOCUMENT_ROOT", str(root))

    result = anonymize_document("contrato.txt", '{"Jane Doe": "[CLIENTE]"}')
    assert result["ok"] is True
    assert "Jane Doe" not in result["texto_preparado_para_ia"]
    assert "jane@example.com" not in result["texto_preparado_para_ia"]
    assert "[CLIENTE]" in result["texto_preparado_para_ia"]
    assert result["original_devuelto"] is False


def test_path_outside_root_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "docs"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setenv("VELUM_DOCUMENT_ROOT", str(root))

    with pytest.raises(ValueError):
        document_fingerprint(str(outside))
