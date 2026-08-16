"""
Domain models for Phase 5 AI Academic Intelligence Layer.
Provides conversation persistence, privacy-conscious metadata logging, and user feedback.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel, User, Role


class AIConversation(TimeStampedModel):
    """
    Persistent conversational session with role and context scope metadata.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name=_('user')
    )
    role = models.CharField(
        _('user role'),
        max_length=20,
        choices=Role.choices
    )
    title = models.CharField(
        _('conversation title'),
        max_length=255,
        default="Academic Advisory Session"
    )
    context_scope = models.JSONField(
        _('context scope metadata'),
        default=dict,
        blank=True,
        help_text=_('UI filter metadata only. Never trusted as an authorization bypass.')
    )
    summary = models.TextField(
        _('compressed conversation summary'),
        blank=True,
        default=""
    )
    is_archived = models.BooleanField(
        _('archived status'),
        default=False
    )

    class Meta:
        verbose_name = _('AI Conversation')
        verbose_name_plural = _('AI Conversations')
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.role}] {self.user.email} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"


class AIMessage(models.Model):
    """
    Individual turn within an AI conversation.
    """
    class SenderType(models.TextChoices):
        USER = 'USER', _('User')
        ASSISTANT = 'ASSISTANT', _('AI Academic Assistant')
        SYSTEM = 'SYSTEM', _('System Instructions')
        TOOL = 'TOOL', _('Deterministic Tool Result')

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('conversation')
    )
    sender = models.CharField(
        _('sender type'),
        max_length=20,
        choices=SenderType.choices,
        default=SenderType.USER
    )
    content = models.TextField(_('message content'))
    structured_payload = models.JSONField(
        _('structured response payload'),
        default=dict,
        blank=True,
        help_text=_('Contains fact attribution, calculations, simulations, actions, and validation status.')
    )
    token_count = models.PositiveIntegerField(_('estimated tokens'), default=0)
    created_at = models.DateTimeField(_('timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI Message')
        verbose_name_plural = _('AI Messages')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} in conv #{self.conversation_id}: {self.content[:40]}..."


class AIMessageFeedback(TimeStampedModel):
    """
    User response quality feedback (Helpful 👍 / 👎) with optional categorization.
    Stored strictly as quality metadata; never alters academic records.
    """
    class FeedbackCategory(models.TextChoices):
        INCORRECT_INFO = 'INCORRECT_INFO', _('Incorrect Information')
        NOT_RELEVANT = 'NOT_RELEVANT', _('Not Relevant')
        TOO_VAGUE = 'TOO_VAGUE', _('Too Vague')
        MISSING_CONTEXT = 'MISSING_CONTEXT', _('Missing Context')
        OTHER = 'OTHER', _('Other')

    message = models.OneToOneField(
        AIMessage,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name=_('AI message')
    )
    is_helpful = models.BooleanField(_('helpful'))
    category = models.CharField(
        _('feedback category'),
        max_length=30,
        choices=FeedbackCategory.choices,
        blank=True,
        default=''
    )
    comments = models.TextField(_('user comments'), blank=True, default='')

    class Meta:
        verbose_name = _('AI Message Feedback')
        verbose_name_plural = _('AI Message Feedbacks')

    def __str__(self):
        status = "Helpful" if self.is_helpful else "Unhelpful"
        return f"Feedback ({status}) on msg #{self.message_id}"


class AIInteractionLog(models.Model):
    """
    Privacy-conscious operational telemetry and observability log.
    Stores operational metadata only; NEVER stores raw user text or sensitive academic narratives.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_interaction_logs',
        verbose_name=_('user')
    )
    role = models.CharField(_('role'), max_length=20)
    request_type = models.CharField(_('request type'), max_length=50) # CHAT, EXPLANATION, STUDY_PLAN, CLASS_BRIEFING, EXEC_BRIEFING
    provider = models.CharField(_('AI provider'), max_length=50)
    model = models.CharField(_('model identifier'), max_length=100)
    prompt_version = models.CharField(_('prompt version'), max_length=50)
    latency_ms = models.PositiveIntegerField(_('latency ms'), default=0)
    success = models.BooleanField(_('success status'), default=True)
    validation_status = models.CharField(_('validation status'), max_length=50, default='VALID')
    error_code = models.CharField(_('error code'), max_length=100, blank=True, default='')
    created_at = models.DateTimeField(_('timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI Interaction Log')
        verbose_name_plural = _('AI Interaction Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.provider}/{self.model}] {self.request_type} by {self.role} ({self.latency_ms}ms, {self.validation_status})"
