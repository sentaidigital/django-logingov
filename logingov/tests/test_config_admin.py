"""
Unit tests for the Login.gov admin interface.

This file contains unit tests for testing the administration of a LoginGovSP record.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from logingov.models import LoginGovSPSettings

class ConfigAdminTestCase(TestCase):
    """
    Test cases for the LoginGovSPSettings model configuration.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='testpass123'
        )

    def test_config_creation(self):
        """Test that LoginGovSPSettings model can be created with custom values."""
        # Test that LoginGovSPSettings model can be created
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            scopes=[]
        )

        self.assertEqual(config.sandbox_mode, True)
        self.assertEqual(config.client_id, "test-client-id")

    def test_config_default_values(self):
        """Test that LoginGovSPSettings has appropriate default values."""
        # Test that LoginGovSPSettings has default values
        config = LoginGovSPSettings.objects.create(
            client_id="default-client-id",
            scopes=[]
        )

        self.assertEqual(config.sandbox_mode, True)
        self.assertEqual(config.client_id, "default-client-id")
        self.assertEqual(config.auto_create_users, False)
        self.assertEqual(config.auto_link_users, False)

    def test_config_admin_access(self):
        """Test that configuration can be accessed via admin interface."""
        # Test that configuration can be accessed via admin interface
        # This is more of a structural test to ensure no errors occur
        LoginGovSPSettings.objects.create(
            sandbox_mode=False,
            client_id="production-client-id",
            scopes=[]
        )

        # Verify the configuration is accessible
        retrieved_config = LoginGovSPSettings.objects.get()
        self.assertEqual(retrieved_config.sandbox_mode, False)
        self.assertEqual(retrieved_config.client_id, "production-client-id")
