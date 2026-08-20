"""Network-free tests for the remote MCP entrypoint configuration."""

import remote_server


def test_remote_configuration_uses_render_hostname(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "example.onrender.com")
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
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


def test_remote_configuration_accepts_railway_hostname(monkeypatch):
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "example-production.up.railway.app")
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)

    remote_server._configure_remote_server()

    security = remote_server.mcp.settings.transport_security
    assert security is not None
    assert "example-production.up.railway.app" in security.allowed_hosts
    assert "example-production.up.railway.app:*" in security.allowed_hosts
    assert "https://example-production.up.railway.app" in security.allowed_origins
    assert remote_server.RAILWAY_PRODUCTION_HOST in security.allowed_hosts


def test_remote_configuration_preserves_custom_hosts(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.com,mcp.example.com:*")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://chat.example.com")
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)

    remote_server._configure_remote_server()

    security = remote_server.mcp.settings.transport_security
    assert security is not None
    assert "mcp.example.com" in security.allowed_hosts
    assert "mcp.example.com:*" in security.allowed_hosts
    assert "https://chat.example.com" in security.allowed_origins
    # Production and local hosts are additive rather than replacing explicit
    # configuration, so deployments remain portable and secure by default.
    assert remote_server.RAILWAY_PRODUCTION_HOST in security.allowed_hosts
    assert "localhost" in security.allowed_hosts
