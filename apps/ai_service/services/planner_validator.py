"""
Deterministic Study Plan Semantic & Feasibility Validator.
Ensures AI-generated study plans only reference verified courses, assignments, and resources,
and enforces schedule feasibility limits.
"""

from typing import Tuple, List
from datetime import date
from django.conf import settings
from apps.academic.models import (
    StudentProfile,
    Enrollment,
    Assignment,
    LearningResource
)
from apps.interventions.models import InterventionAction
from apps.ai_service.schemas.responses import StudyPlanSchema, StudyPlanDaySchema, StudyPlanTaskSchema


class StudyPlanValidator:
    """
    Validates and purges fabricated or infeasible elements from study plans.
    """

    @classmethod
    def validate_plan(cls, plan: StudyPlanSchema, student: StudentProfile) -> Tuple[StudyPlanSchema, bool]:
        """
        Validates entire plan against database entities and feasibility limits.
        Returns sanitized plan and boolean isValid.
        """
        max_daily_minutes = int(getattr(settings, 'AI_MAX_DAILY_STUDY_HOURS', 4.5) * 60)
        enrolled_course_codes = set(
            Enrollment.objects.filter(
                student=student,
                status='ENROLLED'
            ).values_list('class_section__course__code', flat=True)
        )

        valid_assignment_ids = set(
            Assignment.objects.filter(
                class_section__enrollments__student=student,
                class_section__enrollments__status='ENROLLED'
            ).exclude(
                submissions__student=student,
                submissions__status='SUBMITTED'
            ).values_list('id', flat=True)
        )

        enrolled_course_ids = Enrollment.objects.filter(
            student=student,
            status='ENROLLED'
        ).values_list('class_section__course_id', flat=True)

        valid_resource_ids = set(
            LearningResource.objects.filter(
                course_id__in=enrolled_course_ids,
                is_published=True
            ).values_list('id', flat=True)
        )

        valid_action_ids = set(
            InterventionAction.objects.filter(
                intervention__student=student,
                status='PENDING'
            ).values_list('id', flat=True)
        )

        sanitized_days: List[StudyPlanDaySchema] = []
        is_fully_valid = True
        total_minutes = 0

        for day in plan.days:
            sanitized_tasks: List[StudyPlanTaskSchema] = []
            seen_tasks = set()
            day_minutes = 0

            for task in day.tasks:
                # 1. Course enrollment validation
                if task.course_code not in enrolled_course_codes:
                    is_fully_valid = False
                    continue

                # 2. Assignment validation (Must belong to student & be pending)
                if task.assignment_id is not None:
                    if task.assignment_id not in valid_assignment_ids:
                        is_fully_valid = False
                        continue

                # 3. Resource validation (Must exist and be published)
                if task.resource_id is not None:
                    if task.resource_id not in valid_resource_ids:
                        is_fully_valid = False
                        task.resource_id = None
                        task.resource_title = None

                # 4. Action step validation (Must belong to student & be pending)
                if task.action_id is not None:
                    if task.action_id not in valid_action_ids:
                        is_fully_valid = False
                        task.action_id = None

                # 5. Deduplication check
                task_key = (task.course_code, task.title.strip().lower())
                if task_key in seen_tasks:
                    is_fully_valid = False
                    continue
                seen_tasks.add(task_key)

                # 6. Workload feasibility check
                duration = min(max(task.duration_minutes, 15), 120)
                if day_minutes + duration > max_daily_minutes:
                    is_fully_valid = False
                    continue

                # 7. Strict non-official event demarcation
                task.is_official_event = False
                task.duration_minutes = duration

                sanitized_tasks.append(task)
                day_minutes += duration

            total_minutes += day_minutes
            sanitized_days.append(StudyPlanDaySchema(
                day_name=day.day_name,
                date_str=day.date_str,
                focus_summary=day.focus_summary or f"Study schedule for {day.day_name}",
                tasks=sanitized_tasks,
                total_study_minutes=day_minutes
            ))

        plan.days = sanitized_days
        plan.total_estimated_hours = round(total_minutes / 60.0, 1)
        plan.validation_status = "VALID" if is_fully_valid else "VALIDATED_AND_REMEDIATED"
        plan.disclaimer = "AI-suggested study blocks are not official timetable events."

        return plan, is_fully_valid
