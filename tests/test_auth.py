"""
Test authentication functionality.
"""

import pytest
from core.auth_helpers import (
    create_user, authenticate_user, is_valid_email, is_valid_password,
    verify_password, hash_password, confirm_email, regenerate_confirmation_token
)


class TestPasswordValidation:
    """Test password validation rules."""

    def test_valid_password(self):
        """Valid password should pass."""
        valid, msg = is_valid_password('Password123')
        assert valid
        assert msg == "OK"

    def test_password_too_short(self):
        """Password < 8 chars should fail."""
        valid, msg = is_valid_password('Pass12')
        assert not valid
        assert "8 characters" in msg

    def test_password_missing_uppercase(self):
        """Password without uppercase should fail."""
        valid, msg = is_valid_password('password123')
        assert not valid
        assert "uppercase" in msg

    def test_password_missing_lowercase(self):
        """Password without lowercase should fail."""
        valid, msg = is_valid_password('PASSWORD123')
        assert not valid
        assert "lowercase" in msg

    def test_password_missing_digit(self):
        """Password without digit should fail."""
        valid, msg = is_valid_password('Password')
        assert not valid
        assert "digit" in msg


class TestEmailValidation:
    """Test email validation."""

    def test_valid_email(self):
        """Valid email should pass."""
        assert is_valid_email('user@example.com')

    def test_invalid_email_no_at(self):
        """Email without @ should fail."""
        assert not is_valid_email('userexample.com')

    def test_invalid_email_no_domain(self):
        """Email without domain should fail."""
        assert not is_valid_email('user@')

    def test_invalid_email_no_tld(self):
        """Email without TLD should fail."""
        assert not is_valid_email('user@example')


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Password should be hashed."""
        password = 'TestPassword123'
        hashed = hash_password(password)

        # Hash should not be same as password
        assert hashed != password
        # Hash should contain hash algorithm identifier
        assert 'pbkdf2' in hashed

    def test_verify_password_correct(self):
        """Correct password should verify."""
        password = 'TestPassword123'
        hashed = hash_password(password)

        assert verify_password(hashed, password)

    def test_verify_password_incorrect(self):
        """Incorrect password should not verify."""
        password = 'TestPassword123'
        hashed = hash_password(password)

        assert not verify_password(hashed, 'WrongPassword123')


class TestUserCreation:
    """Test user creation."""

    def test_create_user_success(self):
        """User should be created with valid data."""
        success, user, user_id = create_user('test@example.com', 'TestPassword123')

        assert success
        assert user is not None
        assert user_id is not None
        assert user.email == 'test@example.com'

    def test_create_user_duplicate_email(self):
        """Duplicate email should fail."""
        create_user('test@example.com', 'TestPassword123')
        success, msg, _ = create_user('test@example.com', 'AnotherPass123')

        assert not success
        assert "already exists" in msg.lower()

    def test_create_user_invalid_email(self):
        """Invalid email should fail."""
        success, msg, _ = create_user('invalid-email', 'TestPassword123')

        assert not success
        assert "email" in msg.lower()

    def test_create_user_weak_password(self):
        """Weak password should fail."""
        success, msg, _ = create_user('test@example.com', 'weak')

        assert not success
        assert "password" in msg.lower()

    def test_create_user_email_normalized(self):
        """Email should be lowercased."""
        success, user, _ = create_user('Test@Example.COM', 'TestPassword123')

        assert success
        assert user.email == 'test@example.com'


class TestUserAuthentication:
    """Test user login. Login is blocked until the email is confirmed (see
    TestEmailConfirmation below), so every success-path test here must
    confirm the user first - this mirrors the real signup -> confirm -> login
    flow rather than the old signup -> login flow."""

    def test_authenticate_user_success(self):
        """Valid credentials should authenticate once confirmed."""
        email = 'test@example.com'
        password = 'TestPassword123'

        _, user, _ = create_user(email, password)
        confirm_email(user.email_confirmation_token)
        success, user = authenticate_user(email, password)

        assert success
        assert user is not None
        assert user.email == email

    def test_authenticate_user_unconfirmed_blocked(self):
        """Login should be blocked until the email is confirmed."""
        email = 'test@example.com'
        password = 'TestPassword123'

        create_user(email, password)
        success, msg = authenticate_user(email, password)

        assert not success
        assert msg == "EMAIL_NOT_CONFIRMED"

    def test_authenticate_user_wrong_password(self):
        """Wrong password should fail."""
        email = 'test@example.com'
        password = 'TestPassword123'

        _, user, _ = create_user(email, password)
        confirm_email(user.email_confirmation_token)
        success, msg = authenticate_user(email, 'WrongPassword123')

        assert not success
        assert "password" in msg.lower()

    def test_authenticate_user_not_found(self):
        """Non-existent user should fail."""
        success, msg = authenticate_user('notfound@example.com', 'AnyPassword123')

        assert not success
        assert "not found" in msg.lower()

    def test_authenticate_user_email_normalized(self):
        """Email should be case-insensitive for login."""
        email = 'test@example.com'
        password = 'TestPassword123'

        _, user, _ = create_user(email, password)
        confirm_email(user.email_confirmation_token)
        success, user = authenticate_user('TEST@EXAMPLE.COM', password)

        assert success
        assert user.email == email


class TestEmailConfirmation:
    """Test the email confirmation flow itself."""

    def test_new_user_has_unconfirmed_state(self):
        """A freshly created user should have a token and no confirmed timestamp."""
        _, user, _ = create_user('test@example.com', 'TestPassword123')

        assert user.email_confirmation_token is not None
        assert user.email_confirmed_at is None

    def test_confirm_email_success(self):
        """Confirming with the correct token should succeed and clear the token."""
        _, user, _ = create_user('test@example.com', 'TestPassword123')
        token = user.email_confirmation_token

        success, confirmed_user = confirm_email(token)

        assert success
        assert confirmed_user.email_confirmed_at is not None
        assert confirmed_user.email_confirmation_token is None

    def test_confirm_email_invalid_token(self):
        """An unknown token should fail clearly, not silently confirm anyone."""
        success, msg = confirm_email('not-a-real-token')

        assert not success
        assert "invalid" in msg.lower() or "expired" in msg.lower()

    def test_confirm_email_twice_is_harmless(self):
        """Clicking the confirmation link twice (e.g. double-click, email
        client prefetch) should not error - the second click is a no-op."""
        _, user, _ = create_user('test@example.com', 'TestPassword123')
        token = user.email_confirmation_token

        confirm_email(token)
        # Token is now cleared - simulate a second request with the same
        # link by looking up the user fresh and trying their (now-stale)
        # token again should fail safely, not crash.
        success, msg = confirm_email(token)

        assert not success  # token was already consumed

    def test_regenerate_confirmation_token_for_unconfirmed_user(self):
        """Resend-confirmation should issue a new, different token."""
        _, user, _ = create_user('test@example.com', 'TestPassword123')
        old_token = user.email_confirmation_token

        success, updated_user = regenerate_confirmation_token('test@example.com')

        assert success
        assert updated_user.email_confirmation_token is not None
        assert updated_user.email_confirmation_token != old_token

    def test_regenerate_confirmation_token_already_confirmed(self):
        """Resend should refuse once the email is already confirmed."""
        _, user, _ = create_user('test@example.com', 'TestPassword123')
        confirm_email(user.email_confirmation_token)

        success, msg = regenerate_confirmation_token('test@example.com')

        assert not success
        assert "already confirmed" in msg.lower()

    def test_regenerate_confirmation_token_unknown_user(self):
        """Resend for a non-existent email should fail clearly."""
        success, msg = regenerate_confirmation_token('notfound@example.com')

        assert not success
        assert "not found" in msg.lower()
