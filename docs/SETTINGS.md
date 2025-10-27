## Example Settings

The configuration can be set up in the administration section of your project,
with a couple key exceptions. The private key must be configured in the 
environment as a PEM-formatted file (`LOGIN_GOV_PRIVATE_KEY_FILE`) or
as the PEM-formatted key itself (`LOGIN_GOV_PRIVATE_KEY_PEM`)

```python
# Boolean flag to enable sandbox mode (default: True)
LOGIN_GOV_SANDBOX_MODE = True

# Client ID, called the Issuer in the Login.gov Portal
LOGIN_GOV_CLIENT_ID = "urn:gov:gsa:openidconnect.profiles:sp:sso:agency_name:app_name"

# LOGIN_GOV_AAL_LEVEL - AAL level (default: 'duo'). Possible values:
#  - 'duo'
#  - 'separate'
#  - 'phishing_resistant'
#  - 'require_hspd12'
LOGIN_GOV_AAL_LEVEL = "phishing_resistant"

# `LOGIN_GOV_IAL_LEVEL` - IAL level (default: 'auth-only'). Possible values:
#  - 'auth-only'
#  - 'verified'
#  - 'verified-facial-match-preferred'
#  - 'verified-facial-match-required'
LOGIN_GOV_IAL_LEVEL = "verified"

# Token expiration time in seconds (default: 300)
LOGIN_GOV_TOKEN_EXPIR = 300

# List of userinfo fields to include (default: empty list)
# The email scope is always included.
LOGIN_GOV_SCOPES = [
    "all_emails",
    "locale",
    "openid",
    "profile:verified_at",
    "address",
    "phone",
    "profile",
    "profile:name",
    "profile:birthdate",
    "social_security_number",
    "x509",
    "x509:subject",
    "x509:issuer",
    "x509:presented"
]

## Private Key Configuration
# Path to PEM file (environment or settings variable)
LOGIN_GOV_PRIVATE_KEY_FILE = "config/private.pem"

# User Management
# Boolean to enable automatic user creation (default: False)
LOGIN_GOV_AUTO_CREATE_USERS = True

# Boolean to enable automatic user linking (default: False)
LOGIN_GOV_AUTO_LINK_USERS = True

# Default group ID for new users (default: None)
LOGIN_GOV_DEFAULT_GROUP = 1

```
