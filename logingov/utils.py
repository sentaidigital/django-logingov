"""
Login.gov Service Provider controller.

The Service Provider controller does all the heavy lifting to connect to
Login.gov, respond to return redirects, fetch the user's information and
create a new user or link an existing one.
"""
import ast
import json
import logging
import os
import time
from urllib.parse import urlencode
import uuid

import jwt
from jwt import PyJWTError
import requests

# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.exceptions import SuspiciousSession
from django.utils.crypto import get_random_string

# Local module imports.
from logingov.exceptions import InvalidTokenError, InvalidEndpointError
from logingov.models import LoginGovSPSettings, UserUUID

logger = logging.getLogger(__name__)
_UNSET = object()

class LoginGovSP:
    """
    A Service Provider object for Login.gov.

    This class handles the integration with the Login.gov OpenID Connect
    service provider, including configuration management, token handling,
    user creation, and session validation.

    Attributes:
        sp_config: The configuration object for this service provider
        sp_id: The ID of the specific configuration instance to use
    """

    def __init__(self, spid=None):
        """
        Initialize the LoginGovSP instance.

        Args:
            spid: Optional ID of specific configuration to use, or None for default
        """
        self.sp_config = None
        self.sp_id = spid

    #
    # Settings Management
    #

    def load_settings(self):
        """
        Load the Login.gov Service Provider configuration from database.

        This method retrieves the configuration settings for the Login.gov
        integration, either by ID or as the first available configuration.

        Note:
            This method is called internally when settings need to be refreshed.
        """
        # Get the LoginGovConfig instance to check settings
        # try:
        #     config = LoginGovConfig.objects.get()
        # except (LoginGovConfig.ObjectDoesNotExist, LoginGovConfig.MultipleObjectsReturned):
        #     # Default config if none exists
        #     config = LoginGovConfig()

        if self.sp_id is not None:
            self.sp_config = LoginGovSPSettings.objects.get(id=self.sp_id)
        else:
            self.sp_config = LoginGovSPSettings.objects.first()
        logger.debug(self.sp_config)

    def _value_or_override(self, key: str, default: any=_UNSET) -> any:
        """
        Check for site-specific overrides. The priority order is:

        1. Environment variable `LOGIN_GOV_<key>`
        2. Variable in settings.py `LOGIN_GOV_<key>`
        3. The value of <key> in the database.

        Args:
            key: The setting key to look up
            default: Default value if no override is found

        Returns:
            The setting value from the highest priority source

        Raises:
            KeyError: If no override is found and no default is provided
        """
        # Check environment variables for override, highest priority.
        env_key = f"LOGIN_GOV_{key.upper()}"
        if env_key in os.environ:
            logger.debug("Returning environment value for %s", key)
            return os.environ[env_key]

        # Check Django settings for override, second priority.
        setting_key = f"LOGIN_GOV_{key.upper()}"
        if hasattr(settings, setting_key):
            logger.debug("Returning settings value for %s", key)
            return getattr(settings, setting_key)

        # Otherwise, pull from the database.
        if self.sp_config is None:
            self.load_settings()

        if hasattr(self.sp_config, key):
            logger.debug("Returning DB value for %s", key)
            return getattr(self.sp_config, key)

        if default is not _UNSET:
            return default

        raise KeyError(f"SP Setting '{key}' not found")

    def sandbox_mode(self) -> bool:
        """
        Get the sandbox mode setting.

        Returns:
            bool: True if sandbox mode is enabled, False otherwise
        """
        return self._value_or_override("sandbox_mode", True)

    def client_id(self) -> str | None:
        """
        Get the Login.gov client ID.

        Returns:
            str: The client ID for Login.gov authentication
        """
        return self._value_or_override("client_id", None)

    def acr_url(self) -> str:
        """
        Get the ACR (Authentication Context Class Reference) URL.

        Returns:
            str: The ACR URL combining IAL and AAL levels
        """
        aal_setting = self._value_or_override("aal_level", "duo")
        match aal_setting:
            case "duo":
                aal_value = "urn:gov:gsa:ac:classes:sp:PasswordProtectedTransport:duo"
            case "separate":
                aal_value = "http://idmanagement.gov/ns/assurance/aal/2"
            case "phishing_resistant" | "require_hspd12":
                aal_value = "http://idmanagement.gov/ns/assurance/aal/2?" + aal_setting

        acr = [
            "urn:acr.login.gov:" + self._value_or_override("ial_level", "auth-only"),
            aal_value,
        ]
        return " ".join(acr)

    def scope(self) -> str:
        """
        Get the OAuth 2.0 scope for the OpenID Connect request.

        Returns:
            str: Space-separated list of requested scopes
        """
        scopes = self._value_or_override("scopes", [])
        if scopes is None:
            scopes = []
        return " ".join(scopes + ["email"])

    def oidc_autoconfig(self) -> dict:
        """
        Get the OIDC autoconfiguration from database.

        Returns:
            dict: The OIDC autoconfiguration data
        """
        return self._value_or_override("oidc_autoconfig", {})

    def token_expire(self) -> int:
        """
        Get the token expiration time in seconds.

        Returns:
            int: Number of seconds after which tokens expire
        """
        return int(self._value_or_override("token_expire", 300))

    def http_timeout(self) -> tuple:
        """
        Get the HTTP request timeout configuration.

        Returns:
            tuple: Connect and read timeout values (connect_timeout, read_timeout)
        """
        http_timeout_raw = self._value_or_override("http_timeout", (2, 10))

        if isinstance(http_timeout_raw, tuple):
            return http_timeout_raw

        if isinstance(http_timeout_raw, str):
            http_timeout = ast.literal_eval(http_timeout_raw)
            if isinstance(http_timeout, tuple):
                return http_timeout

        # Return default if we don't find any valid data.
        return (2, 10)

    def allowed_drift(self) -> float:
        """
        Get the permitted clock drift between this system and Login.gov when
        validating the timestmaps of the token.

        Returns:
            float: The allowed drift in seconds, default 1.
        """
        return float(self._value_or_override('allowed_drift', 1))

    def private_key(self) -> str | None:
        """
        Load the private key for the site from one of the following, in priority
        order:

        1. Environment variable LOGIN_GOV_PRIVATE_KEY_PEM
            - PEM formatted private key with "BEGIN/END PRIVATE KEY" header and footer.
        2. Environment variable LOGIN_GOV_PRIVATE_KEY_FILE
            - Filename (relative to project root) of PEM formatted private key.
        3. Settings variable LOGIN_GOV_PRIVATE_KEY_FILE
            - Same as #2.

        Returns:
            str: The private key content or None if not found
        """

        # Return the PEM if it's in the environment
        if "LOGIN_GOV_PRIVATE_KEY_PEM" in os.environ:
            return os.environ["LOGIN_GOV_PRIVATE_KEY_PEM"]

        # Check for a filename, relative to the project root, for a
        # PEM-formatted file.
        pem_file_key = "LOGIN_GOV_PRIVATE_KEY_FILE"
        if pem_file_key in os.environ:
            key_file = os.environ[pem_file_key]
        elif hasattr(settings, pem_file_key):
            key_file = getattr(settings, pem_file_key)
        else:
            return None

        # If key_file is None or empty, return None
        if not key_file:
            logger.error("No private key specified in env or settings. Set "
            "LOGIN_GOV_PRIVATE_KEY_PEM in env or LOGIN_GOV_PRIVATE_KEY_FILE "
            "in either env or settings.")
            return None

        try:
            with open(key_file, "r", encoding="utf-8") as f:
                private_key = f.read()
        # If PEM key file can't be read, redirect to homepage.
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Could not open private key '%s'. Error: %s", key_file, e)
            return None
        return private_key

    #
    #  User Creation Settings
    #

    def auto_create_users(self) -> bool:
        """
        Get the setting for automatic user creation.

        Returns:
            bool: True if new users should be created automatically
        """
        return self._value_or_override("auto_create_users", False)

    def auto_link_users(self) -> bool:
        """
        Get the setting for automatic user linking.

        Returns:
            bool: True if existing users should be linked automatically
        """
        return self._value_or_override("auto_link_users", False)

    def default_group(self) -> int | None:
        """
        Get the default group for new or linked users.

        Returns:
            int: The default Django group ID or None if not set
        """
        return self._value_or_override("default_group", None)

    def hostname(self):
        """
        Return the base Login.gov URL for the target environment, sandbox or prod.

        Returns:
            str: The base Login.gov URL (sandbox or production)
        """
        return (
            "https://idp.int.identitysandbox.gov"
            if self.sandbox_mode() is True
            else "https://secure.login.gov"
        )

    #
    # Autoconfiguration from the .well-known URL.
    #

    def autoconfig(self):
        """
        Fetch the login.gov OIDC configuration from the well-known URL.

        Returns:
            dict: The OIDC configuration data
        """
        mode = "sandbox" if self.sandbox_mode() is True else "prod"
        if self.oidc_autoconfig() is None or self.oidc_autoconfig().get(mode) is None:
            self.update_autoconfig()

        logger.debug("Returning %s for oidc_autoconfig", mode)
        return self.oidc_autoconfig().get(mode)

    def update_autoconfig(self):
        """
        Update the OIDC autoconfiguration by fetching from Login.gov.

        This method fetches the OpenID Connect configuration from the well-known
        endpoint and stores it in the database for later use.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails
            json.JSONDecodeError: If the response is not valid JSON
        """
        # Connect to self.hostname() + '/.well-known/openid-configuration'
        url = self.hostname() + "/.well-known/openid-configuration"
        mode = "sandbox" if self.sandbox_mode() is True else "prod"

        try:
            timeout = self.http_timeout()
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()  # Raises an HTTPError for bad responses

            # Parse the JSON response into a dictionary
            config_data = response.json()

            # Save it to self.sp_config['oidc_autoconfig']
            if hasattr(self.sp_config, "oidc_autoconfig"):
                # Update the oidc_autoconfig field on the model instance
                self.sp_config.oidc_autoconfig[mode] = config_data
                self.sp_config.save()
            else:
                # If we don't have the field, we should still handle gracefully
                # This might not be reached in normal operation since sp_config
                # is loaded from the model.
                logger.warning(
                    "sp_config does not have oidc_autoconfig field. Cannot save configuration."
                )

        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch OIDC configuration from %s: %s", url, str(e))
            raise
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from %s: %s", url, str(e))
            raise

    def endpoint(self, key: str) -> str:
        """
        Return the URL for a specific Login.gov endpoint.

        Args:
            key: The endpoint key to look up

        Returns:
            str: The URL for the requested endpoint

        Raises:
            InvalidEndpointError: If the endpoint key is not valid
        """
        autoconfig = self.autoconfig()
        endpoint_keys = [
            "issuer",
            "authorization_endpoint",
            "jwks_uri",
            "token_endpoint",
            "userinfo_endpoint",
            "end_session_endpoint",
        ]
        if key in endpoint_keys:
            return autoconfig[key]

        raise InvalidEndpointError("Invalid endpoint {key}.")

    #
    # OIDC Process Elements
    #

    def get_access_token_for_code(self, code, session):
        """
        Exchange an authorization code for an access token from Login.gov.

        Args:
            code: The authorization code received from Login.gov
            session: The Django session object containing validation data

        Returns:
            str: The access token for making authenticated requests

        Raises:
            InvalidTokenError: If the token validation fails
            requests.exceptions.RequestException: If the HTTP request to Login.gov fails
        """
        self._validate_session(session)

        jwt_url = "{}?{}".format(   # pylint: disable=consider-using-f-string
            self.endpoint("token_endpoint"),
            urlencode(self.token_params(code))
        )

        try:
            timeout = self.http_timeout()
            response = requests.post(jwt_url, verify=True, timeout=timeout)
        # Handle POST failures gracefully with more informative logging
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to POST to token endpoint '%s' with code %s. Error: %s",
                self.endpoint('token_endpoint'), code, str(e)
            )
            # Log the actual URL for better debugging
            logger.debug("Attempted to POST to: %s", jwt_url)
            raise

        # PART 2.5: Decode & Validate JWT
        id_token_raw = response.json().get("id_token")
        try:
            id_token = self.decode_validate_jwt(id_token_raw)
        except (InvalidTokenError, PyJWTError) as e:
            logger.error("Failed to validate JWT token: %s", str(e))
            logger.debug("Invalid token: %s", id_token_raw)
            raise

        if id_token is None:
            logger.error("Could not read token.")
            logger.debug("Unsigned or unparsable token: %s", id_token_raw)
            raise InvalidTokenError("Could not read token")

        # Enhanced nonce validation with session consistency check
        session_nonce = session.get("login_gov_nonce")
        if id_token.get("nonce") != session_nonce:
            logger.error("Invalid Nonce: possible replay attack. Expected: %s, Got: %s",
                        session_nonce, id_token.get("nonce"))
            raise InvalidTokenError("Invalid nonce")

        return response.json().get("access_token")

    def decode_validate_jwt(self, token):
        """
        Decode and validate a JWT token received from Login.gov.

        Args:
            token: The JWT token string to decode and validate

        Returns:
            dict: The decoded token claims

        Raises:
            InvalidTokenError: If the token is unsigned or has invalid signature
        """
        header = jwt.get_unverified_header(token)

        # First check if the token has proper JWT format (3 parts separated by dots)
        if header is None:
            logger.error("Invalid JWT token format.")
            raise InvalidTokenError("Invalid JWT token format.")

        # Check for unsigned tokens
        if header.get("alg") == "none":
            logger.error("Unsigned token.")
            raise InvalidTokenError("Unsigned JWT from Login.gov.")

        # Get the signing key (this needs to be called with the header)
        key = self._get_jwks_signing_key(header)

        # Decode the token
        autoconfig=self.autoconfig()
        id_token = jwt.decode(
            token,
            key,
            verify=True,
            algorithms=autoconfig["token_endpoint_auth_signing_alg_values_supported"],
            audience=self.client_id(),
            issuer=autoconfig["issuer"],
            leeway=self.allowed_drift(),
            options={
                'verify_signature': True,
                'require': ['aud', 'iat', 'iss', 'exp', 'nbf'],
                'verify_aud': True,
                'verify_iat': True,
                'verify_iss': True,
                'verify_exp': True,
                'verify_nbf': True
            }
        )

        return id_token

    def fetch_claims(self, access_token):
        """
        Fetch user claims from Login.gov's userinfo endpoint.

        Args:
            access_token: The access token to use for authentication

        Returns:
            dict: The user claims data from Login.gov

        Raises:
            requests.exceptions.RequestException: If the HTTP request to Login.gov fails
        """
        # authorization dict for authorization header to retrieve user data
        user_payload = {"Authorization": "Bearer " + access_token}
        try:
            timeout = self.http_timeout()
            userinfo_endpoint = self.endpoint("userinfo_endpoint")
            user_data = requests.get(
                userinfo_endpoint, headers=user_payload, verify=True, timeout=timeout
            )
        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Userinfo Endpoint: %s.", str(e), exc_info=True)
            raise

        logger.debug("Fetched %s", json.dumps(user_data.json()))
        return user_data.json()

    #
    # Parameters and URL Generation
    #

    def authorization_params(self, session) -> dict:
        """
        Generate a dict of parameters for the authorization endpoint.

        A per-request nonce and state values are generated and saved to the
        current session for validation when Login.gov returns the user after
        authentication is complete.

        The caller is responsible for filling in the `redirect_uri` and the `locale` value, if
        used.

        Args:
            session: The Django session object to save the nonce and state

        Returns:
            dict: The parameters for the authentication request
        """
        # Construct the redirect_uri using Django's reverse function
        nonce = get_random_string(22)
        state = get_random_string(22)

        # Save nonce and state in the user's session
        session['login_gov_nonce'] = nonce
        session['login_gov_state'] = state

        url_params = {
            "acr_values": self.acr_url(),
            "client_id": self.client_id(),
            "prompt": "select_account",
            "response_type": "code",
            "scope": self.scope(),
            "state": state,
            "nonce": nonce,
        }

        return url_params


    def token_params(self, code) -> dict:
        """
        Generate a dict of parameters for the token request to Login.gov.

        Args:
            code: The authorization code received from Login.gov

        Returns:
            dict: The parameters for the token request
        """
        # required payload settings for login.gov
        payload = {
            "iss": self.client_id(),
            "sub": self.client_id(),
            "aud": self.endpoint("token_endpoint"),
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + int(self.token_expire()),
        }

        encoded_jwt = jwt.encode(payload, self.private_key(), algorithm="RS256")

        return {
            "client_assertion": encoded_jwt,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "code": code,
            "grant_type": "authorization_code",
        }

    def supported_languages(self) -> dict:
        """
        Return the list of supported language codes from Login.gov.

        Returns:
            A dict of supported langauges.
        """
        return ['en', 'es', 'fr']

    def cleanup_session(self, session):
        """
        Cleanup any session state managed by this controller.
        """
        if "login_gov_state" in session:
            del session["login_gov_state"]
        if "login_gov_nonce" in session:
            del session["login_gov_nonce"]

    #
    # Managing Users
    #

    def find_user_by_uuid(self, uuid:str):
        """
        Find a user by their UUID from Login.gov.

        Args:
            uuid: The UUID provided by Login.gov

        Returns:
            User: The Django User object or None if not found
        """
        try:
            user_uuid_record = UserUUID.objects.get(uuid__iexact=uuid)
            return user_uuid_record.user
        except UserUUID.DoesNotExist:
            return None

    def associate_user_with_uuid(self, sub: str, existing_user):
        """
        Associate a user with their Login.gov sub claim by creating a UserUUID record.

        Args:
            sub: The `sub` field from the claims
            existing_user: The Django User object to associate with the sub claim

        Returns:
            UserUUID: The created UserUUID record
        """

        try:
            user_uuid_record = UserUUID.objects.get(uuid__iexact=sub)
            return user_uuid_record
        except UserUUID.DoesNotExist:
            pass

        logger.info("Linking %s to Login.gov UUID %s", existing_user.username, sub)
        user_uuid_record = UserUUID.objects.create(
            uuid=sub,
            user=existing_user
        )
        return user_uuid_record

    def find_or_create_user_by_email(self, user_email):
        """
        Fetch or create a user based on their email from Login.gov.

        Args:
            user_email: The email address provided by Login.gov

        Returns:
            User: The Django User object (existing or newly created) or None if access denied
        """

        # Check if user with email provided by Login.gov auth already exists
        existing_user = get_user_model().objects.filter(email__iexact=user_email).first()

        # If user exists and automatic linking is enabled, use existing user
        if existing_user and self.auto_link_users():
            user = existing_user
            logger.info('User "%s" already exists. No account created.', user.username)
        # If automatic creation is enabled but no user exists, create new user
        elif not existing_user and self.auto_create_users():
            user = self._create_user_from_email(user_email, self.default_group())
        # If automatic creation is disabled, and no user exists, deny access
        elif not existing_user and not self.auto_create_users():
            logger.info(
                "Login.gov authentication failed for email %s: "
                "User does not exist and auto-creation is disabled", user_email
            )
            return None
        else:
            # Otherwise use the existing user
            user = existing_user

        return user

    def _create_user_from_email(
        self, email: str, default_group=None, is_staff: bool = False
    ) -> settings.AUTH_USER_MODEL:
        """
        Create a new user, using only an email address.

        Args:
            email: The user's email address
            default_group: Specifies the group to add new user to.
            is_staff: Sets "is staff" field value for new user (defaults to False).

        Returns:
            user: The new user that was created, or an existing user.
        """
        UserClass = get_user_model() # pylint: disable=invalid-name

        # Check if user already exists. Only get first matching result, to prevent
        # MultipleObjectsReturned exception.
        user = UserClass.objects.filter(email__iexact=email).order_by("email").first()
        if user is not None:
            logger.info('User "%s" already exists. No account created.', user.username)
            return user

        # New user's username will be their email, with "@" replaced by "_".
        email_split = email.split("@")
        # Convert email and username to lowercase before saving.
        email = email.lower()
        username = f"{email_split[0]}_{email_split[1]}".lower()

        # Create new user with basic access settings; is not staff user, so
        # can't login to Django admin.
        user = UserClass(
            is_superuser=False,
            is_staff=is_staff,
            username=username,
            email=email,
            is_active=True,
        )
        user.set_password(get_random_string(32))
        user.save()
        # Add group if it exists
        if default_group is not None:
            user.groups.add(default_group)

        logger.info("Created user %s for Login.gov entity %s", username, email)

        return user

    #
    # Validation Support
    #

    def _get_jwks_signing_key(self, header) -> str:
        """
        Return the signing key for login.gov.

        Returns:
            A JWKS Signing Key from the Login.gov jwks_uri endpoint.
        """
        jwks_url = self.endpoint("jwks_uri")
        jwks_client = jwt.PyJWKClient(jwks_url)
        key = jwks_client.get_signing_key(header["kid"]).key
        return key

    def _validate_session(self, session):
        """
        Validate the security session data for Login.gov authentication.

        This method checks that required session keys exist and have valid format,
        preventing session tampering attacks.

        Args:
            session: The Django session object to validate

        Returns:
            bool: True if session validation passes

        Raises:
            SuspiciousSession: If session integrity checks fail
        """
        # Session integrity checks
        # Check that all required session keys are present and not tampered with
        required_keys = ['login_gov_nonce', 'login_gov_state']
        for key in required_keys:
            if key not in session:
                logger.error("Session integrity check failed: missing key %s", key)
                raise SuspiciousSession("Invalid session state - missing required data")

        # Validate that session data has not been tampered with by checking
        # the structure and content of session values
        session_nonce = session.get("login_gov_nonce")
        session_state = session.get("login_gov_state")

        # Basic validation of session data structure
        if not isinstance(session_nonce, str) or len(session_nonce) < 22:
            logger.error("Session check failed: nonce has invalid format")
            raise SuspiciousSession("Invalid session state - nonce format error")

        if not isinstance(session_state, str) or len(session_state) < 22:
            logger.error("Session check failed: state has invalid format")
            raise SuspiciousSession("Invalid session state - state format error")

        return True
