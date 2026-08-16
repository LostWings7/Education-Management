"""
Administrator AI Intelligence & Institutional Briefing Views.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from apps.core.mixins import AdminRequiredMixin
from apps.ai_service.models import AIConversation, AIMessage
from apps.ai_service.services import (
    ChatService,
    BriefingService,
    SafetyService
)


class AdminAIIntelligenceView(AdminRequiredMixin, View):
    """
    Administrator AI Intelligence Hub and Institutional Briefing.
    """
    template_name = 'portal/admin/ai/intelligence.html'

    def get(self, request):
        briefing = BriefingService.generate_institutional_briefing(request.user)
        conversation_id = request.GET.get('conversation_id')

        conv = None
        if conversation_id:
            conv = AIConversation.objects.filter(pk=conversation_id, user=request.user).first()
        if not conv:
            conv = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at').first()
        if not conv:
            conv = ChatService.get_or_create_conversation(request.user, title="Institutional Intelligence Session")

        conversations = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at')
        chat_messages = conv.messages.all().order_by('created_at')

        suggested_prompts = [
            "Summarize overall institutional academic health and attendance.",
            "Which academic departments show the highest density of high-risk students?",
            "What are the primary curricular friction courses across the university?",
            "Summarize the effectiveness and ROI of evaluated student support plans."
        ]

        return render(request, self.template_name, {
            'briefing': briefing,
            'active_conversation': conv,
            'conversations': conversations,
            'chat_messages': chat_messages,
            'suggested_prompts': suggested_prompts
        })


class AdminAIChatAPIView(AdminRequiredMixin, View):
    """
    Asynchronous JSON chat endpoint for administrators.
    """
    def post(self, request):
        message_text = request.POST.get('message', '').strip()
        conv_id = request.POST.get('conversation_id')

        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        conv = ChatService.get_or_create_conversation(request.user, conversation_id=int(conv_id) if conv_id else None)
        assistant_msg = ChatService.send_user_message(conv, request.user, message_text)

        return JsonResponse({
            'success': True,
            'conversation_id': conv.pk,
            'user_message': message_text,
            'assistant_message_id': assistant_msg.pk,
            'assistant_message': assistant_msg.content,
            'structured_payload': assistant_msg.structured_payload,
            'created_at': assistant_msg.created_at.strftime("%H:%M")
        })


class AdminAIObservabilityView(AdminRequiredMixin, View):
    """
    Administrator AI Health, Telemetry & User Feedback Analytics.
    """
    template_name = 'portal/admin/ai/observability.html'

    def get(self, request):
        from apps.ai_service.services.observability_service import AIObservabilityService
        metrics = AIObservabilityService.get_observability_metrics()
        return render(request, self.template_name, {
            'metrics': metrics
        })
