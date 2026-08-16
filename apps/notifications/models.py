"""
Notification models for Education Management Portal.
Provides priority-aware, deduplicated, and preference-filtered notifications.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import User, TimeStampedModel


class Notification(TimeStampedModel):
    """
    User notification generated deterministically from academic and system events.
    """
    class Priority(models.TextChoices):
        INFO = 'INFO', _('Information')
        SUCCESS = 'SUCCESS', _('Success')
        WARNING = 'WARNING', _('Warning')
        CRITICAL = 'CRITICAL', _('Critical')

    class NotificationType(models.TextChoices):
        ATTENDANCE_WARNING = 'ATTENDANCE_WARNING', _('Attendance Warning')
        ASSIGNMENT_DEADLINE = 'ASSIGNMENT_DEADLINE', _('Assignment Deadline')
        ASSIGNMENT_OVERDUE = 'ASSIGNMENT_OVERDUE', _('Assignment Overdue')
        GRADE_PUBLISHED = 'GRADE_PUBLISHED', _('Grade Published')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Course Announcement')
        INTERVENTION_ASSIGNED = 'INTERVENTION_ASSIGNED', _('Support Plan Assigned')
        INTERVENTION_ACTION_DUE = 'INTERVENTION_ACTION_DUE', _('Support Action Due')
        INTERVENTION_OVERDUE = 'INTERVENTION_OVERDUE', _('Support Action Overdue')
        RISK_ESCALATION = 'RISK_ESCALATION', _('Risk Escalation Alert')
        ACUTE_ANOMALY = 'ACUTE_ANOMALY', _('Acute Performance Anomaly')
        SYSTEM_ALERT = 'SYSTEM_ALERT', _('System Alert')
        DIGEST_SUMMARY = 'DIGEST_SUMMARY', _('Periodic Academic Digest')

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('recipient')
    )
    notification_type = models.CharField(
        _('notification type'),
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM_ALERT,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=Priority.choices,
        default=Priority.INFO,
        db_index=True
    )
    title = models.CharField(_('title'), max_length=255)
    message = models.TextField(_('message'))
    link_url = models.CharField(_('link URL'), max_length=500, blank=True)
    is_read = models.BooleanField(_('is read'), default=False, db_index=True)
    read_at = models.DateTimeField(_('read timestamp'), null=True, blank=True)
    event_hash = models.CharField(
        _('deduplication event hash'),
        max_length=64,
        db_index=True,
        help_text=_('SHA-256 hash preventing duplicate notifications for the same trigger event.')
    )

    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.priority}] {self.recipient.email} - {self.title}"

    def mark_as_read(self):
        """Marks notification as read with timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def badge_class(self):
        mapping = {
            self.Priority.CRITICAL: 'badge-danger',
            self.Priority.WARNING: 'badge-warning',
            self.Priority.SUCCESS: 'badge-success',
            self.Priority.INFO: 'badge-info',
        }
        return mapping.get(self.priority, 'badge-neutral')


class NotificationPreference(TimeStampedModel):
    """
    User notification preferences.
    Critical academic safety alerts remain enforced regardless of preference toggles.
    """
    class DigestFrequency(models.TextChoices):
        DAILY = 'DAILY', _('Daily Summary')
        WEEKLY = 'WEEKLY', _('Weekly Summary')
        NONE = 'NONE', _('No Digest')

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('user')
    )
    enable_academic_alerts = models.BooleanField(
        _('enable academic & risk alerts'),
        default=True,
        help_text=_('Critical academic safety alerts are mandatory and cannot be disabled.')
    )
    enable_assignment_reminders = models.BooleanField(_('enable assignment reminders'), default=True)
    enable_attendance_warnings = models.BooleanField(_('enable attendance warnings'), default=True)
    enable_intervention_updates = models.BooleanField(_('enable support plan updates'), default=True)
    enable_ai_insights = models.BooleanField(_('enable AI periodic summaries'), default=True)
    enable_announcements = models.BooleanField(_('enable course announcements'), default=True)
    digest_frequency = models.CharField(
        _('digest frequency'),
        max_length=20,
        choices=DigestFrequency.choices,
        default=DigestFrequency.DAILY
    )

    class Meta:
        verbose_name = _('notification preference')
        verbose_name_plural = _('notification preferences')

    def __str__(self):
        return f"Notification Preferences: {self.user.email}"

    @classmethod
    def get_for_user(cls, user: User) -> 'NotificationPreference':
        """Retrieves or creates user preferences."""
        pref, _ = cls.objects.get_or_create(user=user)
        return pref
