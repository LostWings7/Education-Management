"""
Executive & Class Briefing Service.
Generates pre-class briefings for faculty and macro intelligence briefings for administration.
"""

import time
from typing import Optional
from django.core.exceptions import PermissionDenied
from apps.core.models import User
from apps.academic.models import TeacherProfile, ClassSection, StudentProfile
from apps.ai_service.providers.factory import get_ai_provider
from apps.ai_service.context.teacher_context import TeacherContextBuilder
from apps.ai_service.context.admin_context import AdminContextBuilder
from apps.ai_service.context.student_context import StudentContextBuilder
from apps.ai_service.prompts.system_base import TEACHER_SYSTEM_PROMPT, ADMIN_SYSTEM_PROMPT
from apps.ai_service.prompts.student_prompts import (
    TEACHER_CLASS_BRIEFING_PROMPT,
    TEACHER_STUDENT_BRIEFING_PROMPT,
    ADMIN_EXECUTIVE_BRIEFING_PROMPT
)
from apps.ai_service.schemas.responses import StructuredAIResponse
from apps.ai_service.models import AIInteractionLog


class BriefingService:
    """
    Generates tailored briefings for teachers and administrators.
    """

    @classmethod
    def generate_class_briefing(cls, teacher: TeacherProfile, section_id: int) -> StructuredAIResponse:
        """
        Generates pre-class briefing for the section instructor.
        """
        sec = ClassSection.objects.filter(pk=section_id, primary_teacher=teacher).first()
        if not sec:
            raise PermissionDenied("Teacher is not assigned to this section.")

        t0 = time.time()
        context = TeacherContextBuilder.build_context(teacher, section_id=section_id)
        prompt = TEACHER_CLASS_BRIEFING_PROMPT.format(
            course_code=sec.course.code,
            section_code=sec.section_code
        )

        provider = get_ai_provider()
        response = provider.generate_briefing(
            system_instruction=TEACHER_SYSTEM_PROMPT,
            prompt=prompt,
            context_data=context.__dict__
        )

        latency = int((time.time() - t0) * 1000)
        AIInteractionLog.objects.create(
            user=teacher.user,
            role="TEACHER",
            request_type="CLASS_BRIEFING",
            provider=provider.provider_name,
            model=getattr(provider, 'model', 'default'),
            prompt_version="teacher_class_briefing_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=response.validation_status
        )

        return response

    @classmethod
    def generate_student_briefing_for_teacher(
        cls,
        teacher: TeacherProfile,
        section_id: int,
        student_id: str
    ) -> StructuredAIResponse:
        """
        Generates confidential 1-on-1 student briefing for an enrolled student.
        """
        sec = ClassSection.objects.filter(pk=section_id, primary_teacher=teacher).first()
        if not sec:
            raise PermissionDenied("Teacher is not assigned to this section.")

        enr = sec.enrollments.filter(student__student_id=student_id, status='ENROLLED').select_related('student__user').first()
        if not enr:
            raise PermissionDenied("Student is not enrolled in this section.")

        t0 = time.time()
        student = enr.student
        context = StudentContextBuilder.build_context(student)
        prompt = TEACHER_STUDENT_BRIEFING_PROMPT.format(
            student_name=student.user.get_full_name(),
            student_id=student.student_id,
            course_code=sec.course.code
        )

        provider = get_ai_provider()
        response = provider.generate_briefing(
            system_instruction=TEACHER_SYSTEM_PROMPT,
            prompt=prompt,
            context_data=context.__dict__
        )

        latency = int((time.time() - t0) * 1000)
        AIInteractionLog.objects.create(
            user=teacher.user,
            role="TEACHER",
            request_type="STUDENT_BRIEFING",
            provider=provider.provider_name,
            model=getattr(provider, 'model', 'default'),
            prompt_version="teacher_student_briefing_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=response.validation_status
        )

        return response

    @classmethod
    def generate_institutional_briefing(cls, admin_user: User) -> StructuredAIResponse:
        """
        Generates university-wide executive briefing for administration.
        """
        t0 = time.time()
        context = AdminContextBuilder.build_context()
        prompt = ADMIN_EXECUTIVE_BRIEFING_PROMPT

        provider = get_ai_provider()
        response = provider.generate_briefing(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            prompt=prompt,
            context_data=context.__dict__
        )

        latency = int((time.time() - t0) * 1000)
        AIInteractionLog.objects.create(
            user=admin_user,
            role="ADMINISTRATOR",
            request_type="EXEC_BRIEFING",
            provider=provider.provider_name,
            model=getattr(provider, 'model', 'default'),
            prompt_version="admin_exec_briefing_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=response.validation_status
        )

        return response
