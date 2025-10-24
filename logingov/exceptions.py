class LoginGovError(Exception):
    """
    A base exception for all Login.gov errors.

    This is the parent exception class for all custom exceptions related to
    Login.gov authentication functionality.
    """

class InvalidEndpointError(LoginGovError):
    """
    Exception raised when an invalid endpoint is requested.

    This error occurs when trying to access a Login.gov OpenID Connect
    endpoint that doesn't exist or is not supported.
    """

class InvalidTokenError(LoginGovError):
    """
    Exception raised when a token validation fails.

    This error occurs when JWT tokens received from Login.gov fail
    validation checks such as signature verification, expiration,
    or nonce matching.
    """
