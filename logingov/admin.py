from django.contrib import admin
from django import forms
from .models import LoginGovSPSettings

# Register your models here.

class LoginGovConfigAdminForm(forms.ModelForm):
    """
    Custom form for LoginGovSPSettings to handle multi-select for scopes.

    This form extends Django's ModelForm to properly handle the JSONField
    'scopes' by converting it to a multiple choice field.

    Attributes:
        scopes_field: MultipleChoiceField for selecting scopes fields to request
    """

    # Define the scopes_field as a multiple choice field
    scopes_field = forms.MultipleChoiceField(
        choices=LoginGovSPSettings.VALID_SCOPES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Scopes to request from Login.gov"
    )

    class Meta:
        model = LoginGovSPSettings
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Initialize the form and load existing scopes values.

        Args:
            *args: Variable arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, **kwargs)
        # If there are existing values in scopes, load them for the form
        if self.instance.pk and self.instance.scopes:
            # For JSONField, directly assign the list
            self.fields['scopes_field'].initial = self.instance.scopes or []

    def save(self, commit=True):
        """
        Save the form data to the model instance.

        Args:
            commit: Boolean indicating whether to save to database immediately

        Returns:
            The saved model instance
        """
        # For JSONField, store the list directly
        scopes = self.cleaned_data.get('scopes_field', [])
        self.instance.scopes = scopes if scopes else None

        return super().save(commit)

class LoginGovConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for LoginGovSPSettings model.

    This admin configuration provides a user-friendly interface for managing
    Login.gov service provider settings in Django's admin panel.

    Attributes:
        form: The custom form to use for this admin interface
        list_display: Fields to display in the list view
        fieldsets: Organized groups of fields in the form view
    """
    form = LoginGovConfigAdminForm
    list_display = ['sandbox_mode', 'client_id', 'auto_create_users', 'default_group', 'updated_at']
    fieldsets = (
        ('Environment Settings', {
            'fields': ('sandbox_mode',)
        }),
        ('Client Configuration', {
            'fields': ('client_id',)
        }),
        ('User Management', {
            'fields': ('auto_create_users', 'auto_link_users', 'default_group')
        }),
        ('Authentication Levels', {
            'fields': ('ial_level', 'aal_level')
        }),
        ('Token Expiration', {
            'fields': ('token_expire',)
        }),
        ('Scopes', {
            'fields': ('scopes_field',)
        }),
    )

    # Make sure only one configuration exists
    def has_add_permission(self, request):
        """
        Check if a new configuration can be added.

        Only one configuration should exist, so prevent adding more than one.

        Args:
            request: The Django HttpRequest object

        Returns:
            Boolean indicating whether adding a new configuration is allowed
        """
        return not LoginGovSPSettings.objects.exists()

admin.site.register(LoginGovSPSettings, LoginGovConfigAdmin)
