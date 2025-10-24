from django.urls import path

from . import views


app_name = 'logingov'

urlpatterns = [
    path('auth', views.AuthCloudView.as_view(), name='auth_cloud'), # Redirect URL
    path('logout', views.LogoutView.as_view(), name='logout_user'),
    path('login', views.LoginGovRedirectView.as_view(), name='login_gov_redirect'),
    path('refresh-session', views.RefreshSessionView.as_view(), name='refresh_session'),
]
