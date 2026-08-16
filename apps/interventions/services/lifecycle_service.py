"""
Intervention Lifecycle State Machine & Transition Service for Phase 4.
Enforces valid state transitions and writes audit trail records to AuditLog.
"""

from typing import Optional, Dict, Any
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.models import AuditLog
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionAcknowledgement,
    InterventionEscalation
)


class InterventionLifecycleService:
    """
    State machine transition authority for academic interventions.
    """

    VALID_TRANSITIONS = {
        Intervention.Status.RECOMMENDED: [
            Intervention.Status.APPROVED,
            Intervention.Status.ASSIGNED,
            Intervention.Status.DISMISSED
        ],
        Intervention.Status.APPROVED: [
            Intervention.Status.ASSIGNED,
            Intervention.Status.DISMISSED,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.CREATED: [
            Intervention.Status.ASSIGNED,
            Intervention.Status.DISMISSED,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.ASSIGNED: [
            Intervention.Status.IN_PROGRESS,
            Intervention.Status.DISMISSED,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.IN_PROGRESS: [
            Intervention.Status.COMPLETED,
            Intervention.Status.EVALUATING,
            Intervention.Status.ESCALATED,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.COMPLETED: [
            Intervention.Status.EVALUATING,
            Intervention.Status.EFFECTIVE,
            Intervention.Status.PARTIALLY_EFFECTIVE,
            Intervention.Status.NO_MEASURABLE_CHANGE,
            Intervention.Status.INEFFECTIVE,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.EVALUATING: [
            Intervention.Status.EFFECTIVE,
            Intervention.Status.PARTIALLY_EFFECTIVE,
            Intervention.Status.NO_MEASURABLE_CHANGE,
            Intervention.Status.INEFFECTIVE,
            Intervention.Status.CLOSED
        ],
        Intervention.Status.EFFECTIVE: [Intervention.Status.CLOSED],
        Intervention.Status.PARTIALLY_EFFECTIVE: [Intervention.Status.CLOSED, Intervention.Status.IN_PROGRESS],
        Intervention.Status.NO_MEASURABLE_CHANGE: [Intervention.Status.CLOSED, Intervention.Status.IN_PROGRESS, Intervention.Status.ESCALATED],
        Intervention.Status.INEFFECTIVE: [Intervention.Status.ESCALATED, Intervention.Status.CLOSED, Intervention.Status.IN_PROGRESS],
        Intervention.Status.ESCALATED: [Intervention.Status.IN_PROGRESS, Intervention.Status.CLOSED],
        Intervention.Status.DISMISSED: [], # Terminal
        Intervention.Status.CLOSED: []      # Terminal
    }

    @classmethod
    def validate_transition(cls, current_status: str, target_status: str) -> None:
        """Raise ValidationError if transition is not allowed."""
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise ValidationError(
                f"Invalid lifecycle state transition from '{current_status}' to '{target_status}'. "
                f"Allowed transitions: {allowed}."
            )

    @classmethod
    @transaction.atomic
    def approve_recommendation(
        cls,
        intervention: Intervention,
        user,
        custom_due_date=None,
        educator_notes: str = ""
    ) -> Intervention:
        """
        Educator approves a recommendation.
        Transitions RECOMMENDED -> ASSIGNED (active support plan).
        """
        cls.validate_transition(intervention.status, Intervention.Status.ASSIGNED)

        old_status = intervention.status
        intervention.status = Intervention.Status.ASSIGNED
        intervention.approved_at = timezone.now()
        if custom_due_date:
            intervention.due_date = custom_due_date
        if educator_notes:
            intervention.educator_notes = educator_notes
        intervention.save()

        # Audit Log
        AuditLog.log_action(
            user=user,
            action="APPROVE_INTERVENTION_RECOMMENDATION",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "course_code": intervention.course.code,
                "category": intervention.category,
                "old_status": old_status,
                "new_status": intervention.status
            }
        )
        return intervention

    @classmethod
    @transaction.atomic
    def dismiss_recommendation(
        cls,
        intervention: Intervention,
        user,
        reason: str
    ) -> Intervention:
        """
        Educator dismisses/rejects a recommendation.
        Transitions RECOMMENDED -> DISMISSED.
        """
        cls.validate_transition(intervention.status, Intervention.Status.DISMISSED)

        old_status = intervention.status
        intervention.status = Intervention.Status.DISMISSED
        intervention.dismissed_at = timezone.now()
        intervention.dismissal_reason = reason
        intervention.save()

        # Audit Log
        AuditLog.log_action(
            user=user,
            action="DISMISS_INTERVENTION_RECOMMENDATION",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "reason": reason,
                "old_status": old_status,
                "new_status": intervention.status
            }
        )
        return intervention

    @classmethod
    @transaction.atomic
    def acknowledge_by_student(
        cls,
        intervention: Intervention,
        student_user,
        ack_status: str,
        student_notes: str = ""
    ) -> InterventionAcknowledgement:
        """
        Student acknowledges the assigned support plan.
        If ACCEPTED, moves status to IN_PROGRESS.
        """
        # Ensure student is the assigned student
        if not hasattr(student_user, 'student_profile') or intervention.student != student_user.student_profile:
            raise ValidationError("You do not have permission to acknowledge this intervention.")

        ack, _ = InterventionAcknowledgement.objects.get_or_create(intervention=intervention)
        ack.status = ack_status
        ack.acknowledged_at = timezone.now()
        ack.student_notes = student_notes
        ack.save()

        if ack_status == InterventionAcknowledgement.AckStatus.ACCEPTED:
            if intervention.status == Intervention.Status.ASSIGNED:
                cls.validate_transition(intervention.status, Intervention.Status.IN_PROGRESS)
                intervention.status = Intervention.Status.IN_PROGRESS
                if not intervention.started_at:
                    intervention.started_at = timezone.now()
                intervention.save()

        # Audit Log
        AuditLog.log_action(
            user=student_user,
            action="ACKNOWLEDGE_INTERVENTION",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "acknowledgment_status": ack_status,
                "student_notes": student_notes
            }
        )
        return ack

    @classmethod
    @transaction.atomic
    def complete_actions(
        cls,
        intervention: Intervention,
        user
    ) -> Intervention:
        """
        Mark all actions completed and transition to COMPLETED / EVALUATING.
        """
        cls.validate_transition(intervention.status, Intervention.Status.COMPLETED)

        intervention.status = Intervention.Status.COMPLETED
        intervention.completed_at = timezone.now()
        intervention.save()

        AuditLog.log_action(
            user=user,
            action="COMPLETE_INTERVENTION_ACTIONS",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "new_status": intervention.status
            }
        )
        return intervention

    @classmethod
    @transaction.atomic
    def close_intervention(
        cls,
        intervention: Intervention,
        user,
        summary_notes: str = ""
    ) -> Intervention:
        """
        Formally close and archive an intervention.
        """
        cls.validate_transition(intervention.status, Intervention.Status.CLOSED)

        old_status = intervention.status
        intervention.status = Intervention.Status.CLOSED
        intervention.closed_at = timezone.now()
        if summary_notes:
            intervention.effectiveness_summary = f"{intervention.effectiveness_summary}\nClosure Notes: {summary_notes}".strip()
        intervention.save()

        AuditLog.log_action(
            user=user,
            action="CLOSE_INTERVENTION",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "previous_status": old_status,
                "closure_notes": summary_notes
            }
        )
        return intervention

    @classmethod
    @transaction.atomic
    def escalate_intervention(
        cls,
        intervention: Intervention,
        user,
        target_role: str,
        reason: str
    ) -> InterventionEscalation:
        """
        Escalate intervention to Academic Advisor or Department Coordinator.
        """
        cls.validate_transition(intervention.status, Intervention.Status.ESCALATED)

        old_status = intervention.status
        intervention.status = Intervention.Status.ESCALATED
        intervention.save()

        escalation = InterventionEscalation.objects.create(
            intervention=intervention,
            escalated_by=user,
            escalated_to_role=target_role,
            reason=reason,
            previous_status=old_status
        )

        AuditLog.log_action(
            user=user,
            action="ESCALATE_INTERVENTION",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "escalated_to_role": target_role,
                "reason": reason,
                "previous_status": old_status
            }
        )
        return escalation
