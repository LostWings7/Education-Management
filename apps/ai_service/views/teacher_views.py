"""
Teacher AI Copilot & Briefing Views.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from apps.core.mixins import TeacherRequiredMixin
from apps.academic.models import ClassSection, StudentProfile
from apps.ai_service.models import AIConversation, AIMessage
from apps.ai_service.services import (
    ChatService,
    BriefingService,
    SafetyService
)


class TeacherAICopilotView(TeacherRequiredMixin, View):
    """
    Teacher Academic Copilot Interface.
    """
    template_name = 'portal/teacher/ai/copilot.html'

    def get(self, request):
        teacher = request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher, semester__is_active=True).select_related('course')
        conversation_id = request.GET.get('conversation_id')

        conv = None
        if conversation_id:
            conv = AIConversation.objects.filter(pk=conversation_id, user=request.user).first()
        if not conv:
            conv = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at').first()
        if not conv:
            conv = ChatService.get_or_create_conversation(request.user, title="Faculty Teaching Assistant Session")

        conversations = AIConversation.objects.filter(user=request.user, is_archived=False).order_by('-updated_at')
        chat_messages = conv.messages.all().order_by('created_at')

        suggested_prompts = [
            "Which students in my classes require immediate academic attention?",
            "Summarize the overall performance and attendance health of my sections.",
            "What syllabus topics currently show the weakest class-wide mastery scores?",
            "Show me overdue intervention support plans across my teaching sections."
        ]

        return render(request, self.template_name, {
            'teacher': teacher,
            'sections': sections,
            'active_conversation': conv,
            'conversations': conversations,
            'chat_messages': chat_messages,
            'suggested_prompts': suggested_prompts
        })


class TeacherAIChatAPIView(TeacherRequiredMixin, View):
    """
    Asynchronous JSON chat endpoint for teachers.
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


class TeacherClassBriefingView(TeacherRequiredMixin, View):
    """
    Dedicated Pre-Class Executive Briefing for a specific teaching section.
    """
    template_name = 'portal/teacher/ai/class_briefing.html'

    def get(self, request, section_id):
        teacher = request.user.teacher_profile
        sec = get_object_or_404(ClassSection.objects.select_related('course'), pk=section_id, primary_teacher=teacher)
        briefing = BriefingService.generate_class_briefing(teacher, sec.pk)

        return render(request, self.template_name, {
            'teacher': teacher,
            'section': sec,
            'briefing': briefing
        })


class TeacherStudentBriefingAPIView(TeacherRequiredMixin, View):
    """
    Generates confidential 1-on-1 student briefing for teacher advising.
    """
    def post(self, request):
        section_id = request.POST.get('section_id')
        student_id = request.POST.get('student_id')

        teacher = request.user.teacher_profile
        briefing = BriefingService.generate_student_briefing_for_teacher(
            teacher=teacher,
            section_id=int(section_id),
            student_id=student_id
        )

        return JsonResponse({
            'success': True,
            'briefing_content': briefing.content,
            'facts_used': [f.__dict__ for f in briefing.facts_used],
            'calculations_used': [f.__dict__ for f in briefing.calculations_used],
            'actions_used': [f.__dict__ for f in briefing.actions_used],
            'disclaimer': briefing.disclaimer
        })
