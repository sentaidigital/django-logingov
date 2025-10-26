"""
Unit tests for the Login.gov Service Provider user UUID functionality.

This file contains unit tests for the find_user_by_uuid method in the LoginGovSP class.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.crypto import get_random_string

# Import the classes we're testing
from logingov.utils import LoginGovSP
from logingov.models import UserUUID

class UserUUIDTestCase(TestCase):
    """
    Test cases for user UUID lookup in the LoginGovSP class.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='admin@example.com',
            password=get_random_string(12)
        )
        self.user_uuid = UserUUID.objects.create(
            uuid='a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6',
            user=self.user
        )


    def test_find_user_by_uuid_found(self):
        """Test find_user_by_uuid method with existing UUID mapping."""

        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Test that existing user is returned when UUID exists
        result = sp.find_user_by_uuid('a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6')
        self.assertEqual(result, self.user)

    def test_find_user_by_uuid_not_found(self):
        """Test find_user_by_uuid method with non-existent UUID."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Test that None is returned when UUID doesn't exist
        nonexistent_uuid = '12345678-1234-1234-1234-123456789012'
        result = sp.find_user_by_uuid(nonexistent_uuid)
        self.assertIsNone(result)

    def test_find_user_by_uuid_case_insensitive(self):
        """Test find_user_by_uuid method with case insensitive UUID lookup."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Test that lookup is case insensitive - uppercase version
        result = sp.find_user_by_uuid('a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6'.upper())
        self.assertEqual(result, self.user)

        # Test that lookup is case insensitive - mixed case version
        result = sp.find_user_by_uuid('a1b2c3d4-e5f6-A7B8-C9D0-E1F2a3b4c5d6')
        self.assertEqual(result, self.user)
