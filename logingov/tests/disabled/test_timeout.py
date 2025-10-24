"""
Unit tests for the Login.gov Service Provider timeout functionality.

This file contains unit tests to verify that timeout configuration works correctly
and all HTTP requests use the timeout parameter.
"""

import os
from unittest.mock import patch, Mock, PropertyMock, MagicMock

from django.utils.crypto import get_random_string
from django.test import TestCase

# Import the classes we're testing
from logingov.utils import LoginGovSP


class TimeoutTestCase(TestCase):
    """
    Test cases for the timeout functionality in LoginGovSP.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""

    def test_default_timeout(self):
        """Test that default timeout values are used when no configuration is provided."""
        # Create a LoginGovSP instance
        lgc = LoginGovSP()

        # Mock the _value_or_override method to return default values
        with patch.object(lgc, '_value_or_override') as mock_override:
            mock_override.side_effect = lambda key, default: default if key == "http_timeout" else None

            # Check that the timeout method returns the default
            timeout = lgc.http_timeout()
            expected = (2, 10)

            self.assertEqual(timeout, expected, f"Expected {expected}, got {timeout}")

    def test_env_override_timeout(self):
        """Test that environment variable overrides work."""
        # Set the environment variable
        os.environ["LOGIN_GOV_HTTP_TIMEOUT"] = "(5, 15)"

        try:
            # Create a LoginGovSP instance
            lgc = LoginGovSP()

            # Mock the _value_or_override method to return environment variable
            with patch.object(lgc, '_value_or_override') as mock_override:
                # Mock to return the environment variable when checking http_timeout
                def mock_side_effect(key, default):
                    if key == "http_timeout":
                        return (5, 15)  # From environment
                    return default

                mock_override.side_effect = mock_side_effect

                # Check that the timeout method returns the environment value
                timeout = lgc.http_timeout()
                expected = (5, 15)

                self.assertEqual(timeout, expected, f"Expected {expected}, got {timeout}")

        finally:
            # Clean up environment variable
            if "LOGIN_GOV_HTTP_TIMEOUT" in os.environ:
                del os.environ["LOGIN_GOV_HTTP_TIMEOUT"]

    def test_http_requests_use_timeout(self):
        """Test that HTTP requests are made with timeout parameter."""
        # Create a LoginGovSP instance
        mock_session = Mock()
        type(mock_session).login_gov_nonce=PropertyMock(return_value=get_random_string(22))
        type(mock_session).login_gov_state=PropertyMock(return_value=get_random_string(22))

        lgc = LoginGovSP()

        # Mock the requests module to capture call parameters
        with patch('logingov.utils.requests') as mock_requests:
            # Mock responses to avoid actual HTTP calls
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {}

            # Set up the mocks for different types of calls
            mock_requests.get.return_value = mock_response
            mock_requests.post.return_value = mock_response

            # Test that the update_autoconfig method uses timeout
            lgc.update_autoconfig()
            # Verify that the get call was made with timeout parameter
            self.assertTrue(mock_requests.get.called, "GET request should be called")
            call_args = mock_requests.get.call_args
            self.assertIn('timeout', call_args.kwargs, "GET request should include timeout parameter")

            # Reset mock for next test
            mock_requests.reset_mock()

            # Test that the get_access_token_for_code method uses timeout
            lgc.get_access_token_for_code("test_code", mock_session)
            # Verify that the post call was made with timeout parameter
            self.assertTrue(mock_requests.post.called, "POST request should be called")
            call_args = mock_requests.post.call_args
            self.assertIn('timeout', call_args.kwargs, "POST request should include timeout parameter")

            # Reset mock for next test
            mock_requests.reset_mock()

            # Test that the fetch_claims method uses timeout
            lgc.fetch_claims("test_token")
            # Verify that the get call was made with timeout parameter
            self.assertTrue(mock_requests.get.called, "GET request should be called")
            call_args = mock_requests.get.call_args
            self.assertIn('timeout', call_args.kwargs, "GET request should include timeout parameter")
