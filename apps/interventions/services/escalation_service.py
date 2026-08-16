"""
Intervention Escalation Service for Phase 4.
Handles structured escalation transfers and target role logging.
"""

from typing import Optional
from apps.core.models import AuditLog
from apps.interventions.models import Intervention, InterventionEscalation
from .lifecycle_service import InterventionLifecycleService


class InterventionEscalationService:
    """
    Escalation dispatcher transferring cases to Academic Advisors or Department Coordinators.
    """

    @classmethod
    def process_overdue_escalation(
        cls,
        intervention: Intervention,
        user,
        target_role: str = "ACADEMIC_ADVISOR",
        custom_reason: str = ""
    ) -> InterventionEscalation:
        """
        Escalate a severely overdue support plan.
        """
        reason = custom_reason or f"Support plan is overdue by more than 14 calendar days with insufficient student engagement."
        return InterventionLifecycleService.escalate_intervention(
            intervention=intervention,
            user=user,
            target_role=target_role,
            reason=reason
        )

    @classmethod
    def process_ineffective_escalation(
        cls,
        intervention: Intervention,
        user,
        target_role: str = "DEPARTMENT_COORDINATOR",
        custom_reason: str = ""
    ) -> InterventionEscalation:
        """
        Escalate an ineffective outcome for higher-level departmental review.
        """
        reason = custom_reason or f"Post-intervention diagnostics indicate persistent risk and ineffective primary target recovery."
        return InterventionLifecycleService.escalate_intervention(
            intervention=intervention,
            user=user,
            target_role=target_role,
            reason=reason
        )
