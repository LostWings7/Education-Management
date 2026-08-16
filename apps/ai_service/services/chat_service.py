"""
Conversational Chat Service.
Manages persistent conversation sessions, sliding memory window, fresh context injection, and privacy.
"""

import time
from typing import Optional, List
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from apps.core.models import User
from apps.academic.models import StudentProfile, TeacherProfile
from apps.ai_service.models import AIConversation, AIMessage, AIInteractionLog
from apps.ai_service.schemas.messages import ChatMessage
from apps.ai_service.schemas.responses import StructuredAIResponse
from apps.ai_service.providers.factory import get_ai_provider
from apps.ai_service.context.student_context import StudentContextBuilder
from apps.ai_service.context.teacher_context import TeacherContextBuilder
from apps.ai_service.context.admin_context import AdminContextBuilder
from apps.ai_service.prompts.system_base import (
    STUDENT_SYSTEM_PROMPT,
    TEACHER_SYSTEM_PROMPT,
    ADMIN_SYSTEM_PROMPT
)


class ChatService:
    """
    Coordinates conversational turns with authentic pre-prompt context injection.
    """

    @classmethod
    def get_or_create_conversation(
        cls,
        user: User,
        conversation_id: Optional[int] = None,
        title: str = "Academic Advisory Session"
    ) -> AIConversation:
        """
        Retrieves existing conversation with ownership validation, or creates a new one.
        """
        if conversation_id:
            conv = AIConversation.objects.filter(pk=conversation_id, user=user).first()
            if conv:
                return conv
            raise PermissionDenied("Conversation not found or unauthorized.")

        return AIConversation.objects.create(
            user=user,
            role=getattr(user, 'role', 'STUDENT'),
            title=title
        )

    @classmethod
    def send_user_message(
        cls,
        conversation: AIConversation,
        user: User,
        message_text: str
    ) -> AIMessage:
        """
        Processes a user turn, injects fresh authoritative context, calls AI provider,
        and records the response.
        """
        if conversation.user != user:
            raise PermissionDenied("Unauthorized access to conversation.")

        t0 = time.time()

        # 1. Record user turn
        user_msg = AIMessage.objects.create(
            conversation=conversation,
            sender=AIMessage.SenderType.USER,
            content=message_text.strip()
        )

        # 2. Build fresh role-scoped context (live database state always wins)
        if user.is_student:
            student = getattr(user, 'student_profile', None)
            context_obj = StudentContextBuilder.build_context(student)
            system_prompt = STUDENT_SYSTEM_PROMPT
            role_str = "STUDENT"
        elif user.is_teacher:
            teacher = getattr(user, 'teacher_profile', None)
            context_obj = TeacherContextBuilder.build_context(teacher)
            system_prompt = TEACHER_SYSTEM_PROMPT
            role_str = "TEACHER"
        else:
            context_obj = AdminContextBuilder.build_context()
            system_prompt = ADMIN_SYSTEM_PROMPT
            role_str = "ADMINISTRATOR"

        # 3. Assemble sliding window history (last 6 messages = 3 full turns)
        history_msgs = list(conversation.messages.order_by('created_at'))
        recent_msgs = history_msgs[-6:]

        chat_messages: List[ChatMessage] = []
        if conversation.summary:
            chat_messages.append(ChatMessage(
                role="system",
                content=f"Summary of previous discussion: {conversation.summary}"
            ))

        for m in recent_msgs:
            chat_messages.append(ChatMessage(
                role="user" if m.sender == AIMessage.SenderType.USER else "assistant",
                content=m.content
            ))

        # 4. Invoke AI provider
        provider = get_ai_provider()
        ai_response: StructuredAIResponse = provider.chat(
            system_instruction=system_prompt,
            messages=chat_messages,
            context_data=context_obj.__dict__
        )

        # 5. Record assistant turn with structured payload for Evidence Inspector
        structured_payload = {
            'facts_used': [f.__dict__ for f in ai_response.facts_used],
            'calculations_used': [f.__dict__ for f in ai_response.calculations_used],
            'simulations_used': [f.__dict__ for f in ai_response.simulations_used],
            'actions_used': [f.__dict__ for f in ai_response.actions_used],
            'interpretations': ai_response.interpretations,
            'recommendations': ai_response.recommendations,
            'provider': ai_response.provider,
            'model': ai_response.model,
            'validation_status': ai_response.validation_status,
            'disclaimer': ai_response.disclaimer
        }

        assistant_msg = AIMessage.objects.create(
            conversation=conversation,
            sender=AIMessage.SenderType.ASSISTANT,
            content=ai_response.content,
            structured_payload=structured_payload,
            token_count=ai_response.token_count
        )

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])

        latency = int((time.time() - t0) * 1000)
        AIInteractionLog.objects.create(
            user=user,
            role=role_str,
            request_type="CHAT",
            provider=ai_response.provider,
            model=ai_response.model,
            prompt_version="chat_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=ai_response.validation_status
        )

        return assistant_msg

    @classmethod
    def delete_conversation(cls, conversation: AIConversation, user: User) -> bool:
        """
        Deletes a conversation ensuring ownership.
        """
        if conversation.user != user and not (user.is_administrator or user.is_superuser):
            raise PermissionDenied("Cannot delete another user's conversation.")

        conversation.delete()
        return True

    @classmethod
    def clear_messages(cls, conversation: AIConversation, user: User) -> bool:
        """
        Clears message history for a conversation.
        """
        if conversation.user != user and not (user.is_administrator or user.is_superuser):
            raise PermissionDenied("Cannot clear another user's conversation.")

        conversation.messages.all().delete()
        conversation.summary = ""
        conversation.save(update_fields=['summary'])
        return True
