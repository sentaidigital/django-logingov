from django.urls import path

from . import views


app_name = 'logingov'

urlpatterns = [
    path('auth', views.get_token, name='auth_cloud'), # Redirect URL
    path('logout', views.logout_user, name='logout_user'),
    path('login', views.LoginGovRedirectView.as_view(), name='login-gov-redirect'),
    path('refresh-session', views.refresh_session, name='refresh_session'),
]
