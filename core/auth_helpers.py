"""
Authentication helpers for email/password and session management.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from database.database import SessionLocal
from database.models import User
import re
import secrets
import string


def is_valid_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_password(password):
    """
    Validate password strength.
    Requirements: min 8 chars, at least one uppercase, one lowercase, one digit.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, "OK"


def hash_password(password):
    """Hash a password using werkzeug."""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """Verify a password against its hash."""
    return check_password_hash(password_hash, password)


def get_user_by_email(email):
    """Retrieve user by email from database."""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email.lower()).first()
        return user
    finally:
        session.close()


def _generate_referral_code(session):
    """8-char uppercase alphanumeric code, unique among existing users."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        if not session.query(User).filter(User.referral_code == code).first():
            return code


def _generate_confirmation_token():
    """URL-safe random token for email confirmation links - unguessable,
    no need to check uniqueness (collision odds are astronomically low and
    the token is only ever looked up by exact match, never enumerated)."""
    return secrets.token_urlsafe(32)


def get_user_by_referral_code(code):
    """Look up a user by their referral code (for linking new signups)."""
    if not code:
        return None
    session = SessionLocal()
    try:
        return session.query(User).filter(User.referral_code == code.strip().upper()).first()
    finally:
        session.close()


def create_user(email, password, referred_by_code=None):
    """
    Create a new user in the database.
    referred_by_code: optional referral code of the user who referred this signup.
    Attribution only - no reward logic exists yet.
    Returns: (success, user_or_error_msg, user_id)
    """
    email = email.lower().strip()

    # Validate email
    if not is_valid_email(email):
        return False, "Invalid email format", None

    # Validate password
    valid, msg = is_valid_password(password)
    if not valid:
        return False, msg, None

    # Check if user already exists
    if get_user_by_email(email):
        return False, "User already exists", None

    # Create user
    session = SessionLocal()
    try:
        password_hash = hash_password(password)
        referral_code = _generate_referral_code(session)

        referred_by_user_id = None
        referred_by_code_clean = None
        if referred_by_code:
            referrer = session.query(User).filter(User.referral_code == referred_by_code.strip().upper()).first()
            if referrer:
                referred_by_user_id = referrer.id
                referred_by_code_clean = referrer.referral_code

        user = User(
            email=email,
            password_hash=password_hash,
            referral_code=referral_code,
            referred_by_user_id=referred_by_user_id,
            referred_by_code=referred_by_code_clean,
            email_confirmation_token=_generate_confirmation_token()
        )
        session.add(user)
        session.commit()
        user_id = str(user.id)
        return True, user, user_id
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}", None
    finally:
        session.close()


def authenticate_user(email, password):
    """
    Authenticate user by email and password.
    Returns: (success, user_or_error_msg)
    Login is blocked until the email is confirmed (email_confirmed_at set) -
    this is a deliberate choice, not an oversight: it's the only way to
    actually verify a real, reachable address rather than just trusting
    whatever format-valid string was typed at signup, which matters here
    because anyone could otherwise sign up with a fake/bot-generated address
    and get full app access immediately.
    """
    email = email.lower().strip()
    user = get_user_by_email(email)

    if not user:
        return False, "User not found"

    if not verify_password(user.password_hash, password):
        return False, "Invalid password"

    if not user.email_confirmed_at:
        return False, "EMAIL_NOT_CONFIRMED"

    return True, user


def confirm_email(token):
    """Mark a user's email as confirmed via their confirmation token.
    Returns: (success, user_or_error_msg)."""
    if not token:
        return False, "Missing confirmation token"

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email_confirmation_token == token).first()
        if not user:
            return False, "Invalid or expired confirmation link"

        if user.email_confirmed_at:
            return True, user  # already confirmed - clicking the link twice is harmless

        from datetime import datetime
        user.email_confirmed_at = datetime.utcnow()
        user.email_confirmation_token = None  # one-time use, prevents replay
        session.commit()
        session.refresh(user)
        return True, user
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def regenerate_confirmation_token(email):
    """Issue a fresh confirmation token for a "resend confirmation email"
    flow - needed because the original token may have landed in spam or
    the email was mistyped at signup time. Returns: (success, user_or_error_msg)."""
    email = email.lower().strip()
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return False, "User not found"

        if user.email_confirmed_at:
            return False, "Email already confirmed"

        user.email_confirmation_token = _generate_confirmation_token()
        session.commit()
        session.refresh(user)
        return True, user
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def request_password_reset(email):
    """Generate a password reset token. Always returns True even if email not
    found — never reveals whether an account exists (prevents enumeration)."""
    from datetime import datetime
    email = email.lower().strip()
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return True, None
        user.password_reset_token = _generate_confirmation_token()
        user.password_reset_requested_at = datetime.utcnow()
        session.commit()
        session.refresh(user)
        return True, user
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def reset_password(token, new_password):
    """Reset password via a valid token. Tokens expire after 1 hour."""
    from datetime import datetime, timedelta
    if not token:
        return False, "Missing reset token"
    valid, msg = is_valid_password(new_password)
    if not valid:
        return False, msg
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.password_reset_token == token).first()
        if not user:
            return False, "Invalid or expired reset link"
        if user.password_reset_requested_at:
            age = datetime.utcnow() - user.password_reset_requested_at
            if age > timedelta(hours=1):
                return False, "Reset link has expired — please request a new one"
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_requested_at = None
        session.commit()
        return True, "Password updated successfully"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def delete_user_account(user_id):
    """Delete a user and all their data. Handles FK constraints in correct order."""
    session = SessionLocal()
    try:
        from database.models import Household, HouseholdMember
        owned_ids = [
            h.id for h in session.query(Household).filter(Household.owner_id == user_id).all()
        ]
        for hid in owned_ids:
            session.query(HouseholdMember).filter(HouseholdMember.household_id == hid).delete()
        session.query(HouseholdMember).filter(HouseholdMember.user_id == user_id).delete()
        session.query(Household).filter(Household.owner_id == user_id).delete()
        session.query(User).filter(User.id == user_id).delete()
        session.commit()
        return True, "Account deleted"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def set_pin(user_id, pin):
    """Set or change the account's shared-device PIN. 4 digits only, hashed
    the same way as the account password - never stored in clear text even
    though it's short. Returns: (success, message)."""
    if not pin or not pin.isdigit() or len(pin) != 4:
        return False, "PIN must be exactly 4 digits"

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        user.pin_hash = hash_password(pin)
        session.commit()
        return True, "PIN updated"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def clear_pin(user_id):
    """Remove the account's PIN, falling back to requiring the full password again."""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        user.pin_hash = None
        session.commit()
        return True, "PIN removed"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def verify_pin(user_id, pin):
    """Check a PIN against the account's stored pin_hash. Returns False if no
    PIN has ever been set (caller should fall back to full-password auth)."""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user or not user.pin_hash:
            return False
        return verify_password(user.pin_hash, pin)
    finally:
        session.close()
