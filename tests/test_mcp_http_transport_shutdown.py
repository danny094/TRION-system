def test_http_shutdown_is_idempotent_noop_and_does_not_reset(monkeypatch):
    from mcp.transports.http import HTTPTransport

    transport = HTTPTransport("http://example.invalid/mcp")
    transport._format = "streamable"
    transport._session_id = "sid"
    transport._format_detected = True
    monkeypatch.setattr(transport, "reset", lambda: (_ for _ in ()).throw(AssertionError("reset called")))

    transport.shutdown()
    transport.shutdown()

    assert transport._format == "streamable"
    assert transport._session_id == "sid"
    assert transport._format_detected is True
