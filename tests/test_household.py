"""
Test household and team management functionality.
"""

import pytest
from core.auth_helpers import create_user
from core.household_helpers import (
    create_household, get_household, get_user_households, get_household_members,
    add_household_member, remove_household_member, update_member_role,
    user_can_access_household, user_can_edit_household
)


@pytest.fixture
def test_users():
    """Create test users."""
    user1_success, user1, _ = create_user('owner@example.com', 'Owner12345')
    user2_success, user2, _ = create_user('member@example.com', 'Member12345')
    user3_success, user3, _ = create_user('viewer@example.com', 'Viewer12345')

    assert user1_success and user2_success and user3_success

    return {
        'owner': user1,
        'member': user2,
        'viewer': user3,
    }


class TestHouseholdCreation:
    """Test household creation."""

    def test_create_household_success(self, test_users):
        """Household should be created."""
        owner = test_users['owner']
        success, household, household_id = create_household(str(owner.id), 'My Family')

        assert success
        assert household is not None
        assert household_id is not None
        assert household.name == 'My Family'
        assert household.owner_id == owner.id

    def test_create_household_empty_name(self, test_users):
        """Empty name should fail."""
        owner = test_users['owner']
        success, msg, _ = create_household(str(owner.id), '')

        assert not success
        assert "name" in msg.lower()

    def test_create_household_adds_owner_as_member(self, test_users):
        """Creator should be added as owner member."""
        owner = test_users['owner']
        _, household, household_id = create_household(str(owner.id), 'My Family')

        members = get_household_members(household_id)
        assert len(members) == 1
        assert members[0]['user_id'] == str(owner.id)
        assert members[0]['role'] == 'owner'


class TestHouseholdAccess:
    """Test household access control."""

    def test_user_can_access_household_as_member(self, test_users):
        """Member should access household."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, member.email, 'viewer')

        assert user_can_access_household(str(member.id), household_id)

    def test_user_cannot_access_household_not_member(self, test_users):
        """Non-member should not access household."""
        owner = test_users['owner']
        viewer = test_users['viewer']

        _, household, household_id = create_household(str(owner.id), 'My Family')

        assert not user_can_access_household(str(viewer.id), household_id)

    def test_user_can_edit_as_owner(self, test_users):
        """Owner should edit household."""
        owner = test_users['owner']
        _, household, household_id = create_household(str(owner.id), 'My Family')

        assert user_can_edit_household(str(owner.id), household_id)

    def test_user_can_edit_as_editor(self, test_users):
        """Editor should edit household."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, member.email, 'editor')

        assert user_can_edit_household(str(member.id), household_id)

    def test_user_cannot_edit_as_viewer(self, test_users):
        """Viewer should not edit household."""
        owner = test_users['owner']
        viewer = test_users['viewer']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, viewer.email, 'viewer')

        assert not user_can_edit_household(str(viewer.id), household_id)


class TestHouseholdMembers:
    """Test household member management."""

    def test_add_household_member_success(self, test_users):
        """Member should be added."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        success, msg, member_id = add_household_member(
            household_id, member.email, 'editor'
        )

        assert success
        assert member_id is not None

        members = get_household_members(household_id)
        assert len(members) == 2  # owner + new member

    def test_add_household_member_duplicate(self, test_users):
        """Duplicate member should fail."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, member.email, 'viewer')

        success, msg, _ = add_household_member(household_id, member.email, 'editor')
        assert not success
        assert "already" in msg.lower()

    def test_add_household_member_not_found(self, test_users):
        """Non-existent user should fail."""
        owner = test_users['owner']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        success, msg, _ = add_household_member(
            household_id, 'notfound@example.com', 'viewer'
        )

        assert not success
        assert "not found" in msg.lower()

    def test_remove_household_member_success(self, test_users):
        """Member should be removed."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        _, _, member_id = add_household_member(household_id, member.email, 'viewer')

        success, msg = remove_household_member(household_id, member_id, str(owner.id))
        assert success

        members = get_household_members(household_id)
        assert len(members) == 1  # only owner left

    def test_remove_household_member_permission_denied(self, test_users):
        """Non-owner should not remove member."""
        owner = test_users['owner']
        member = test_users['member']
        viewer = test_users['viewer']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, member.email, 'editor')
        _, _, viewer_member_id = add_household_member(
            household_id, viewer.email, 'viewer'
        )

        # member (editor) tries to remove viewer
        success, msg = remove_household_member(
            household_id, viewer_member_id, str(member.id)
        )
        assert success  # editors can remove


class TestMemberRoles:
    """Test member role management."""

    def test_update_member_role_success(self, test_users):
        """Member role should be updated."""
        owner = test_users['owner']
        member = test_users['member']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        _, _, member_id = add_household_member(household_id, member.email, 'viewer')

        success, msg = update_member_role(
            household_id, member_id, 'editor', str(owner.id)
        )
        assert success

        members = get_household_members(household_id)
        member_role = next(m for m in members if m['member_id'] == member_id)
        assert member_role['role'] == 'editor'

    def test_update_member_role_permission_denied(self, test_users):
        """Non-owner should not change roles."""
        owner = test_users['owner']
        member = test_users['member']
        viewer = test_users['viewer']

        _, household, household_id = create_household(str(owner.id), 'My Family')
        add_household_member(household_id, member.email, 'editor')
        _, _, viewer_member_id = add_household_member(
            household_id, viewer.email, 'viewer'
        )

        # member (editor) tries to promote viewer to editor
        success, msg = update_member_role(
            household_id, viewer_member_id, 'editor', str(member.id)
        )
        assert not success
        assert "owner" in msg.lower()
