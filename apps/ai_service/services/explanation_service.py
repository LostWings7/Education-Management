"""
Contextual AI Explanation Service.
Generates evidence-grounded explanations for deterministic analytics and interventions.
"""

import time
from typing import Dict, Any, Optional
from apps.core.models import User
from apps.academic.models import StudentProfile
from apps.ai_service.providers.factory import get_ai_provider
from apps.ai_service.context.student_context import StudentContextBuilder
from apps.ai_service.prompts.system_base import STUDENT_SYSTEM_PROMPT
from apps.ai_service.prompts.student_prompts import STUDENT_EXPLANATION_PROMPT
from apps.ai_service.schemas.responses import StructuredAIResponse
from apps.ai_service.models import AIInteractionLog


class ExplanationService:
    """
    Generates tailored, evidence-backed explanations for specific analytical findings.
    """

    @classmethod
    def explain_insight(
        cls,
        user: User,
        subject: str,
        evidence: Dict[str, Any],
        student: Optional[StudentProfile] = None
    ) -> StructuredAIResponse:
        """
        Explains an analytical finding (Risk, Anomaly, Attendance, Intervention) for the student.
        """
        t0 = time.time()
        if not student and user.is_student:
            student = getattr(user, 'student_profile', None)

        if student:
            context = StudentContextBuilder.build_context(student)
            context_dict = context.__dict__
        else:
            context_dict = evidence

        context_dict['title'] = subject
        context_dict['summary'] = str(evidence)

        prompt = STUDENT_EXPLANATION_PROMPT.format(
            subject=subject,
            evidence=str(evidence)
        )

        provider = get_ai_provider()
        response = provider.generate_explanation(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            prompt=prompt,
            context_data=context_dict
        )

        latency = int((time.time() - t0) * 1000)
        AIInteractionLog.objects.create(
            user=user,
            role=getattr(user, 'role', 'STUDENT'),
            request_type="EXPLANATION",
            provider=provider.provider_name,
            model=getattr(provider, 'model', 'default'),
            prompt_version="student_explanation_v1.0",
            latency_ms=latency,
            success=True,
            validation_status=response.validation_status
        )

        return response
