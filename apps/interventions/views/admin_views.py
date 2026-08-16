"""
Administrator Portal views for Phase 4 Closed-Loop Academic Interventions.
Provides institution-wide oversight, priority distribution, effectiveness analytics,
and comprehensive audit trails.
"""

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Count, Q

from apps.core.mixins import AdminRequiredMixin
from apps.academic.models import Department
from apps.interventions.models import (
    Intervention,
    InterventionEvaluation,
    InterventionEscalation
)
from apps.interventions.services import InterventionMonitoringService


class AdminInterventionOverviewView(AdminRequiredMixin, View):
    """
    Institution-Wide Academic Intervention Oversight Hub.
    """
    template_name = 'portal/admin/interventions/overview.html'

    def get(self, request):
        all_interventions = Intervention.objects.select_related(
            'student__user', 'student__department', 'course', 'class_section', 'assigned_to__user'
        ).all()

        total_count = all_interventions.count()
        active_plans = all_interventions.filter(
            status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]
        )
        active_count = active_plans.count()
        overdue_count = InterventionMonitoringService.get_overdue_interventions(active_plans).count()
        escalated_count = all_interventions.filter(status=Intervention.Status.ESCALATED).count()

        # Outcomes breakdown
        effective_count = all_interventions.filter(status=Intervention.Status.EFFECTIVE).count()
        completed_evaluated = all_interventions.filter(
            status__in=[
                Intervention.Status.EFFECTIVE,
                Intervention.Status.PARTIALLY_EFFECTIVE,
                Intervention.Status.NO_MEASURABLE_CHANGE,
                Intervention.Status.INEFFECTIVE
            ]
        ).count()
        effectiveness_rate = round((effective_count / completed_evaluated * 100.0), 1) if completed_evaluated > 0 else 0.0

        # Priority Counts
        priority_counts = {
            'URGENT': all_interventions.filter(priority=Intervention.Priority.URGENT).count(),
            'HIGH': all_interventions.filter(priority=Intervention.Priority.HIGH).count(),
            'MEDIUM': all_interventions.filter(priority=Intervention.Priority.MEDIUM).count(),
            'LOW': all_interventions.filter(priority=Intervention.Priority.LOW).count(),
        }

        # Category Counts
        category_counts = all_interventions.values('category').annotate(count=Count('id')).order_by('-count')

        # Department Breakdown
        dept_summary = []
        departments = Department.objects.all().order_by('code')
        for d in departments:
            d_plans = all_interventions.filter(student__department=d)
            d_total = d_plans.count()
            d_active = d_plans.filter(status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]).count()
            d_effective = d_plans.filter(status=Intervention.Status.EFFECTIVE).count()
            d_overdue = InterventionMonitoringService.get_overdue_interventions(d_plans).count()
            dept_summary.append({
                'department': d,
                'total_interventions': d_total,
                'active_count': d_active,
                'effective_count': d_effective,
                'overdue_count': d_overdue
            })

        # Recent intervention list
        recent_interventions = all_interventions.order_by('-created_at')[:25]

        return render(request, self.template_name, {
            'total_count': total_count,
            'active_count': active_count,
            'overdue_count': overdue_count,
            'escalated_count': escalated_count,
            'effectiveness_rate': effectiveness_rate,
            'priority_counts': priority_counts,
            'category_counts': category_counts,
            'dept_summary': dept_summary,
            'recent_interventions': recent_interventions,
        })


class AdminInterventionDetailView(AdminRequiredMixin, View):
    """
    Detailed audit inspector for administrators.
    """
    template_name = 'portal/admin/interventions/detail.html'

    def get(self, request, pk):
        intervention = get_object_or_404(
            Intervention.objects.select_related(
                'student__user', 'student__department', 'course', 'class_section', 'topic', 'assigned_to__user'
            ).prefetch_related('actions__resource', 'evaluations__evaluator', 'escalations__escalated_by'),
            pk=pk
        )

        actions = intervention.actions.all().order_by('order_index')
        evaluations = intervention.evaluations.all().order_by('checkpoint_number')
        escalations = intervention.escalations.all().order_by('-created_at')

        return render(request, self.template_name, {
            'intervention': intervention,
            'actions': actions,
            'evaluations': evaluations,
            'escalations': escalations,
        })
