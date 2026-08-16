"""
Intervention Monitoring & Overdue Detection Service for Phase 4.
Calculates progress metrics, tracks calendar deadlines, and identifies candidates for escalation.
"""

from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db.models import QuerySet

from apps.interventions.models import Intervention, InterventionAction


class InterventionMonitoringService:
    """
    Service monitoring intervention progress and calendar deadlines.
    """

    @classmethod
    def get_overdue_interventions(cls, queryset: Optional[QuerySet] = None) -> QuerySet:
        """
        Return active interventions where today's date exceeds the due date.
        """
        today = timezone.now().date()
        active_statuses = [
            Intervention.Status.APPROVED,
            Intervention.Status.ASSIGNED,
            Intervention.Status.IN_PROGRESS
        ]
        qs = queryset if queryset is not None else Intervention.objects.all()
        return qs.filter(status__in=active_statuses, due_date__lt=today).order_by('due_date')

    @classmethod
    def get_severely_overdue_interventions(cls, queryset: Optional[QuerySet] = None) -> QuerySet:
        """
        Return interventions overdue by more than 14 calendar days (today > due_date + 14 days).
        """
        cutoff_date = timezone.now().date() - timezone.timedelta(days=14)
        active_statuses = [
            Intervention.Status.APPROVED,
            Intervention.Status.ASSIGNED,
            Intervention.Status.IN_PROGRESS
        ]
        qs = queryset if queryset is not None else Intervention.objects.all()
        return qs.filter(status__in=active_statuses, due_date__lt=cutoff_date).order_by('due_date')

    @classmethod
    def get_candidate_escalations(cls, queryset: Optional[QuerySet] = None) -> List[Dict[str, Any]]:
        """
        Identify interventions requiring immediate educator or administrative escalation:
        1. Severely overdue (> 14 days) with zero progress (progress = 0%).
        2. Outcome evaluated as INEFFECTIVE.
        """
        candidates = []
        qs = queryset if queryset is not None else Intervention.objects.all()

        # Check severely overdue with 0% progress
        severely_overdue = cls.get_severely_overdue_interventions(qs)
        for plan in severely_overdue:
            if plan.action_progress_percentage == 0.0:
                candidates.append({
                    'intervention': plan,
                    'reason': f"Action plan is overdue by more than 14 calendar days with 0% student progress.",
                    'recommended_role': 'ACADEMIC_ADVISOR'
                })

        # Check ineffective outcomes
        ineffective_plans = qs.filter(status=Intervention.Status.INEFFECTIVE)
        for plan in ineffective_plans:
            candidates.append({
                'intervention': plan,
                'reason': "Post-intervention metrics showed deterioration or persistent critical academic risk.",
                'recommended_role': 'DEPARTMENT_COORDINATOR'
            })

        return candidates
