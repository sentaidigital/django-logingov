"""
Unit tests for the Login.gov Service Provider session management.

This file contains unit tests for session handling and cleanup functionality.
"""

from django.contrib.sessions.exceptions import SuspiciousSession
from django.test import TestCase

# Import the classes we're testing
from logingov.utils import LoginGovSP

class SessionTestCase(TestCase):
    """
    Test cases for session management and cleanup in the LoginGovSP class.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""

    def test_cleanup_session_with_empty_session(self):
        """Test cleanup_session method with empty session."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Create an empty session
        session = {}

        # Test cleanup_session doesn't crash with empty session
        sp.cleanup_session(session)

        # Session should remain empty
        self.assertEqual(session, {})

    def test_cleanup_session_with_nonexistent_keys(self):
        """Test cleanup_session method with session missing keys."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Create session with non-login_gov keys
        session = {
            'other_key': 'value',
            'another_key': 'another_value'
        }

        # Test cleanup_session doesn't crash and preserves non-login_gov keys
        sp.cleanup_session(session)

        # Should have removed login_gov keys and kept others
        self.assertNotIn('login_gov_state', session)
        self.assertNotIn('login_gov_nonce', session)
        self.assertIn('other_key', session)
        self.assertIn('another_key', session)

    def test_validate_session_missing_keys(self):
        """Test _validate_session method with missing required keys."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Create session missing required keys
        session = {
            'login_gov_nonce': 'a' * 22,
            # Missing login_gov_state
        }

        # Test that SuspiciousSession is raised for missing keys
        with self.assertRaises(SuspiciousSession):
            sp._validate_session(session)  # pylint: disable=protected-access

    def test_validate_session_invalid_nonce_format(self):
        """Test _validate_session method with invalid nonce format."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Create session with invalid nonce format (too short)
        session = {
            'login_gov_nonce': 'short',  # Too short for nonce
            'login_gov_state': 'b' * 22
        }

        # Test that SuspiciousSession is raised for invalid nonce format
        with self.assertRaises(SuspiciousSession):
            sp._validate_session(session)  # pylint: disable=protected-access

    def test_validate_session_valid(self):
        """Test _validate_session method with valid session."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Create session with valid required keys
        session = {
            'login_gov_nonce': 'a' * 22,
            'login_gov_state': 'b' * 22
        }

        # Test that valid session passes validation (should return True)
        result = sp._validate_session(session)  # pylint: disable=protected-access
        self.assertTrue(result)
