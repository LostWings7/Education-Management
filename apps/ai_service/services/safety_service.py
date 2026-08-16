"""
Safety, Sanitization & Feedback Service.
Enforces defense-in-depth sanitization and records user feedback without modifying academic data.
"""

from typing import Optional
from django.core.exceptions import PermissionDenied, ValidationError
from apps.core.models import User
from apps.ai_service.models import AIMessage, AIMessageFeedback


class SafetyService:
    """
    Manages safety checks, untrusted text boundaries, and feedback collection.
    """

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """
        Escapes special characters and ensures boundary delimiters cannot be closed.
        """
        if not text:
            return ""
        # Remove literal XML closing tags to prevent boundary escaping
        sanitized = text.replace("</academic_data_context>", "&lt;/academic_data_context&gt;")
        sanitized = sanitized.replace("<system_instruction>", "&lt;system_instruction&gt;")
        return sanitized

    @classmethod
    def record_user_feedback(
        cls,
        message: AIMessage,
        user: User,
        is_helpful: bool,
        category: str = '',
        comments: str = ''
    ) -> AIMessageFeedback:
        """
        Records user feedback (👍 / 👎) with optional categorization.
        Only the owner of the conversation can submit feedback.
        """
        if message.conversation.user != user:
            raise PermissionDenied("Cannot submit feedback on another user's conversation.")

        feedback, _ = AIMessageFeedback.objects.update_or_create(
            message=message,
            defaults={
                'is_helpful': is_helpful,
                'category': category,
                'comments': comments.strip()
            }
        )
        return feedback
