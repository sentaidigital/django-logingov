"""
Unit tests for the Login.gov Service Provider authentication integration.

This file contains unit tests for authentication-related functionality
including OIDC process and session management.
"""

from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.test import TestCase

from jwt import DecodeError

# Import the classes we're testing
from logingov.utils import LoginGovSP


class AuthenticationTestCase(TestCase):
    """
    Test cases for the LoginGovSP authentication functionality.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='admin@example.com',
            password=get_random_string(12)
        )

    def test_fetch_claims_with_exception(self):
        """Test fetch_claims method with HTTP exception."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the endpoint method to return a valid URL
        with patch.object(sp, 'endpoint') as mock_endpoint:
            mock_endpoint.return_value = "https://test.example.com/userinfo"

            # Mock the requests.get to raise an exception
            with patch('requests.get') as mock_get:
                mock_get.side_effect = Exception("Network error")

                # Test that exception is raised
                with self.assertRaises(Exception):
                    sp.fetch_claims("test_token")

    def test_decode_validate_jwt_with_exception(self):
        """Test decode_validate_jwt method with exception handling."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the endpoint method to return valid URLs
        with patch.object(sp, 'endpoint') as mock_endpoint:
            mock_endpoint.return_value = "https://test.example.com/jwks"

            # Mock the jwt.PyJWKClient to raise an exception
            with patch('jwt.PyJWKClient') as mock_jwk_client:
                mock_jwk_client_instance = Mock()
                mock_jwk_client_instance.get_signing_key.side_effect = Exception("JWK error")
                mock_jwk_client.return_value = mock_jwk_client_instance

                # Test that InvalidTokenError is raised when JWT validation fails
                with self.assertRaises(DecodeError):
                    sp.decode_validate_jwt("invalid_token")

    def test_get_access_token_for_code_with_exception(self):
        """Test get_access_token_for_code method with exception handling."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the required methods to return valid values
        with patch.object(sp, '_validate_session') as mock_validate:
            with patch.object(sp, 'endpoint') as mock_endpoint:
                with patch.object(sp, 'token_params') as mock_token_params:
                    with patch('requests.post') as mock_post:
                        # Mock the validation to pass
                        mock_validate.return_value = True

                        # Mock endpoint to return valid URLs
                        mock_endpoint.return_value = "https://test.example.com/token"

                        # Mock token_params to return valid parameters
                        mock_token_params.return_value = {"test_param": "test_value"}

                        # Mock the requests.post to raise an exception
                        mock_post.side_effect = Exception("Network error")

                        # Test that exception is raised
                        with self.assertRaises(Exception):
                            sp.get_access_token_for_code("auth_code", {})
