"""
Household and membership management helpers.
"""

from database.database import SessionLocal
from database.models import Household, HouseholdMember, User
import uuid


def create_household(user_id, household_name):
    """
    Create a new household owned by the user.
    Returns: (success, household_or_error_msg, household_id)
    """
    if not household_name or not household_name.strip():
        return False, "Household name required", None

    household_name = household_name.strip()[:255]

    session = SessionLocal()
    try:
        household = Household(
            name=household_name,
            owner_id=user_id
        )
        session.add(household)
        session.flush()

        # Add creator as owner member
        member = HouseholdMember(
            household_id=household.id,
            user_id=user_id,
            role='owner'
        )
        session.add(member)
        session.commit()

        household_id = str(household.id)
        return True, household, household_id

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}", None
    finally:
        session.close()


def get_household(household_id):
    """Get household by ID."""
    session = SessionLocal()
    try:
        household = session.query(Household).filter(Household.id == household_id).first()
        return household
    finally:
        session.close()


def get_user_households(user_id):
    """Get all households the user is a member of."""
    session = SessionLocal()
    try:
        members = session.query(HouseholdMember).filter(
            HouseholdMember.user_id == user_id
        ).all()

        household_ids = [m.household_id for m in members]
        if not household_ids:
            return []

        households = session.query(Household).filter(
            Household.id.in_(household_ids)
        ).all()

        return households
    finally:
        session.close()


def get_household_members(household_id):
    """Get all members and profiles of a household."""
    session = SessionLocal()
    try:
        members = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id
        ).all()

        result = []
        for member in members:
            if member.is_profile:
                result.append({
                    'member_id': str(member.id),
                    'user_id': None,
                    'is_profile': True,
                    'display_name': member.display_name,
                    'avatar_type': member.avatar_type,
                    'avatar_value': member.avatar_value,
                    'email': None,
                    'role': member.role,
                    'joined_at': member.joined_at.strftime('%b %d, %Y') if member.joined_at else None
                })
            else:
                user = session.query(User).filter(User.id == member.user_id).first()
                if user:
                    result.append({
                        'member_id': str(member.id),
                        'user_id': str(member.user_id),
                        'is_profile': False,
                        # Leave display_name as None when unset (rather than
                        # falling back to the email here) - the template
                        # already does `member.display_name or member.email`
                        # for the main label, and separately shows the email
                        # in parentheses only when a *real* display_name is
                        # set. Defaulting it to the email here made that
                        # parenthetical check always true, showing the same
                        # email twice: "user@example.com (user@example.com)".
                        'display_name': member.display_name,
                        'avatar_type': member.avatar_type,
                        'avatar_value': member.avatar_value,
                        'email': user.email,
                        'role': member.role,
                        'joined_at': member.joined_at.strftime('%b %d, %Y') if member.joined_at else None
                    })

        return result
    finally:
        session.close()


def create_profile(household_id, display_name, role='viewer', avatar_type=None, avatar_value=None):
    """
    Create a lightweight member profile (no email/password) under a household.
    'co-owner' grants the same rights as 'owner' (see acting_role_is_owner in
    flask_app.py) but without a separate login - for a spouse/partner who needs
    full control without a separate email-invite account.
    Returns: (success, message, member_id)
    """
    if role not in ('editor', 'viewer', 'co-owner'):
        return False, "Invalid role for profile", None

    if not display_name or not display_name.strip():
        return False, "Profile name required", None

    session = SessionLocal()
    try:
        member = HouseholdMember(
            household_id=household_id,
            user_id=None,
            role=role,
            is_profile=True,
            display_name=display_name.strip()[:100],
            avatar_type=avatar_type,
            avatar_value=avatar_value
        )
        session.add(member)
        session.commit()

        member_id = str(member.id)
        return True, f"Added profile {display_name}", member_id

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}", None
    finally:
        session.close()


def get_profiles(household_id):
    """Get all profiles (non-account members) for a household."""
    session = SessionLocal()
    try:
        members = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.is_profile == True
        ).all()
        return members
    finally:
        session.close()


