from django import template
from django.utils import translation

register = template.Library()

@register.inclusion_tag('logingov/login_button.html', takes_context=True)
def logingov_button(context, button_style="primary", big=False, extra_classes=""):
    language = translation.get_language()

    allowed_styles = [
        "primary",
        "primary-lighter",
        "primary-darker"
    ]

    # Language-specific order mapping.
    logo_first_languages = ["jp"]

    # Defaults
    logo_size = { "width": "7.4rem", "height": "1rem"}
    lg_logo = "login_gov_logo.svg"

    # Build button classes
    if button_style not in allowed_styles:
        button_style = "primary"

    if button_style == "primary-darker":
        lg_logo = "login_gov_logo-white.svg"

    button_classes = ["usa-button", "login-button", f"login-button--{button_style}" ]

    if big:
        button_classes.append("usa-button--big")
        logo_size = {"width": "11.1rem", "height": "1.5rem"}

    if extra_classes:
        button_classes.extend(extra_classes.split())

    return {
        'logo_first': language in logo_first_languages,
        'button_classes': ' '.join(sorted(button_classes)),
        'button-style': button_style,
        'logo_file': lg_logo,
        'logo_size': logo_size
    }
