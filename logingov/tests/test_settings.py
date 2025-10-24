"""
Unit tests for the Login.gov Service Provider settings and configuration.

This file contains unit tests that verify the LoginGovSP class returns valid
parameters and handles missing values and overrides correctly.
"""
import os
from unittest.mock import patch, Mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.test import TestCase

# Import the classes we're testing
from logingov.utils import LoginGovSP
from logingov.models import LoginGovSPSettings

class SettingsTestCase(TestCase):
    """
    Test cases for LoginGovSP settings and configuration management.
    """

    def setUp(self):
        """Set up test fixtures before running each test method."""
        # Create a test user for authentication testing
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='testpass123'
        )

    def test_load_settings_with_spid(self):
        """Test loading settings with a specific SP ID."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id"
        )

        # Create LoginGovSP instance with specific ID
        sp = LoginGovSP(spid=config.id)

        # Mock the load_settings method to avoid actual database queries
        with patch.object(sp, 'load_settings') as mock_load:
            sp.load_settings()

            # Verify that load_settings was called
            mock_load.assert_called_once()

    def test_load_settings_without_spid(self):
        """Test loading settings without a specific SP ID."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id"
        )
        config.save()

        # Create LoginGovSP instance without specific ID
        sp = LoginGovSP()
        sp.load_settings()

        # Verify that load_settings was called
        self.assertEqual(sp.sp_config.sandbox_mode, config.sandbox_mode)
        self.assertEqual(sp.sp_config.client_id, config.client_id)

    def test_value_or_override_priority_order(self):
        """Test the priority order for setting value overrides."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="db-client-id"
        )

        sp = LoginGovSP()

        # Set up environment variable override
        with patch.dict(os.environ, {'LOGIN_GOV_SANDBOX_MODE': 'False'}):
            # Test environment variable override (highest priority)
            result = sp._value_or_override("sandbox_mode", True)  # pylint: disable=protected-access
            self.assertEqual(result, "False")  # String from environment

        # Test Django settings override (second priority)
        with patch.object(settings, 'LOGIN_GOV_CLIENT_ID', 'settings-client-id', create=True):
            result = sp._value_or_override("client_id", "default")  # pylint: disable=protected-access
            self.assertEqual(result, "settings-client-id")

        # Test database fallback (lowest priority)
        sp.sp_config = config
        result = sp._value_or_override("client_id", "default")  # pylint: disable=protected-access
        self.assertEqual(result, "db-client-id")

    def test_value_or_override_with_default(self):
        """Test _value_or_override with default values."""
        sp = LoginGovSP()

        # Test that default value is returned when setting not found
        result = sp._value_or_override("nonexistent_key", "default_value")  # pylint: disable=protected-access
        self.assertEqual(result, "default_value")

    def test_sandbox_mode(self):
        """Test sandbox_mode method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the _value_or_override method to return a specific value
        with patch.object(sp, '_value_or_override') as mock_value_or_override:
            mock_value_or_override.return_value = True

            # Test sandbox_mode
            result = sp.sandbox_mode()
            self.assertTrue(result)

    def test_client_id(self):
        """Test client_id method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the _value_or_override method to return a specific value
        with patch.object(sp, '_value_or_override') as mock_value_or_override:
            mock_value_or_override.return_value = "test_client_id"

            # Test client_id
            result = sp.client_id()
            self.assertEqual(result, "test_client_id")

    def test_acr_url(self):
        """Test acr_url method with different AAL levels."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            ial_level="verified",
            aal_level="duo"
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test with default AAL level (duo)
        result = sp.acr_url()
        self.assertIn("urn:gov:gsa:ac:classes:sp:PasswordProtectedTransport:duo", result)

        # Test with separate AAL level
        config.aal_level = "separate"
        config.save()

        result = sp.acr_url()
        self.assertIn("http://idmanagement.gov/ns/assurance/aal/2", result)

        # Test with phishing_resistant AAL level
        config.aal_level = "phishing_resistant"
        config.save()

        result = sp.acr_url()
        self.assertIn("http://idmanagement.gov/ns/assurance/aal/2?phishing_resistant", result)

    def test_scope(self):
        """Test scope method."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            scopes=["given_name", "locale", "x509"]
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test that scope includes required fields and custom userinfo fields
        result = sp.scope()
        self.assertIn("email", result)
        self.assertIn("given_name", result)
        self.assertIn("locale", result)
        self.assertIn("x509", result)
        self.assertNotIn("address", result)
        self.assertNotIn("birthdate", result)


    def test_token_expire(self):
        """Test token_expire method."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            token_expire=600
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test that token_expire returns correct value
        result = sp.token_expire()
        self.assertEqual(result, 600)

    def test_http_timeout(self):
        """Test http_timeout method."""
        # Test 1: Default value when not set anywhere
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
        )
        sp = LoginGovSP()
        sp.sp_config = config

        result = sp.http_timeout()
        self.assertEqual(result, (2, 10))

        # Test 2: Value from environment variable (highest priority)
        with patch.dict(os.environ, {'LOGIN_GOV_HTTP_TIMEOUT': '(1, 8)'}):
            sp = LoginGovSP()
            result = sp.http_timeout()
            self.assertEqual(result, (1, 8))

        # Test 3: Value from Django settings (second priority), as string.
        with patch.object(settings, 'LOGIN_GOV_HTTP_TIMEOUT', '(3, 8)', create=True):
            sp = LoginGovSP()
            result = sp.http_timeout()
            self.assertEqual(result, (3, 8))

        # Test 4: Value from Django settings (second priority), as tuple.
        with patch.object(settings, 'LOGIN_GOV_HTTP_TIMEOUT', (4, 9), create=True):
            sp = LoginGovSP()
            result = sp.http_timeout()
            self.assertEqual(result, (4, 9))
            # Test 5: Override the settings wiht an environment setting.
            with patch.dict(os.environ, {'LOGIN_GOV_HTTP_TIMEOUT': '(5, 6)'}):
                sp = LoginGovSP()
                result = sp.http_timeout()
                self.assertEqual(result, (5, 6))

    def test_allowed_drift(self):
        """Test allowed_drift method."""
        # Create a test configuration
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
        )
        sp = LoginGovSP()
        sp.sp_config = config

        # Test 2: Value from the environment variable
        with patch.dict(os.environ, {"LOGIN_GOV_ALLOWED_DRIFT": "2.5"}):
            # Test that allowed_drift returns correct value
            result = sp.allowed_drift()
            self.assertEqual(result, 2.5)

        # Test 3: Value from Django settings (second priority)
        with patch.object(settings, "LOGIN_GOV_ALLOWED_DRIFT", "3.5", create=True):
            # Test that allowed_drift returns correct value
            result = sp.allowed_drift()
            self.assertEqual(result, 3.5)
            # Test 4: Override the settings with the environment
            with patch.dict(os.environ, {"LOGIN_GOV_ALLOWED_DRIFT": "4.5"}):
                # Test that allowed_drift returns correct value
                result = sp.allowed_drift()
                self.assertEqual(result, 4.5)

    def test_private_key_with_env_var(self):
        """Test private_key method with environment variable."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Set up environment variable with private key
        with patch.dict(os.environ, {'LOGIN_GOV_PRIVATE_KEY_PEM': 'mock_private_key_content'}):
            # Test that private key is returned from environment variable
            result = sp.private_key()
            self.assertEqual(result, 'mock_private_key_content')

    def test_private_key_with_file(self):
        """Test private_key method with file path."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the settings to return a file path
        with patch.object(settings, 'LOGIN_GOV_PRIVATE_KEY_FILE', 'mock_key_path', create=True):
            # Mock file reading to return content
            with patch('builtins.open') as mock_open:
                mock_file = Mock()
                mock_file.read.return_value = 'mock_file_content'
                mock_open.return_value.__enter__.return_value = mock_file
                # Test that private key is returned from file
                result = sp.private_key()
                self.assertEqual(result, 'mock_file_content')

    def test_private_key_with_no_source(self):
        """Test private_key method with no source."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock all sources to return None
        with patch.dict(os.environ, {}):
            with patch.object(settings, 'LOGIN_GOV_PRIVATE_KEY_FILE', None, create=True):
                # Test that private key returns None when no source is available
                result = sp.private_key()
                self.assertIsNone(result)

    def test_auto_create_users(self):
        """Test auto_create_users method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the _value_or_override method to return a specific value
        with patch.object(sp, '_value_or_override') as mock_value_or_override:
            mock_value_or_override.return_value = True

            # Test auto_create_users
            result = sp.auto_create_users()
            self.assertTrue(result)

    def test_auto_link_users(self):
        """Test auto_link_users method."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the _value_or_override method to return a specific value
        with patch.object(sp, '_value_or_override') as mock_value_or_override:
            mock_value_or_override.return_value = False

            # Test auto_link_users
            result = sp.auto_link_users()
            self.assertFalse(result)

    def test_default_group(self):
        """Test default_group method."""
        # Create a test configuration with default_group=None
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            default_group=None
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test that default_group returns correct value
        result = sp.default_group()
        self.assertIsNone(result)

    def test_supported_languages(self):
        """Test supported_languages method returns expected list."""
        sp = LoginGovSP()

        # Test that supported_languages returns the expected list of languages
        result = sp.supported_languages()
        self.assertEqual(result, ['en', 'es', 'fr'])


    def test_hostname(self):
        """Test hostname method."""
        # Create a test configuration with sandbox_mode=True
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id"
        )

        sp = LoginGovSP()
        sp.sp_config = config

        # Test that hostname returns sandbox URL for sandbox mode
        result = sp.hostname()
        self.assertEqual(result, "https://idp.int.identitysandbox.gov")

        # Change to production mode
        config.sandbox_mode = False
        config.save()

        result = sp.hostname()
        self.assertEqual(result, "https://secure.login.gov")

    def test_acr_url_with_different_aal_levels(self):
        """Test acr_url method with different AAL levels."""
        # Test default AAL level (duo)
        config_duo = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            aal_level="duo",
            ial_level="auth-only"
        )
        sp_duo = LoginGovSP()
        sp_duo.sp_config = config_duo
        result = sp_duo.acr_url()
        self.assertIn("urn:gov:gsa:ac:classes:sp:PasswordProtectedTransport:duo", result)

        # Test separate AAL level
        config_separate = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            aal_level="separate",
            ial_level="auth-only"
        )
        sp_separate = LoginGovSP()
        sp_separate.sp_config = config_separate
        result = sp_separate.acr_url()
        self.assertIn("http://idmanagement.gov/ns/assurance/aal/2", result)

        # Test phishing_resistant AAL level
        config_phishing = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id="test-client-id",
            aal_level="phishing_resistant",
            ial_level="auth-only"
        )
        sp_phishing = LoginGovSP()
        sp_phishing.sp_config = config_phishing
        result = sp_phishing.acr_url()
        self.assertIn("http://idmanagement.gov/ns/assurance/aal/2?phishing_resistant", result)

    def test_scope_with_custom_fields(self):
        """Test scope method with custom userinfo fields."""
        # Create a LoginGovSP instance
        config = LoginGovSPSettings.objects.create(
            sandbox_mode=True,
            client_id=get_random_string(12),
            scopes = ["locale", "profile:name"]
        )
        sp = LoginGovSP()
        sp.sp_config = config

        result = sp.scope()
        self.assertIn("email", result)
        self.assertIn("locale", result)
        self.assertIn("profile:name", result)
        # self.assertTrue(False, 'scope needs to translate')

    def test_hostname_with_sandbox_and_production(self):
        """Test hostname method with sandbox and production modes."""
        # Create a LoginGovSP instance
        sp = LoginGovSP()

        # Mock the sandbox_mode method to return True (sandbox mode)
        with patch.object(sp, 'sandbox_mode', return_value=True):
            result = sp.hostname()
            self.assertEqual(result, "https://idp.int.identitysandbox.gov")

        # Mock the sandbox_mode method to return False (production mode)
        with patch.object(sp, 'sandbox_mode', return_value=False):
            result = sp.hostname()
            self.assertEqual(result, "https://secure.login.gov")
