"""
Student AI Copilot Views and API Endpoints.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from apps.core.mixins import StudentRequiredMixin
from apps.ai_service.models import AIConversation, AIMessage
from apps.ai_service.services import (
    ChatService,
    StudyPlannerService,
    ExplanationService,
    SafetyService
)


class StudentAICopilotView(StudentRequiredMixin, View):
    """
    Main Student AI Copilot conversational portal interface.
    """
    template_name = 'portal/student/ai/copilot.html'

    def get(self, request):
        student = request.user.student_profile
        conversation_id = request.GET.get('conversation_id')

        # Get or create active conversation
        conv = None
        if conversation_id:
            conv = AIConversation.objects.filter(pk=conversation_id, user=request.user).first()
        if not conv:
            conv = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at').first()
        if not conv:
            conv = ChatService.get_or_create_conversation(request.user, title="Academic Copilot Session")

        conversations = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at')
        chat_messages = conv.messages.all().order_by('created_at')

        suggested_prompts = [
            "Why is my current academic risk level what it is?",
            "What should I focus on studying this week?",
            "Explain my attendance standing and absence buffer.",
            "What are my weakest syllabus topics across my courses?",
            "Explain my active support plan and next steps."
        ]

        return render(request, self.template_name, {
            'student': student,
            'active_conversation': conv,
            'conversations': conversations,
            'chat_messages': chat_messages,
            'suggested_prompts': suggested_prompts
        })


class StudentAIChatAPIView(StudentRequiredMixin, View):
    """
    Asynchronous JSON chat endpoint.
    """
    def post(self, request):
        message_text = request.POST.get('message', '').strip()
        conv_id = request.POST.get('conversation_id')

        if not message_text:
            return JsonResponse({'error': 'Message content cannot be empty.'}, status=400)

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


class StudentAIStudyPlannerView(StudentRequiredMixin, View):
    """
    Student Study Planner Page.
    """
    template_name = 'portal/student/ai/planner.html'

    def get(self, request):
        student = request.user.student_profile
        plan = StudyPlannerService.generate_plan_for_student(student)

        return render(request, self.template_name, {
            'student': student,
            'study_plan': plan
        })


class StudentAIExplanationAPIView(StudentRequiredMixin, View):
    """
    Generates contextual explanation for an insight.
    """
    def post(self, request):
        subject = request.POST.get('subject', 'Academic Insight')
        evidence_str = request.POST.get('evidence', '')

        student = request.user.student_profile
        resp = ExplanationService.explain_insight(
            user=request.user,
            subject=subject,
            evidence={'evidence': evidence_str},
            student=student
        )

        return JsonResponse({
            'success': True,
            'explanation': resp.content,
            'facts_used': [f.__dict__ for f in resp.facts_used],
            'calculations_used': [f.__dict__ for f in resp.calculations_used],
            'simulations_used': [f.__dict__ for f in resp.simulations_used],
            'actions_used': [f.__dict__ for f in resp.actions_used],
            'interpretations': resp.interpretations,
            'recommendations': resp.recommendations,
            'disclaimer': resp.disclaimer
        })


class StudentAIFeedbackAPIView(StudentRequiredMixin, View):
    """
    Collects user response feedback (👍 / 👎).
    """
    def post(self, request):
        msg_id = request.POST.get('message_id')
        is_helpful = request.POST.get('is_helpful') == 'true'
        category = request.POST.get('category', '')
        comments = request.POST.get('comments', '')

        msg = get_object_or_404(AIMessage, pk=msg_id)
        feedback = SafetyService.record_user_feedback(
            message=msg,
            user=request.user,
            is_helpful=is_helpful,
            category=category,
            comments=comments
        )

        return JsonResponse({'success': True, 'feedback_id': feedback.pk})


class StudentAIDeleteConversationView(StudentRequiredMixin, View):
    """
    Deletes an existing conversation session.
    """
    def post(self, request, pk):
        conv = get_object_or_404(AIConversation, pk=pk)
        ChatService.delete_conversation(conv, request.user)
        messages.success(request, "Conversation deleted.")
        return redirect('portal:student_ai_copilot')
