from django.apps import AppConfig


class LoginGovConfig(AppConfig):
    """
    Django AppConfig for the Login.gov authentication application.

    This configuration defines the application's behavior and metadata within
    the Django project, including default field types, app name, and human-readable
    verbose name.

    Attributes:
        default_auto_field: The default field type for auto-generated primary keys
        name: The internal name of the Django app
        verbose_name: A human-readable name for the app
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logingov'
    verbose_name = 'Login.gov OIDC Authentication'
