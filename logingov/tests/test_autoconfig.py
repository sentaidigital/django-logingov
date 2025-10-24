"""
Unit tests for the Login.gov Service Provider autoconfiguration functionality.

This file contains unit tests for OIDC autoconfiguration and endpoint handling.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.test import TestCase

# Import the classes we're testing
from logingov.exceptions import InvalidEndpointError
from logingov.models import LoginGovSPSettings
from logingov.utils import LoginGovSP


class AutoconfigTestCase(TestCase):
    """
    Test cases for OIDC autoconfiguration and endpoint handling in LoginGovSP.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password=get_random_string(12)
        )

    def test_oidc_autoconfig(self):
        """Test oidc_autoconfig method."""
        # Create a test configuration with OIDC autoconfig
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            oidc_autoconfig={"sandbox": {"issuer": "https://test-issuer"}}
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test that oidc_autoconfig returns correct value
        result = sp.oidc_autoconfig()
        self.assertEqual(result, {"sandbox": {"issuer": "https://test-issuer"}})

        # Test that autoconfig returns correct value
        result = sp.autoconfig()
        self.assertEqual(result, {"issuer": "https://test-issuer"})


    def test_endpoint_invalid_key(self):
        """Test endpoint method with invalid endpoint key."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock autoconfig to return valid config
        with patch.object(sp, 'autoconfig') as mock_autoconfig:
            mock_autoconfig.return_value = {
                "issuer": "https://test.example.com/issuer",
                "authorization_endpoint": "https://test.example.com/auth"
            }

            # Test that InvalidEndpointError is raised for invalid endpoint
            with self.assertRaises(InvalidEndpointError):
                sp.endpoint("invalid_endpoint")
