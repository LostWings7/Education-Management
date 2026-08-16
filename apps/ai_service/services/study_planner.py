"""
Study Planner Service.
Coordinates AI study plan generation and deterministic feasibility validation.
"""

import time
from apps.academic.models import StudentProfile
from apps.ai_service.providers.factory import get_ai_provider
from apps.ai_service.context.student_context import StudentContextBuilder
from apps.ai_service.prompts.system_base import STUDENT_SYSTEM_PROMPT
from apps.ai_service.prompts.student_prompts import STUDY_PLANNER_PROMPT
from apps.ai_service.schemas.responses import StudyPlanSchema
from apps.ai_service.models import AIInteractionLog
from .planner_validator import StudyPlanValidator


class StudyPlannerService:
    """
    Generates and validates weekly study schedules for students.
    """

    @classmethod
    def generate_plan_for_student(cls, student: StudentProfile) -> StudyPlanSchema:
        """
        Generates a validated study schedule for the authenticated student.
        """
        t0 = time.time()
        context = StudentContextBuilder.build_context(student)
        provider = get_ai_provider()

        raw_plan = provider.generate_study_plan(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            prompt=STUDY_PLANNER_PROMPT,
            context_data=context.__dict__
        )

        validated_plan, is_valid = StudyPlanValidator.validate_plan(raw_plan, student)
        latency = int((time.time() - t0) * 1000)

        AIInteractionLog.objects.create(
            user=student.user,
            role="STUDENT",
            request_type="STUDY_PLAN",
            provider=provider.provider_name,
            model=getattr(provider, 'model', 'default'),
            prompt_version="study_planner_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=validated_plan.validation_status
        )

        return validated_plan
