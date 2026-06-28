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
            referred_by_code=referred_by_code_clean
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
    """
    email = email.lower().strip()
    user = get_user_by_email(email)

    if not user:
        return False, "User not found"

    if not verify_password(user.password_hash, password):
        return False, "Invalid password"

    return True, user
