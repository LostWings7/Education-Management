"""
Custom user manager for email-based authentication.
"""

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, role=None, **extra_fields):
        """
        Create and save a User with the given email, password, and role.
        """
        if not email:
            raise ValueError(_('The Email field must be set'))

        email = self.normalize_email(email).lower()

        # Import here to avoid circular dependencies
        from .models import Role

        if role is None:
            role = Role.STUDENT

        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, role=role, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        from .models import Role

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        role = extra_fields.pop('role', Role.ADMINISTRATOR)
        return self.create_user(
            email=email,
            password=password,
            role=role,
            **extra_fields
        )
