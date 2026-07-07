"""
M5 (audit 2026-07-07): every error path (404, 500, CSRF failure) used to
render the same full HTML error page regardless of whether the caller was a
browser navigation or a fetch()-based JSON API client - this is exactly why
B63's frontend error handling had to special-case "the server sent back
HTML, not JSON" instead of reading a real error message. These tests confirm
/api/* paths now get a JSON body on every error path, while normal page
routes are unaffected.
"""

import pytest


def test_api_404_returns_json(client):
    resp = client.get("/api/this-route-does-not-exist")
    assert resp.status_code == 404
    assert resp.content_type.startswith("application/json")
    data = resp.get_json()
    assert data["success"] is False


def test_page_404_returns_html(client):
    resp = client.get("/this-page-does-not-exist")
    assert resp.status_code == 404
    assert resp.content_type.startswith("text/html")


def test_api_500_returns_json(client, monkeypatch):
    from deployment import flask_app

    def _boom():
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(flask_app, "load_menu", _boom)
    # Flask's TESTING=True (set by the test_app fixture) re-raises exceptions
    # instead of invoking the registered error handler, so this test would
    # never actually exercise the handler under test without disabling that.
    flask_app.app.config["TESTING"] = False
    try:
        resp = client.get("/api/menu")
    finally:
        flask_app.app.config["TESTING"] = True
    assert resp.status_code == 500
    assert resp.content_type.startswith("application/json")
    data = resp.get_json()
    assert data["success"] is False


def test_page_500_returns_html(client, monkeypatch):
    from deployment import flask_app

    def _boom():
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(flask_app, "load_menu", _boom)

    with client.session_transaction() as sess:
        sess["user_id"] = "fake-user-id"

    flask_app.app.config["TESTING"] = False
    try:
        resp = client.get("/")
    finally:
        flask_app.app.config["TESTING"] = True
    assert resp.status_code == 500
    assert resp.content_type.startswith("text/html")


def test_api_csrf_failure_returns_json(client):
    from deployment import flask_app

    flask_app.app.config["WTF_CSRF_ENABLED"] = True
    try:
        resp = client.post("/api/pantry/add", json={"item": "salt"})
        assert resp.status_code == 400
        assert resp.content_type.startswith("application/json")
        data = resp.get_json()
        assert data["success"] is False
    finally:
        flask_app.app.config["WTF_CSRF_ENABLED"] = False


def test_page_csrf_failure_returns_html(client):
    from deployment import flask_app

    flask_app.app.config["WTF_CSRF_ENABLED"] = True
    try:
        resp = client.post("/login", data={"email": "x@example.com", "password": "x"})
        assert resp.status_code == 400
        assert resp.content_type.startswith("text/html")
    finally:
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
