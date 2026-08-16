"""
Teacher Portal views for Phase 4 Closed-Loop Academic Interventions.
Provides full educator oversight, recommendation review, plan creation, action management,
progress checkpoints, and target-aware impact evaluations.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.mixins import TeacherRequiredMixin
from apps.academic.models import (
    ClassSection,
    StudentProfile,
    Course,
    Topic,
    LearningResource,
    Enrollment
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionEvaluation,
    InterventionEscalation
)
from apps.interventions.services import (
    InterventionRecommendationService,
    InterventionLifecycleService,
    InterventionActionService,
    InterventionCheckpointService,
    InterventionImpactService,
    InterventionMonitoringService,
    InterventionEscalationService
)


class TeacherInterventionCenterView(TeacherRequiredMixin, View):
    """
    Teacher Intervention Operations Hub:
    Displays recommendation inbox, active assigned support plans, and completed plans.
    """
    template_name = 'portal/teacher/interventions/center.html'

    def get(self, request):
        teacher = request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course', 'semester')

        # Filter by section if selected
        section_id = request.GET.get('section_id')
        selected_section = None
        interventions_qs = Intervention.objects.filter(
            class_section__in=sections
        ).select_related('student__user', 'course', 'class_section', 'topic')

        if section_id:
            selected_section = sections.filter(pk=section_id).first()
            if selected_section:
                interventions_qs = interventions_qs.filter(class_section=selected_section)

        # Recommendation Inbox
        recommendations = interventions_qs.filter(
            status=Intervention.Status.RECOMMENDED
        ).order_by('-created_at')

        # Active Plans (Assigned, In Progress)
        active_plans = interventions_qs.filter(
            status__in=[Intervention.Status.APPROVED, Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]
        ).prefetch_related('actions').order_by('due_date')

        # Evaluation & Outcome Plans
        evaluation_plans = interventions_qs.filter(
            status__in=[
                Intervention.Status.COMPLETED,
                Intervention.Status.EVALUATING,
                Intervention.Status.EFFECTIVE,
                Intervention.Status.PARTIALLY_EFFECTIVE,
                Intervention.Status.NO_MEASURABLE_CHANGE,
                Intervention.Status.INEFFECTIVE,
                Intervention.Status.ESCALATED
            ]
        ).order_by('-completed_at', '-created_at')

        # Overdue Count
        overdue_count = InterventionMonitoringService.get_overdue_interventions(active_plans).count()

        return render(request, self.template_name, {
            'sections': sections,
            'selected_section': selected_section,
            'recommendations': recommendations,
            'active_plans': active_plans,
            'evaluation_plans': evaluation_plans,
            'recommendations_count': recommendations.count(),
            'active_count': active_plans.count(),
            'overdue_count': overdue_count,
            'completed_count': evaluation_plans.count(),
        })


class TeacherScanRecommendationsView(TeacherRequiredMixin, View):
    """
    POST endpoint to run deterministic Phase 3 intelligence scan across teacher's sections
    and generate structured recommendations.
    """
    def post(self, request):
        teacher = request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher)

        section_id = request.POST.get('section_id')
        if section_id:
            sections = sections.filter(pk=section_id)

        created_total = 0
        for sec in sections:
            enrollments = Enrollment.objects.filter(
                class_section=sec,
                status=Enrollment.EnrollmentStatus.ENROLLED
            ).select_related('student__user')

            for enr in enrollments:
                recs = InterventionRecommendationService.generate_recommendations_for_student_section(
                    student=enr.student,
                    section=sec,
                    creator_user=request.user
                )
                created_total += len(recs)

        if created_total > 0:
            messages.success(request, _(f"Scan complete: Generated {created_total} new deterministic intervention recommendation(s)."))
        else:
            messages.info(request, _("Scan complete: No new intervention recommendations needed at this time."))

        return redirect('portal:teacher_interventions')


class TeacherRecommendationApproveView(TeacherRequiredMixin, View):
    """
    POST endpoint to approve a recommendation and transition it to active ASSIGNED status.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(
            Intervention,
            pk=pk,
            class_section__primary_teacher=teacher,
            status=Intervention.Status.RECOMMENDED
        )

        custom_due = request.POST.get('due_date')
        notes = request.POST.get('educator_notes', '').strip()

        try:
            InterventionLifecycleService.approve_recommendation(
                intervention=intervention,
                user=request.user,
                custom_due_date=custom_due if custom_due else None,
                educator_notes=notes
            )
            messages.success(request, _(f"Approved support plan '{intervention.title}'. Plan is now assigned to {intervention.student.student_id}."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_interventions')


class TeacherRecommendationDismissView(TeacherRequiredMixin, View):
    """
    POST endpoint to dismiss a recommendation.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(
            Intervention,
            pk=pk,
            class_section__primary_teacher=teacher,
            status=Intervention.Status.RECOMMENDED
        )

        reason = request.POST.get('reason', '').strip() or "Educator reviewed and deemed unnecessary at this time."

        try:
            InterventionLifecycleService.dismiss_recommendation(
                intervention=intervention,
                user=request.user,
                reason=reason
            )
            messages.info(request, _(f"Dismissed recommendation for {intervention.student.student_id}."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_interventions')


class TeacherInterventionDetailView(TeacherRequiredMixin, View):
    """
    Detailed educator view for managing an intervention, its action checklist, progress checkpoints, and evaluation.
    """
    template_name = 'portal/teacher/interventions/detail.html'

    def get(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(
            Intervention.objects.select_related(
                'student__user', 'course', 'class_section', 'topic', 'assigned_to__user'
            ).prefetch_related('actions__resource', 'evaluations__evaluator'),
            pk=pk,
            class_section__primary_teacher=teacher
        )

        actions = intervention.actions.all().order_by('order_index')
        evaluations = intervention.evaluations.all().order_by('checkpoint_number')
        suggested_resources = InterventionActionService.get_suggested_resources(
            course=intervention.course,
            topic=intervention.topic
        )

        return render(request, self.template_name, {
            'intervention': intervention,
            'actions': actions,
            'evaluations': evaluations,
            'suggested_resources': suggested_resources,
            'progress_percentage': intervention.action_progress_percentage,
            'is_overdue': intervention.is_overdue,
            'is_overdue_14_days': intervention.is_overdue_14_days,
        })


class TeacherActionAddView(TeacherRequiredMixin, View):
    """
    POST endpoint for teachers to add custom action steps to an intervention plan.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)

        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        ver_type = request.POST.get('verification_type', InterventionAction.VerificationType.STUDENT_CHECK)
        resource_id = request.POST.get('resource_id')

        resource = None
        if resource_id:
            resource = LearningResource.objects.filter(pk=resource_id, course=intervention.course).first()

        if title:
            InterventionActionService.add_action(
                intervention=intervention,
                title=title,
                description=description,
                verification_type=ver_type,
                resource=resource
            )
            messages.success(request, _("Action step added to plan."))

        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)


