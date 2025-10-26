"""
Unit tests for the Login.gov Service Provider user login functionality.

This file contains unit tests for user login and creation methods in the LoginGovSP class.
"""
from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.test import TestCase

# Import the classes we're testing
from logingov.utils import LoginGovSP

class UserLoginTestCase(TestCase):
    """
    Test cases for user login and creation in the LoginGovSP class.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='admin@example.com',
            password=get_random_string(12)
        )

    def test_find_or_create_user_by_email_with_existing_user(self):
        """Test find_or_create_user_by_email method with existing user."""
        # Create a test user
        existing_user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password=get_random_string(12)
        )

        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the settings to enable auto_link_users
        with patch.object(sp, 'auto_link_users', return_value=True):
            # Test that existing user is returned when auto_link_users is True
            result = sp.find_or_create_user_by_email('test@example.com')
            self.assertEqual(result, existing_user)

    def test_find_or_create_user_by_email_with_new_user_creation(self):
        """Test find_or_create_user_by_email method with new user creation."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the settings to enable auto_create_users
        with patch.object(sp, 'auto_create_users', return_value=True):
            # Mock the _create_user_from_email method to return a new user
            with patch.object(sp, '_create_user_from_email') as mock_create:
                mock_user = Mock()
                mock_create.return_value = mock_user

                # Test that new user is created when auto_create_users is True
                result = sp.find_or_create_user_by_email('newuser@example.com')
                self.assertEqual(result, mock_user)
                mock_create.assert_called_once_with('newuser@example.com', None)

    def test_find_or_create_user_by_email_auto_create_disabled(self):
        """Test find_or_create_user_by_email method with auto-create disabled."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the settings to disable auto_create_users
        with patch.object(sp, 'auto_create_users', return_value=False):
            # Mock the settings to disable auto_link_users
            with patch.object(sp, 'auto_link_users', return_value=False):
                # Test that None is returned when both auto_create_users and
                # auto_link_users are False
                result = sp.find_or_create_user_by_email('nonexistent@example.com')
                self.assertIsNone(result)


    def test_create_user_from_email(self):
        """Test _create_user_from_email method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock get_user_model to return User class
        with patch('logingov.utils.get_user_model') as mock_get_user_model:
            mock_user_class = Mock()
            mock_user_class.objects.filter.return_value.order_by().first.return_value = None

            # Mock the set_password and save methods
            mock_user_instance = Mock()
            mock_user_class.return_value = mock_user_instance

            mock_get_user_model.return_value = mock_user_class

            # Test _create_user_from_email
            result = sp._create_user_from_email("test@example.com") # pylint: disable=protected-access

            # Verify that user creation was attempted
            self.assertEqual(result, mock_user_instance)
            mock_user_class.assert_called_once_with(
                is_superuser=False,
                is_staff=False,
                username="test_example.com",
                email="test@example.com",
                is_active=True
            )
            mock_user_instance.set_password.assert_called_once()
            mock_user_instance.save.assert_called_once()
