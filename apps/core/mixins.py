"""
Role-based access control mixins for Class-Based Views.
"""

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from .models import Role


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin that verifies the authenticated user possesses one of the allowed roles.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user_role = getattr(request.user, 'role', None)
        if request.user.is_superuser or user_role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("You do not have permission to access this portal.")


class StudentRequiredMixin(RoleRequiredMixin):
    """CBV mixin requiring Student role."""
    allowed_roles = [Role.STUDENT]


class TeacherRequiredMixin(RoleRequiredMixin):
    """CBV mixin requiring Teacher role."""
    allowed_roles = [Role.TEACHER]


class AdminRequiredMixin(RoleRequiredMixin):
    """CBV mixin requiring Administrator role."""
    allowed_roles = [Role.ADMINISTRATOR]