class TeacherActionUpdateView(TeacherRequiredMixin, View):
    """
    POST endpoint for teachers to verify or update status of an action step.
    """
    def post(self, request, pk, action_id):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)
        action = get_object_or_404(InterventionAction, pk=action_id, intervention=intervention)

        new_status = request.POST.get('status', InterventionAction.ActionStatus.COMPLETED)
        notes = request.POST.get('completion_notes', '').strip()

        try:
            InterventionActionService.update_action_status(
                action=action,
                user=request.user,
                new_status=new_status,
                completion_notes=notes
            )
            messages.success(request, _("Action status updated."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)


class TeacherCheckpointRecordView(TeacherRequiredMixin, View):
    """
    POST endpoint to record an intermediate progress checkpoint.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)
        notes = request.POST.get('notes', '').strip()

        InterventionCheckpointService.record_checkpoint(
            intervention=intervention,
            evaluator_user=request.user,
            notes=notes
        )
        messages.success(request, _("Intermediate progress checkpoint recorded successfully."))
        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)


class TeacherEvaluateOutcomeView(TeacherRequiredMixin, View):
    """
    POST endpoint to run target-aware impact evaluation and finalize plan outcome.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)
        notes = request.POST.get('notes', '').strip()

        final_eval = InterventionImpactService.evaluate_and_record_outcome(
            intervention=intervention,
            evaluator_user=request.user,
            evaluator_notes=notes
        )
        messages.success(request, _(f"Impact evaluated: Outcome classified as {final_eval.get_classification_display()}."))
        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)


class TeacherCloseInterventionView(TeacherRequiredMixin, View):
    """
    POST endpoint to formally archive and close an intervention.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)
        notes = request.POST.get('notes', '').strip()

        try:
            InterventionLifecycleService.close_intervention(
                intervention=intervention,
                user=request.user,
                summary_notes=notes
            )
            messages.success(request, _("Support plan closed and archived."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)


class TeacherEscalateInterventionView(TeacherRequiredMixin, View):
    """
    POST endpoint to escalate an intervention to Academic Advisor or Department Coordinator.
    """
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        intervention = get_object_or_404(Intervention, pk=pk, class_section__primary_teacher=teacher)

        target_role = request.POST.get('target_role', 'ACADEMIC_ADVISOR')
        reason = request.POST.get('reason', '').strip() or "Escalated for specialized departmental oversight."

        try:
            InterventionLifecycleService.escalate_intervention(
                intervention=intervention,
                user=request.user,
                target_role=target_role,
                reason=reason
            )
            messages.warning(request, _(f"Support plan escalated to {target_role}."))
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_intervention_detail', pk=intervention.pk)
