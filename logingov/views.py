import logging
from urllib.parse import quote, urlencode, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import DisallowedHost, PermissionDenied
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.views.generic.base import RedirectView
from django.views.generic import View
from logingov.utils import LoginGovSP

# Some module-level globals.
logger = logging.getLogger(__name__)

# Load the Login.gov SP object.
lgc = LoginGovSP()

class LoginGovRedirectView(RedirectView):
    """
    Django RedirectView for handling Login.gov authentication redirects.

    This view prepares the authentication request to Login.gov by generating
    the appropriate redirect URL with required parameters including nonce,
    state, and scope.

    Methods:
        get_redirect_url: Generate the redirect URL to Login.gov
        generate_nonce: Generate a secure random nonce for authentication
    """

    # Build the redirect target URL.
    def get_redirect_url(self, *args, **kwargs):
        """
        Generate the redirect URL to Login.gov's authorization endpoint.

        This method constructs the full authorization URL that will redirect
        users to Login.gov for authentication, including all required OAuth 2.0
        parameters.

        Args:
            *args: Variable arguments passed to parent class
            **kwargs: Keyword arguments passed to parent class

        Returns:
            str: The complete authorization URL for Login.gov
        """
        # Clear any existing login.gov session data to ensure clean authentication flow
        lgc.cleanup_session(self.request.session)

        # PART 1: Initial Login.gov Request
        url_params = lgc.authorization_params(self.request.session)
        url_params["redirect_uri"] = self.request.build_absolute_uri(reverse("logingov:auth_cloud"))

        # Build the final URL
        url = "{}?{}".format(   # pylint: disable=consider-using-f-string
            lgc.endpoint("authorization_endpoint"),
            urlencode(url_params)
        )
        return url

class AuthCloudView(RedirectView):
    """
    Django View class for handling the Login.gov authentication callback.

    This view processes the authorization code returned by Login.gov, exchanges
    it for an access token, fetches user claims, and logs the user in.

    Methods:
        get_redirect_url: Handle GET requests with authorization code from Login.gov
    """

    def get_redirect_url(self, *args, **kwargs):
        """
        Handle the callback from Login.gov after successful authentication.

        This method processes the authorization code returned by Login.gov, exchanges
        it for an access token, fetches user claims, and logs the user in.

        Args:
            request: The Django HttpRequest object containing the callback parameters

        Returns:
            HttpResponse: Redirect to appropriate page or render error pages
        """
        # GET query params from login.gov from redirect URL.
        code = quote(self.request.GET.get("code", None))
        error = self.request.GET.get("error", None)

        # Part 0: Validate internal settings

        # If "error" query param from login.gov redirect URL contains an error
        # (such as "access denied") -or- "code" param is not set -or- any required
        # settings are missing, log the issue, then redirect user to home page.
        if (
            error is not None
            or code is None
        ):
            # Log specific issue with Login.gov-provided redirect URL.
            if code is None:
                logger.error(
                    'Login.gov provided redirect URL with missing "code" parameter.'
                )
            elif error is not None:
                logger.error('Login.gov provided redirect URL set to "%s".', error)
            # Log issue with missing setting or environment variable.
            else:
                logger.error(
                    "Missing required setting or env variable(s) for JWT token request."
                )
            messages.error(self.request,
                'An error occured communicating with Login.gov. See logs for details.'
            )
            return "/accounts/login?e=invalid-config"

        try:
            # PART 2: Get the JWT from Login.gov
            access_token = lgc.get_access_token_for_code(code, self.request.session)

            # PART 3: Fetch the User Claims
            claims = lgc.fetch_claims(access_token)
            user_email = claims.get("email")
        except Exception as e:
            logger.exception('Failed to fetch claims from Login.gov: %s', str(e))
            messages.error(self.request, 'Unable to communicate with Login.gov. See logs for details.')
            return "/accounts/login?e=bad-token"

        # TODO - Add a signal here to allow other apps to react to the claims.


        # PART 4: Create / Connect & Login User
        user = lgc.find_user_by_uuid(claims.get('sub'))

        if user is not None:
            logger.info("Found user %s by their Login.gov UUID.", user.username)
        else:
            user = lgc.find_or_create_user_by_email(user_email)

        if user is not None and lgc.auto_link_users():
            lgc.associate_user_with_uuid(claims.get("sub"), user)

        # If user was not found (or not created), redirect to home page with an error.
        if user is None:
            messages.error(self.request, "Cannot Login: No user exists with email {user_email}")
            return '/accounts/login?e=invalid-user'

        if not user.is_active:
            logger.warning("Login Denied: User %s authenticated by Login.gov, but is inactive.",
                user.username)
            messages.error(self.request, "Cannot Login: {user.username}'s account is disabled.")
            return '/accounts/login?e=inactive-user'

        if user.is_active:
            login(self.request, user)
            logger.info("User %s successfully authenticated by Login.gov.", user.username)
            messages.success(self.request, "You have been successfully logged into the system.")
            if user.is_staff or user.is_superuser:
                return "/admin/"
            else:
                return "/polls"

class LogoutView(RedirectView):
    """
    Django RedirectView for handling user logout from the Login.gov authentication system.

    This view logs out the user and clears their session data related to
    Login.gov authentication, then redirects to the homepage.

    Methods:
        get_redirect_url: Generate the redirect URL after logout
    """

    def get_redirect_url(self, *args, **kwargs):
        """
        Generate the redirect URL after logout.

        This method handles the logout process by calling Django's logout function,
        setting appropriate messages, and returning the redirect URL.

        Args:
            *args: Variable arguments passed to parent class
            **kwargs: Keyword arguments passed to parent class

        Returns:
            str: The redirect URL after logout
        """
        # Function removes token from login.gov
        logout(self.request)
        inactive = self.request.GET.get("inactive")
        messages.info(self.request, "You have been successfully logged out of the system.")
        # Redirect logged-out user to homepage. Include "inactive" query param if
        # it's true (js code will display modal "you've been signed out" message
        # if it sees this param).
        redirect_url = "/?inactive=true" if inactive else "/"
        return redirect_url

def _validate_auth_url(url: str) -> str:
    """
    Check if an authentication URL is in a supplied list of allowed URLs.

    This helper function validates that the provided URL is in the list of
    allowed authentication domains to prevent open redirect vulnerabilities.

    Args:
        url: The URL to be checked

    Returns:
        str: The validated URL

    Raises:
        DisallowedHost: If the URL is not in allowed domains
    """
    parse = urlparse(url)
    url_parsed = parse.geturl()
    url_is_safe = url_has_allowed_host_and_scheme(
        url=url_parsed,
        allowed_hosts=set(settings.ALLOWED_AUTH_LOGIN_DOMAINS),
        require_https=False,
    )
    if not url_is_safe:
        raise DisallowedHost(
            "The authentication URL is not in the allowed auth login domains."
        )

    return url_parsed

class RefreshSessionView(View):
    """
    Django View class for handling refresh-session endpoint.

    This view allows authenticated users to refresh their session by making
    a GET request, which can be useful for maintaining session state in
    single-page applications.
    """

    def get(self, request):
        """
        Handle GET requests to refresh a user's session.

        Args:
            request: The Django HttpRequest object

        Returns:
            JsonResponse: A JSON response with session information

        Raises:
            PermissionDenied: If the user is not authenticated
        """
        # Only allow authenticated users to access this endpoint.
        if request.user is not None and request.user.is_authenticated:
            data = {
                "token": "ok",
                "cookies": request.COOKIES,
            }
            return JsonResponse(data)
        else:
            raise PermissionDenied("Access not granted.")
