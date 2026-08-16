"""
Core authentication, registration, and profile views.
"""

from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import View, FormView, UpdateView
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import User, Role, AuditLog
from .forms import (
    LoginForm,
    StudentRegistrationForm,
    UserProfileForm,
    PasswordChangeCustomForm
)


class LoginView(FormView):
    """
    Handles user login using email and password.
    """
    template_name = 'core/login.html'
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('portal:dispatcher')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.get_user()
        remember_me = form.cleaned_data.get('remember_me', False)

        login(self.request, user)

        if not remember_me:
            # Session expires on browser close
            self.request.session.set_expiry(0)
        else:
            # 2 weeks expiry
            self.request.session.set_expiry(1209600)

        AuditLog.log_action(
            user=user,
            action='USER_LOGIN',
            request=self.request,
            details={'role': user.role}
        )

        messages.success(self.request, f"Welcome back, {user.get_short_name()}!")

        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        return redirect('portal:dispatcher')


class LogoutView(View):
    """
    Handles user logout with audit logging.
    """
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            AuditLog.log_action(
                user=request.user,
                action='USER_LOGOUT',
                request=request
            )
            logout(request)
            messages.info(request, "You have been logged out successfully.")
        return redirect('core:login')


class StudentRegisterView(FormView):
    """
    Public registration endpoint for students.
    Role is strictly hardcoded to STUDENT.
    """
    template_name = 'core/register.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('portal:dispatcher')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('portal:dispatcher')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()

        # Log audit entry
        AuditLog.log_action(
            user=user,
            action='STUDENT_REGISTRATION',
            request=self.request,
            details={'email': user.email}
        )

        # Log user in automatically
        login(self.request, user)
        messages.success(
            self.request,
            "Your student account has been created successfully! Welcome to the portal."
        )
        return redirect(self.success_url)


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Allows authenticated users to view and update their personal details.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'core/profile.html'
    success_url = reverse_lazy('core:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile details have been updated successfully.")
        AuditLog.log_action(
            user=self.request.user,
            action='PROFILE_UPDATE',
            request=self.request
        )
        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixin, FormView):
    """
    Allows authenticated users to change their password.
    """
    template_name = 'core/password_change.html'
    form_class = PasswordChangeCustomForm
    success_url = reverse_lazy('core:profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Your password has been changed successfully. Please keep it safe."
        )
        AuditLog.log_action(
            user=self.request.user,
            action='PASSWORD_CHANGE',
            request=self.request
        )
        return redirect(self.success_url)
