# Login.gov Integration

This app provides integration with Login.gov for authentication.

## Models

### LoginGovSPSettings
Django model representing Login.gov Service Provider settings.

This model stores configuration parameters required for integrating with
the Login.gov OpenID Connect service provider. It includes settings for
authentication modes, client configuration, user management, and
authentication levels (IAL and AAL).

#### Fields:
- `sandbox_mode`: Boolean indicating if sandbox mode is enabled
- `client_id`: The client ID for Login.gov authentication
- `auto_create_users`: Boolean indicating if new users should be created automatically
- `auto_link_users`: Boolean indicating if existing users should be linked automatically
- `default_group`: Default Django group for new or linked users
- `oidc_autoconfig`: JSON field storing OIDC auto configuration
- `ial_level`: Identity Assurance Level setting
- `aal_level`: Authenticator Assurance Level setting
- `userinfo_fields`: JSON field storing requested userinfo fields
- `token_expire`: Token expiration time in seconds (default: 300)
- `updated_at`: Timestamp of last update

## Admin Interface
The Django admin interface provides a user-friendly way to manage Login.gov service provider settings.

### Configuration:
- Environment Settings: `sandbox_mode`
- Client Configuration: `client_id`
- User Management: `auto_create_users`, `auto_link_users`, `default_group`
- Authentication Levels: `ial_level`, `aal_level`
- Userinfo Fields: `userinfo_fields`
- Token Expiration: `token_expire` (default: 300 seconds)
