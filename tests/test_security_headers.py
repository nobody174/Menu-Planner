"""
M8 + LO1 (audit 2026-07-07, PR 2026-07-08): security response headers and
the request body size cap had zero test coverage - a regression on either
(e.g. someone removing the after_request hook, or accidentally resetting
MAX_CONTENT_LENGTH) would have shipped silently.
"""


def test_security_headers_present_on_normal_response(client):
    resp = client.get("/login-page")
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_not_set_outside_production(client):
    resp = client.get("/login-page")
    assert "Strict-Transport-Security" not in resp.headers


def test_oversized_request_body_rejected(client):
    from deployment.flask_app import app

    max_len = app.config["MAX_CONTENT_LENGTH"]
    assert max_len is not None and max_len > 0

    oversized = b"x" * (max_len + 1)
    resp = client.post(
        "/login",
        data=oversized,
        content_type="application/x-www-form-urlencoded",
    )
    assert resp.status_code == 413
