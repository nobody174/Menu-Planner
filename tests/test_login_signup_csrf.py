"""
B59 (audit 2026-07-07): login and signup had zero test coverage, and CSRF
protection itself was never exercised anywhere in the test suite -
conftest.py's test_app fixture disables it for every test
(WTF_CSRF_ENABLED = False), so a CSRF regression on these routes could ship
without a single test catching it. These tests explicitly re-enable CSRF and
drive the real two-step flow (GET the page to get a real token, then POST
with it) end to end, plus confirm a request WITHOUT a valid token is
correctly rejected.
"""

import re
import pytest
from core.auth_helpers import create_user, confirm_email


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no csrf_token input found in rendered page"
    return match.group(1)


@pytest.fixture
def csrf_enabled_client(client):
    from deployment import flask_app

    flask_app.app.config["WTF_CSRF_ENABLED"] = True
    yield client
    flask_app.app.config["WTF_CSRF_ENABLED"] = False


class TestSignupFlow:
    def test_signup_with_valid_csrf_token_succeeds(self, csrf_enabled_client):
        page = csrf_enabled_client.get("/signup")
        token = _extract_csrf_token(page.get_data(as_text=True))

        resp = csrf_enabled_client.post(
            "/signup",
            data={
                "email": "new-signup@example.com",
                "password": "NewSignup123",
                "password_confirm": "NewSignup123",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "confirmation link" in resp.get_data(as_text=True).lower()

        from core.auth_helpers import get_user_by_email

        created = get_user_by_email("new-signup@example.com")
        assert created is not None
        assert created.email_confirmed_at is None

    def test_signup_without_csrf_token_rejected(self, csrf_enabled_client):
        resp = csrf_enabled_client.post(
            "/signup",
            data={
                "email": "no-token@example.com",
                "password": "NewSignup123",
                "password_confirm": "NewSignup123",
            },
        )
        assert resp.status_code == 400

    def test_signup_password_mismatch_rejected(self, csrf_enabled_client):
        page = csrf_enabled_client.get("/signup")
        token = _extract_csrf_token(page.get_data(as_text=True))

        resp = csrf_enabled_client.post(
            "/signup",
            data={
                "email": "mismatch@example.com",
                "password": "PasswordOne123",
                "password_confirm": "PasswordTwo123",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 400
        assert "do not match" in resp.get_data(as_text=True).lower()


class TestLoginFlow:
    def test_login_with_valid_credentials_and_csrf_redirects(self, csrf_enabled_client):
        _, user, _ = create_user("login-flow@example.com", "LoginFlow123")
        confirm_email(user.raw_confirmation_token)

        page = csrf_enabled_client.get("/login-page")
        token = _extract_csrf_token(page.get_data(as_text=True))

        resp = csrf_enabled_client.post(
            "/login",
            data={
                "email": "login-flow@example.com",
                "password": "LoginFlow123",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 302
        assert "/profile-picker" in resp.headers["Location"]

        with csrf_enabled_client.session_transaction() as sess:
            assert sess["user_id"] == str(user.id)

    def test_login_without_csrf_token_rejected(self, csrf_enabled_client):
        _, user, _ = create_user("login-no-csrf@example.com", "LoginFlow123")
        confirm_email(user.raw_confirmation_token)

        resp = csrf_enabled_client.post(
            "/login",
            data={"email": "login-no-csrf@example.com", "password": "LoginFlow123"},
        )
        assert resp.status_code == 400

    def test_login_unconfirmed_email_blocked(self, csrf_enabled_client):
        create_user("unconfirmed@example.com", "LoginFlow123")

        page = csrf_enabled_client.get("/login-page")
        token = _extract_csrf_token(page.get_data(as_text=True))

        resp = csrf_enabled_client.post(
            "/login",
            data={
                "email": "unconfirmed@example.com",
                "password": "LoginFlow123",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 401
        assert "confirm your email" in resp.get_data(as_text=True).lower()

    def test_login_wrong_password_rejected_generically(self, csrf_enabled_client):
        """M7: the error message must not distinguish "wrong password" from
        "no such account" - see core/auth_helpers.py's authenticate_user()."""
        _, user, _ = create_user("wrong-pw@example.com", "LoginFlow123")
        confirm_email(user.raw_confirmation_token)

        page = csrf_enabled_client.get("/login-page")
        token = _extract_csrf_token(page.get_data(as_text=True))

        resp = csrf_enabled_client.post(
            "/login",
            data={
                "email": "wrong-pw@example.com",
                "password": "TotallyWrongPassword123",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 401
        assert "invalid email or password" in resp.get_data(as_text=True).lower()

    def test_rate_limit_kicks_in_after_repeated_attempts(self, csrf_enabled_client):
        """H2: /login is limited to 10/minute. The 11th attempt in the same
        window must be rejected with 429, regardless of credentials."""
        page = csrf_enabled_client.get("/login-page")
        token = _extract_csrf_token(page.get_data(as_text=True))

        last_status = None
        for _ in range(11):
            resp = csrf_enabled_client.post(
                "/login",
                data={
                    "email": "rate-limit-test@example.com",
                    "password": "WrongPassword123",
                    "csrf_token": token,
                },
            )
            last_status = resp.status_code
        assert last_status == 429
