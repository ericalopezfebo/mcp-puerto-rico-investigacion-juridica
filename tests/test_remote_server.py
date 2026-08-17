"""Network-free tests for the remote MCP entrypoint configuration."""

import remote_server


def test_remote_configuration_uses_render_hostname(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "example.onrender.com")
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)

    remote_server._configure_remote_server()

    assert remote_server.mcp.settings.host == "0.0.0.0"
    assert remote_server.mcp.settings.port == 10000
    assert remote_server.mcp.settings.streamable_http_path == "/mcp"
    security = remote_server.mcp.settings.transport_security
    assert security is not None
    assert "example.onrender.com" in security.allowed_hosts
    assert "https://example.onrender.com" in security.allowed_origins
    assert security.enable_dns_rebinding_protection is True


def test_remote_configuration_accepts_custom_hosts(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.com,mcp.example.com:*")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://chat.example.com")
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)

    remote_server._configure_remote_server()

    security = remote_server.mcp.settings.transport_security
    assert security is not None
    assert security.allowed_hosts == ["mcp.example.com", "mcp.example.com:*"]
    assert security.allowed_origins == ["https://chat.example.com"]
