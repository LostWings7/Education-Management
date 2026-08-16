"""
Role-based access control decorators for function-based views.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from .models import Role


def role_required(allowed_roles):
    """
    Decorator for views that checks whether the user is logged in
    and has one of the required roles.

    :param allowed_roles: A single Role or a list/tuple of Roles.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={request.path}")

            # Administrators / Superusers always have overarching access to all views if needed,
            # or strictly check the role
            user_role = getattr(request.user, 'role', None)
            if request.user.is_superuser or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Deny access if user does not possess required role
            raise PermissionDenied(
                "You do not have permission to access this portal."
            )

        return _wrapped_view

    return decorator


def student_required(view_func):
    """Decorator to require Student role."""
    return role_required([Role.STUDENT])(view_func)


def teacher_required(view_func):
    """Decorator to require Teacher role."""
    return role_required([Role.TEACHER])(view_func)


def admin_required(view_func):
    """Decorator to require Administrator role or superuser."""
    return role_required([Role.ADMINISTRATOR])(view_func)
