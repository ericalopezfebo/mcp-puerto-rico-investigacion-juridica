import pytest
from starlette.testclient import TestClient

import remote_server


def test_bearer_token_validation():
    assert remote_server._authorized("Bearer office-secret", "office-secret")
    assert not remote_server._authorized("Bearer wrong", "office-secret")
    assert not remote_server._authorized("Basic office-secret", "office-secret")
    assert not remote_server._authorized(None, "office-secret")


def test_remote_app_requires_api_key(monkeypatch):
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    monkeypatch.delenv("MCP_ALLOW_INSECURE", raising=False)
    with pytest.raises(RuntimeError, match="MCP_API_KEY is required"):
        remote_server.create_remote_app()


def test_health_is_public_but_mcp_requires_bearer(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "office-secret")
    with TestClient(remote_server.create_remote_app()) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/mcp")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
