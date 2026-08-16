"""
Role-based portal dispatcher view.
Directs authenticated users to their corresponding role portal dashboard.
"""

from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from apps.core.models import Role


class PortalDispatcherView(LoginRequiredMixin, View):
    """
    Central router that redirects users to their appropriate portal
    based on their assigned role.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        if user.is_administrator or user.role == Role.ADMINISTRATOR:
            return redirect('portal_admin:dashboard')
        elif user.is_teacher or user.role == Role.TEACHER:
            return redirect('portal:teacher_dashboard')
        elif user.is_student or user.role == Role.STUDENT:
            return redirect('portal:student_dashboard')

        # Fallback to home if no role matches
        return redirect('public:home')
