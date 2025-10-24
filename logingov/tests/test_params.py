"""
Unit tests for the Login.gov Service Provider parameter generation.

This file contains unit tests for parameter generation methods in the LoginGovSP class.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, Mock

# Import the classes we're testing
from logingov.utils import LoginGovSP


class ParamsTestCase(TestCase):
    """
    Test cases for parameter generation methods in the LoginGovSP class.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = User.objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='testpass123'
        )

    def test_token_params(self):
        """Test token_params method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the required methods
        with patch.object(sp, 'client_id') as mock_client_id:
            with patch.object(sp, 'endpoint') as mock_endpoint:
                with patch.object(sp, 'token_expire') as mock_token_expire:
                    # Set up mock return values
                    mock_client_id.return_value = "test_client_id"
                    mock_endpoint.return_value = "https://test.example.com/token"
                    mock_token_expire.return_value = 300

                    # Mock the jwt.encode method
                    with patch('jwt.encode') as mock_encode:
                        mock_encode.return_value = "mock_jwt_token"

                        # Test token_params
                        result = sp.token_params("auth_code")

                        # Verify the returned parameters
                        self.assertIn("client_assertion", result)
                        self.assertEqual(result["client_assertion_type"], "urn:ietf:params:oauth:client-assertion-type:jwt-bearer")
                        self.assertEqual(result["code"], "auth_code")
                        self.assertEqual(result["grant_type"], "authorization_code")
