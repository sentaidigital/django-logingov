"""
Model definitions for Login.gov integration.
"""

from django.db import models

class LoginGovSPSettings(models.Model):
    """
    Django model representing Login.gov Service Provider settings.

    This model stores configuration parameters required for integrating with
    the Login.gov OpenID Connect service provider. It includes settings for
    authentication modes, client configuration, user management, and
    authentication levels (IAL and AAL).

    Attributes:
        sandbox_mode: Boolean indicating if sandbox mode is enabled
        client_id: The client ID for Login.gov authentication
        auto_create_users: Boolean indicating if new users should be created automatically
        auto_link_users: Boolean indicating if existing users should be linked automatically
        default_group: Default Django group for new or linked users
        oidc_autoconfig: JSON field storing OIDC auto configuration
        ial_level: Identity Assurance Level setting
        aal_level: Authenticator Assurance Level setting
        scopes: JSON field storing requested scopes
        updated_at: Timestamp of last update
    """

    class Meta:
        """
        Metadata for LoginGovSPSettings
        """
        verbose_name = "Login.gov SP"
        verbose_name_plural = "Login.gov SP Configurations"

    # Default to sandbox mode
    sandbox_mode = models.BooleanField(
        default=True, help_text="Enable sandbox mode (default: True)"
    )

    # Client ID for Login.gov
    client_id = models.CharField(
        verbose_name="Client ID (Issuer)",
        max_length=255,
        default=None,
        help_text="Client ID for Login.gov. "
        'In the Login.gov dashboard, this is called "Issuer" and will have the form '
        "<b>urn:gov:gsa:openidconnect.profiles:sp:sso:<i>agency_name</i>:<i>app_name</i></b>",
    )

    # Automatically create new users
    auto_create_users = models.BooleanField(
        default=False,
        help_text="Automatically create new Django users when logging in via Login.gov",
    )

    # Automatically link existing users
    auto_link_users = models.BooleanField(
        default=False,
        help_text="Automatically link existing Django users when logging in via Login.gov",
    )

    # Default groups for new or linked users
    default_group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Default group for new or linked users",
    )

    # OIDC auto configuration as JSON blob
    oidc_autoconfig = models.JSONField(
        null=True,
        blank=True,
        help_text="OIDC auto configuration as JSON blob",
        default=dict
    )

    # IAL level (single-value select)
    IAL_CHOICES = [
        ("auth-only", "Authentication only"),
        ("verified", "Verified, no facial matching"),
        ("verified-facial-match-preferred", "Verified, facial match preferred"),
        ("verified-facial-match-required", "Verified, facial match required"),
    ]
    ial_level = models.CharField(
        verbose_name="IAL Level",
        max_length=31,
        choices=IAL_CHOICES,
        default="auth-only",
        help_text="IAL level for authentication",
    )

    # AAL level (single-value select)
    AAL_CHOICES = [
        ("duo", "Require basic two-factor authentication"),
        ("separate", "Require separate second factor (i.e., not a remembered device)"),
        (
            "phishing_resistant",
            "Require a phishing resistant second factor (WebAuthn or PIV/CAC)",
        ),
        ("require_hspd12", "Require an HSPD12 credential (requires PIV/CAC)"),
    ]
    aal_level = models.CharField(
        verbose_name="AAL Level",
        max_length=50,
        choices=AAL_CHOICES,
        default="duo",
        help_text="AAL level for authentication",
    )

    VALID_SCOPES = [
        ("all_emails", "All emails"),
        ("locale", "Locale"),
        ("openid", "UUID"),
        ("x509", "X509 (all)"),
        ("x509:subject", "X509 subject"),
        ("x509:issuer", "X509 issuer"),
        ("x509:presented", "X509 present"),
        ("address", "Address"),
        ("phone", "Phone"),
        ("profile", "Profile (all)"),
        ("profile:name", "Profile - name (given, family)"),
        ("profile:birthdate", "Profile - birthdate"),
        ("profile:verified_at", "Profile - ID Verified At"),
        ("social_security_number", "Social Security Number")
    ]

    scopes = models.JSONField(
        verbose_name="Scopes",
        null=True,
        blank=True,
        default=dict,
        help_text="The scopes to request from Login.gov. " \
            "The <code>email</code> scope is always requested."
    )

    # Token expiration time in seconds
    token_expire = models.IntegerField(
        verbose_name="Token TTL",
        default=300,
        help_text="Token expiration time in seconds (default: 300)"
    )

    # Timestamp of last update
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        Return a string representation of the model instance.

        Returns:
            str: A human-readable string identifying the configuration
        """
        return "Login.gov Configuration"
