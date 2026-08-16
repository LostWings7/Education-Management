"""
Core URL routing for authentication and profile management.
"""

from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    StudentRegisterView,
    ProfileView,
    PasswordChangeView
)

app_name = 'core'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', StudentRegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),
]