def get_member_by_id(member_id, household_id):
    """Get a single household_member row by id, scoped to a household."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()
        return member
    finally:
        session.close()


def update_household(household_id, name=None):
    """Update household details (currently just the name)."""
    if name is not None and not name.strip():
        return False, "Household name cannot be empty"

    if name is None:
        return False, "No changes to update"

    session = SessionLocal()
    try:
        household = session.query(Household).filter(Household.id == household_id).first()
        if not household:
            return False, "Household not found"

        household.name = name.strip()[:255]

        session.commit()
        return True, household

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def delete_household(household_id, owner_id):
    """Delete household (owner only)."""
    session = SessionLocal()
    try:
        household = session.query(Household).filter(Household.id == household_id).first()
        if not household:
            return False, "Household not found"

        if household.owner_id != owner_id:
            return False, "Only owner can delete household"

        session.delete(household)
        session.commit()
        return True, "Household deleted"

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def add_household_member(household_id, email, role='viewer'):
    """
    Add a member to household by email.
    Returns: (success, message, member_id)
    """
    if role not in ('owner', 'editor', 'viewer'):
        return False, "Invalid role", None

    session = SessionLocal()
    try:
        # Find user by email
        user = session.query(User).filter(User.email == email.lower()).first()
        if not user:
            return False, "User not found", None

        # Check if already member
        existing = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user.id
        ).first()

        if existing:
            return False, "User is already a member", None

        # Add member
        member = HouseholdMember(
            household_id=household_id,
            user_id=user.id,
            role=role
        )
        session.add(member)
        session.commit()

        member_id = str(member.id)
        return True, f"Added {email} as {role}", member_id

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}", None
    finally:
        session.close()


def remove_household_member(household_id, member_id, remover_id):
    """
    Remove a member from household (owner/editor only).
    Returns: (success, message)
    """
    session = SessionLocal()
    try:
        # Check remover is owner/editor
        remover_member = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == remover_id
        ).first()

        if not remover_member or remover_member.role not in ('owner', 'editor'):
            return False, "Permission denied"

        # Get member to remove
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()

        if not member:
            return False, "Member not found"

        # Can't remove owner (must transfer first)
        if member.role == 'owner':
            return False, "Cannot remove owner. Transfer ownership first."

        session.delete(member)
        session.commit()

        return True, "Member removed"

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def update_member_role(household_id, member_id, new_role, updater_id):
    """
    Update member role (owner only). Profiles may be set to editor/viewer/co-owner
    (same roles [[create_profile]] allows at creation time) but never 'owner' -
    that role is reserved for the actual account holder, since a profile has no
    login of its own. Account-holder members may be set to owner/editor/viewer
    (an account-holder is never a 'profile', so 'co-owner' doesn't apply to them -
    that distinction exists specifically for profiles without their own login).
    Returns: (success, message)
    """
    session = SessionLocal()
    try:
        # Check updater is owner
        updater = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == updater_id
        ).first()

        if not updater or updater.role != 'owner':
            return False, "Only owner can change roles"

        # Get member to update
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()

        if not member:
            return False, "Member not found"

        allowed_roles = ('editor', 'viewer', 'co-owner') if member.is_profile else ('owner', 'editor', 'viewer')
        if new_role not in allowed_roles:
            return False, "Invalid role"

        member.role = new_role
        session.commit()

        return True, f"Updated role to {new_role}"

    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def user_can_access_household(user_id, household_id):
    """Check if user is member of household."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        ).first()
        return member is not None
    finally:
        session.close()


def user_can_edit_household(user_id, household_id):
    """Check if user can edit household (owner or editor)."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        ).first()

        if not member:
            return False

        return member.role in ('owner', 'editor')
    finally:
        session.close()


def get_account_holder_role(user_id, household_id):
    """Look up the role of the account-holder's own HouseholdMember row
    (not a profile) - the account equivalent of [[get_profile_role]]."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        ).first()
        return member.role if member else None
    finally:
        session.close()


def user_is_household_owner(user_id, household_id):
    """Check if the ACCOUNT is the owner of the household. Does not account for an
    active profile - use [[acting_role_is_owner]] for permission checks, since a
    profile (e.g. 'Wife') can be active under the owner's account but should not
    inherit owner privileges."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        ).first()

        if not member:
            return False

        return member.role == 'owner'
    finally:
        session.close()


def set_member_avatar(member_id, household_id, emoji):
    """Set a member's emoji avatar (works for both profiles and the account row)."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()

        if not member:
            return False, "Member not found"

        member.avatar_type = 'emoji'
        member.avatar_value = emoji
        session.commit()
        return True, "Avatar updated"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def rename_member(member_id, household_id, new_name):
    """Rename a household member's display name. Works for both profiles
    (e.g. 'Wife') and the owner's own account row (overrides the email-based
    display fallback). Owner-only, enforced by the caller."""
    new_name = (new_name or '').strip()[:100]
    if not new_name:
        return False, "Name required"

    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()

        if not member:
            return False, "Member not found"

        member.display_name = new_name
        session.commit()
        return True, "Renamed"
    except Exception as e:
        session.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        session.close()


def get_profile_role(member_id, household_id):
    """Look up the role of a specific profile (HouseholdMember row) by id."""
    session = SessionLocal()
    try:
        member = session.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household_id
        ).first()
        return member.role if member else None
    finally:
        session.close()
