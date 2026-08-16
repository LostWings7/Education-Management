"""
Action checklist management service for Phase 4 Interventions.
Handles action sequencing, status progression, and LearningResource integration.
"""

from typing import List, Optional
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.models import AuditLog
from apps.academic.models import LearningResource, Topic, Course
from apps.interventions.models import Intervention, InterventionAction


class InterventionActionService:
    """
    Service managing discrete action steps inside an intervention plan.
    """

    @classmethod
    def get_suggested_resources(cls, course: Course, topic: Optional[Topic] = None) -> List[LearningResource]:
        """
        Query available published learning resources matching the targeted course and topic.
        """
        qs = LearningResource.objects.filter(course=course, is_published=True)
        if topic:
            qs = qs.filter(topic=topic)
        return list(qs.order_by('-created_at'))

    @classmethod
    @transaction.atomic
    def add_action(
        cls,
        intervention: Intervention,
        title: str,
        description: str = "",
        verification_type: str = InterventionAction.VerificationType.STUDENT_CHECK,
        resource: Optional[LearningResource] = None,
        due_date=None
    ) -> InterventionAction:
        """
        Append a new action step to the plan.
        """
        next_order = intervention.actions.count() + 1
        action = InterventionAction.objects.create(
            intervention=intervention,
            order_index=next_order,
            title=title,
            description=description,
            verification_type=verification_type,
            resource=resource,
            due_date=due_date or intervention.due_date,
            status=InterventionAction.ActionStatus.PENDING
        )
        return action

    @classmethod
    @transaction.atomic
    def update_action_status(
        cls,
        action: InterventionAction,
        user,
        new_status: str,
        completion_notes: str = ""
    ) -> InterventionAction:
        """
        Update action progress status with permission validation.
        """
        is_student = hasattr(user, 'student_profile') and action.intervention.student == user.student_profile
        is_teacher = hasattr(user, 'teacher_profile') and (
            action.intervention.assigned_to == user.teacher_profile or
            action.intervention.class_section.primary_teacher == user.teacher_profile
        )
        is_admin = user.is_administrator

        if not (is_student or is_teacher or is_admin):
            raise ValidationError("You do not have permission to update this action.")

        # If action requires EDUCATOR_VERIFIED, student cannot mark it completed
        if action.verification_type == InterventionAction.VerificationType.EDUCATOR_VERIFIED and is_student:
            if new_status == InterventionAction.ActionStatus.COMPLETED:
                raise ValidationError("This action requires educator verification before it can be marked completed.")

        action.status = new_status
        if new_status == InterventionAction.ActionStatus.COMPLETED:
            action.completed_at = timezone.now()
        else:
            action.completed_at = None

        if completion_notes:
            action.completion_notes = completion_notes
        action.save()

        # Audit Log
        AuditLog.log_action(
            user=user,
            action="UPDATE_INTERVENTION_ACTION",
            details={
                "intervention_id": action.intervention.pk,
                "action_id": action.pk,
                "action_title": action.title,
                "status": new_status,
                "completed": new_status == InterventionAction.ActionStatus.COMPLETED
            }
        )

        # Check if all actions in the intervention are completed
        all_actions = action.intervention.actions.all()
        if all_actions.exists() and all(a.status == InterventionAction.ActionStatus.COMPLETED for a in all_actions):
            if action.intervention.status == Intervention.Status.IN_PROGRESS:
                action.intervention.status = Intervention.Status.COMPLETED
                action.intervention.completed_at = timezone.now()
                action.intervention.save()

        return action
