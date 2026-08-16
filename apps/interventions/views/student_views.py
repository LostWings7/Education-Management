"""
Student Portal views for Phase 4 Closed-Loop Academic Interventions.
Provides a supportive, non-punitive experience for tracking academic recovery plans and completing action items.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import StudentRequiredMixin
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionAcknowledgement
)
from apps.interventions.services import (
    InterventionLifecycleService,
    InterventionActionService
)


class StudentInterventionListView(StudentRequiredMixin, View):
    """
    Student Support Hub: Lists active academic support plans and historical archives.
    """
    template_name = 'portal/student/interventions/list.html'

    def get(self, request):
        student = request.user.student_profile

        # Active plans: ASSIGNED or IN_PROGRESS or EVALUATING
        active_statuses = [
            Intervention.Status.ASSIGNED,
            Intervention.Status.IN_PROGRESS,
            Intervention.Status.COMPLETED,
            Intervention.Status.EVALUATING
        ]
        active_interventions = Intervention.objects.filter(
            student=student,
            status__in=active_statuses
        ).select_related('course', 'class_section', 'topic', 'assigned_to__user').prefetch_related('actions').order_by('-created_at')

        # Completed/Closed archive
        archive_statuses = [
            Intervention.Status.EFFECTIVE,
            Intervention.Status.PARTIALLY_EFFECTIVE,
            Intervention.Status.NO_MEASURABLE_CHANGE,
            Intervention.Status.INEFFECTIVE,
            Intervention.Status.CLOSED
        ]
        archived_interventions = Intervention.objects.filter(
            student=student,
            status__in=archive_statuses
        ).select_related('course', 'class_section', 'assigned_to__user').order_by('-closed_at', '-created_at')

        return render(request, self.template_name, {
            'active_interventions': active_interventions,
            'archived_interventions': archived_interventions,
        })


class StudentInterventionDetailView(StudentRequiredMixin, View):
    """
    Detailed support plan view with action checklist, learning resource downloads, and acknowledgment.
    """
    template_name = 'portal/student/interventions/detail.html'

    def get(self, request, pk):
        student = request.user.student_profile
        intervention = get_object_or_404(
            Intervention.objects.select_related(
                'course', 'class_section', 'topic', 'assigned_to__user'
            ).prefetch_related('actions__resource', 'evaluations__evaluator'),
            pk=pk,
            student=student
        )

        ack = getattr(intervention, 'acknowledgement', None)
        actions = intervention.actions.all().order_by('order_index')
        evaluations = intervention.evaluations.all().order_by('checkpoint_number')

        return render(request, self.template_name, {
            'intervention': intervention,
            'acknowledgement': ack,
            'actions': actions,
            'evaluations': evaluations,
        })


class StudentInterventionAcknowledgeView(StudentRequiredMixin, View):
    """
    POST endpoint for students to acknowledge or request clarification on an assigned plan.
    """
    def post(self, request, pk):
        student = request.user.student_profile
        intervention = get_object_or_404(Intervention, pk=pk, student=student)

        ack_status = request.POST.get('status', InterventionAcknowledgement.AckStatus.ACCEPTED)
        notes = request.POST.get('notes', '').strip()

        try:
            InterventionLifecycleService.acknowledge_by_student(
                intervention=intervention,
                student_user=request.user,
                ack_status=ack_status,
                student_notes=notes
            )
            if ack_status == InterventionAcknowledgement.AckStatus.ACCEPTED:
                messages.success(request, _("Thank you! You have accepted this support plan. Action checklist is now active."))
            else:
                messages.info(request, _("Your clarification request has been forwarded to your instructor."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:student_intervention_detail', pk=intervention.pk)


class StudentActionToggleView(StudentRequiredMixin, View):
    """
    POST endpoint allowing a student to mark a self-check action item as completed or pending.
    """
    def post(self, request, pk, action_id):
        student = request.user.student_profile
        intervention = get_object_or_404(Intervention, pk=pk, student=student)
        action = get_object_or_404(InterventionAction, pk=action_id, intervention=intervention)

        new_status = request.POST.get('status', InterventionAction.ActionStatus.COMPLETED)
        notes = request.POST.get('notes', '').strip()

        try:
            InterventionActionService.update_action_status(
                action=action,
                user=request.user,
                new_status=new_status,
                completion_notes=notes
            )
            messages.success(request, _("Action progress updated successfully."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:student_intervention_detail', pk=intervention.pk)
