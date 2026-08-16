"""
Core models for Education Management Portal.
Handles identity, custom User, roles, and audit logging.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .managers import UserManager


class Role(models.TextChoices):
    """
    System user roles. Extensible for future roles (HOD, Coordinator).
    """
    ADMINISTRATOR = 'ADMINISTRATOR', _('Administrator')
    TEACHER = 'TEACHER', _('Teacher')
    STUDENT = 'STUDENT', _('Student')


class TimeStampedModel(models.Model):
    """
    Abstract base model providing self-updating created_at and updated_at fields.
    """
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        abstract = True


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model where email is the unique identifier for authentication.
    Domain-specific academic details are delegated to StudentProfile / TeacherProfile.
    """
    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        db_index=True,
        error_messages={
            'unique': _('A user with that email address already exists.'),
        }
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True
    )
    phone_number = models.CharField(_('phone number'), max_length=20, blank=True)
    avatar = models.ImageField(
        _('avatar'),
        upload_to='avatars/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into the Django admin site.'),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.email})"
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0]

    @property
    def is_student(self):
        """Check if user has student role."""
        return self.role == Role.STUDENT

    @property
    def is_teacher(self):
        """Check if user has teacher role."""
        return self.role == Role.TEACHER

    @property
    def is_administrator(self):
        """Check if user has administrator role or superuser status."""
        return self.role == Role.ADMINISTRATOR or self.is_superuser

    @property
    def role_badge_class(self):
        """Return styling badge class for UI representation."""
        mapping = {
            Role.ADMINISTRATOR: 'badge-admin',
            Role.TEACHER: 'badge-teacher',
            Role.STUDENT: 'badge-student',
        }
        return mapping.get(self.role, 'badge-secondary')


class AuditLog(TimeStampedModel):
    """
    Audit logging for security events and critical administrative actions.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('user')
    )
    action = models.CharField(_('action'), max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    details = models.JSONField(_('details'), default=dict, blank=True)

    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.email if self.user else 'System/Anonymous'
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action}"

    @classmethod
    def log_action(cls, user, action, request=None, details=None):
        """Helper to create an audit log entry cleanly."""
        ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

        return cls.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            action=action,
            ip_address=ip,
            details=details or {}
        )
