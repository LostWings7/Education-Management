"""
Domain models for Phase 4 Closed-Loop Academic Intervention Engine.
Defines:
- Intervention: Core academic support plan with frozen baseline/followup evidence snapshots and target metrics.
- InterventionAction: Action checklist items linked to LearningResources.
- InterventionEvaluation: Immutable progress checkpoints and final impact evaluation records.
- InterventionAcknowledgement: Student participation acknowledgment.
- InterventionEscalation: Structured transfer to academic advisors or department coordinators.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.academic.models import StudentProfile, TeacherProfile, ClassSection, Course, Topic, LearningResource


class Intervention(TimeStampedModel):
    """
    Primary academic support plan record with frozen evidence snapshots and lifecycle governance.
    """
    class InterventionCategory(models.TextChoices):
        ACADEMIC_REMEDIAL = 'ACADEMIC_REMEDIAL', _('Topic / Academic Remediation')
        ATTENDANCE_RECOVERY = 'ATTENDANCE_RECOVERY', _('Attendance Recovery Plan')
        ASSIGNMENT_RECOVERY = 'ASSIGNMENT_RECOVERY', _('Coursework & Assignment Support')
        FACULTY_DIAGNOSTIC = 'FACULTY_DIAGNOSTIC', _('Faculty Diagnostic Review')
        THEORY_REINFORCEMENT = 'THEORY_REINFORCEMENT', _('Theoretical Concept Reinforcement')
        ENGAGEMENT_SUPPORT = 'ENGAGEMENT_SUPPORT', _('Academic Engagement Check')

    class Status(models.TextChoices):
        RECOMMENDED = 'RECOMMENDED', _('Recommended (Pending Educator Review)')
        APPROVED = 'APPROVED', _('Approved')
        CREATED = 'CREATED', _('Created')
        ASSIGNED = 'ASSIGNED', _('Assigned to Student')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Actions Completed (Pending Evaluation)')
        EVALUATING = 'EVALUATING', _('In Evaluation Window')
        EFFECTIVE = 'EFFECTIVE', _('Effective')
        PARTIALLY_EFFECTIVE = 'PARTIALLY_EFFECTIVE', _('Partially Effective')
        NO_MEASURABLE_CHANGE = 'NO_MEASURABLE_CHANGE', _('No Measurable Change')
        INEFFECTIVE = 'INEFFECTIVE', _('Ineffective')
        ESCALATED = 'ESCALATED', _('Escalated')
        DISMISSED = 'DISMISSED', _('Dismissed')
        CLOSED = 'CLOSED', _('Closed & Archived')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low Priority')
        MEDIUM = 'MEDIUM', _('Medium Priority')
        HIGH = 'HIGH', _('High Priority')
        URGENT = 'URGENT', _('Urgent Priority')

    class TargetMetric(models.TextChoices):
        ATTENDANCE = 'ATTENDANCE', _('Attendance Percentage')
        ASSIGNMENT_COMPLETION = 'ASSIGNMENT_COMPLETION', _('Assignment Completion Rate')
        TOPIC_MASTERY = 'TOPIC_MASTERY', _('Topic Syllabus Mastery')
        ASSESSMENT_PERFORMANCE = 'ASSESSMENT_PERFORMANCE', _('Weighted Course Performance')
        THEORY_PERFORMANCE = 'THEORY_PERFORMANCE', _('Theoretical Exam Scores')
        ANOMALY_RECOVERY = 'ANOMALY_RECOVERY', _('Performance Anomaly Recovery')

    class EvaluationWindow(models.TextChoices):
        DAYS_7 = 'DAYS_7', _('Immediate Window (7 Days)')
        DAYS_14 = 'DAYS_14', _('Short Term Window (14 Days)')
        DAYS_30 = 'DAYS_30', _('Standard Term Window (30 Days)')
        NEXT_ASSESSMENT = 'NEXT_ASSESSMENT', _('Next Course Assessment')

    # Core Relational Links
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='interventions',
        verbose_name=_('student')
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='interventions',
        verbose_name=_('target course')
    )
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='interventions',
        verbose_name=_('class section')
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interventions',
        verbose_name=_('target syllabus topic')
    )

    # Ownership & Governance
    assigned_to = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='supervised_interventions',
        verbose_name=_('supervising educator')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_interventions',
        verbose_name=_('author / initiator')
    )

    # Plan Specification
    title = models.CharField(_('intervention title'), max_length=200)
    category = models.CharField(
        _('category'),
        max_length=30,
        choices=InterventionCategory.choices,
        default=InterventionCategory.ACADEMIC_REMEDIAL
    )
    status = models.CharField(
        _('lifecycle status'),
        max_length=30,
        choices=Status.choices,
        default=Status.RECOMMENDED
    )
    priority = models.CharField(
        _('priority level'),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    primary_target_metric = models.CharField(
        _('primary target metric'),
        max_length=30,
        choices=TargetMetric.choices,
        default=TargetMetric.ASSESSMENT_PERFORMANCE
    )
    evaluation_window = models.CharField(
        _('evaluation window'),
        max_length=20,
        choices=EvaluationWindow.choices,
        default=EvaluationWindow.DAYS_14
    )

    # Narrative Goals & Notes
    objective = models.TextField(_('concrete learning / recovery objective'))
    educator_notes = models.TextField(_('faculty observations & strategy'), blank=True)

    # Target Deadlines & Lifecycle Timestamps
    due_date = models.DateField(_('action plan completion due date'))
    approved_at = models.DateTimeField(_('approval timestamp'), null=True, blank=True)
    started_at = models.DateTimeField(_('started timestamp'), null=True, blank=True)
    completed_at = models.DateTimeField(_('actions completed timestamp'), null=True, blank=True)
    evaluated_at = models.DateTimeField(_('impact evaluated timestamp'), null=True, blank=True)
    closed_at = models.DateTimeField(_('closed timestamp'), null=True, blank=True)
    dismissed_at = models.DateTimeField(_('dismissed timestamp'), null=True, blank=True)
    dismissal_reason = models.TextField(_('dismissal explanation'), blank=True)

    # Immutable Evidence & Snapshots
    trigger_insight_type = models.CharField(_('trigger insight type'), max_length=50, blank=True)
    baseline_metrics = models.JSONField(_('frozen baseline snapshot at creation'), default=dict)
    followup_metrics = models.JSONField(_('frozen follow-up metrics at evaluation'), default=dict)
    effectiveness_summary = models.TextField(_('deterministic impact summary'), blank=True)

    class Meta:
        verbose_name = _('academic intervention')
        verbose_name_plural = _('academic interventions')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.student.student_id} - {self.title} ({self.course.code})"

    @property
    def is_overdue(self):
        """Check if action plan is past due date and not completed/closed."""
        if self.status in [self.Status.COMPLETED, self.Status.CLOSED, self.Status.DISMISSED, self.Status.EFFECTIVE, self.Status.PARTIALLY_EFFECTIVE, self.Status.INEFFECTIVE, self.Status.NO_MEASURABLE_CHANGE]:
            return False
        return timezone.now().date() > self.due_date

    @property
    def is_overdue_14_days(self):
        """Check if action plan is overdue by more than 14 calendar days."""
        if self.status in [self.Status.COMPLETED, self.Status.CLOSED, self.Status.DISMISSED, self.Status.EFFECTIVE, self.Status.PARTIALLY_EFFECTIVE, self.Status.INEFFECTIVE, self.Status.NO_MEASURABLE_CHANGE]:
            return False
        return timezone.now().date() > (self.due_date + timezone.timedelta(days=14))

    @property
    def action_progress_percentage(self):
        """Compute the completion rate of associated action items."""
        total = self.actions.count()
        if total == 0:
            return 0.0
        completed = self.actions.filter(status=InterventionAction.ActionStatus.COMPLETED).count()
        return round((completed / total) * 100.0, 1)


class InterventionAction(TimeStampedModel):
    """
    Concrete actionable step within an intervention plan.
    Supports ordering, due dates, verification types, and linked LearningResources.
    """
    class ActionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        SKIPPED = 'SKIPPED', _('Skipped / Optional')

    class VerificationType(models.TextChoices):
        STUDENT_CHECK = 'STUDENT_CHECK', _('Student Self-Check')
        EDUCATOR_VERIFIED = 'EDUCATOR_VERIFIED', _('Faculty / Advisor Verified')
        SYSTEM_AUTOMATIC = 'SYSTEM_AUTOMATIC', _('Automatic System Verification')

    intervention = models.ForeignKey(
        Intervention,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name=_('parent intervention')
    )
    order_index = models.PositiveSmallIntegerField(_('sequence order'), default=1)
    title = models.CharField(_('action title'), max_length=200)
    description = models.TextField(_('detailed instructions & requirements'), blank=True)

    # Optional Curricular Learning Resource Link
    resource = models.ForeignKey(
        LearningResource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_intervention_actions',
        verbose_name=_('linked learning resource')
    )

    status = models.CharField(
        _('action status'),
        max_length=20,
        choices=ActionStatus.choices,
        default=ActionStatus.PENDING
    )
    verification_type = models.CharField(
        _('verification type'),
        max_length=30,
        choices=VerificationType.choices,
        default=VerificationType.STUDENT_CHECK
    )

    due_date = models.DateField(_('action target due date'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completion timestamp'), null=True, blank=True)
    completion_notes = models.TextField(_('completion evidence / notes'), blank=True)

    class Meta:
        verbose_name = _('intervention action item')
        verbose_name_plural = _('intervention action items')
        ordering = ['intervention', 'order_index']

    def __str__(self):
        return f"Step {self.order_index}: {self.title} ({self.get_status_display()})"


class InterventionEvaluation(TimeStampedModel):
    """
    Immutable checkpoint and final impact evaluation records preserving the progress history.
    """
    class EvaluationType(models.TextChoices):
        CHECKPOINT = 'CHECKPOINT', _('Intermediate Progress Checkpoint')
        FINAL_EVALUATION = 'FINAL_EVALUATION', _('Final Outcome Impact Evaluation')

    class EffectivenessClassification(models.TextChoices):
        EFFECTIVE = 'EFFECTIVE', _('Effective (Target Metric Measurably Improved)')
        PARTIALLY_EFFECTIVE = 'PARTIALLY_EFFECTIVE', _('Partially Effective (Target Improved, Mixed Secondary)')
        NO_MEASURABLE_CHANGE = 'NO_MEASURABLE_CHANGE', _('No Measurable Change')
        INEFFECTIVE = 'INEFFECTIVE', _('Ineffective (Target Deteriorated or Persistent Risk)')
        INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', _('Insufficient Post-Intervention Data')

    intervention = models.ForeignKey(
        Intervention,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name=_('intervention')
    )
    checkpoint_number = models.PositiveSmallIntegerField(_('checkpoint sequence number'), default=1)
    evaluation_type = models.CharField(
        _('evaluation type'),
        max_length=30,
        choices=EvaluationType.choices,
        default=EvaluationType.CHECKPOINT
    )
    classification = models.CharField(
        _('effectiveness classification'),
        max_length=30,
        choices=EffectivenessClassification.choices,
        default=EffectivenessClassification.INSUFFICIENT_DATA
    )

    metrics_snapshot = models.JSONField(_('metrics snapshot at checkpoint'), default=dict)
    delta_metrics = models.JSONField(_('metric movements relative to baseline'), default=dict)
    progress_percentage = models.FloatField(_('action checklist progress %'), default=0.0)

    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='conducted_intervention_evaluations',
        verbose_name=_('evaluating educator')
    )
    evaluation_notes = models.TextField(_('evaluator commentary & observations'), blank=True)
    data_quality = models.CharField(_('data quality rating'), max_length=30, default='VALID')

    class Meta:
        verbose_name = _('intervention evaluation checkpoint')
        verbose_name_plural = _('intervention evaluation checkpoints')
        ordering = ['intervention', 'checkpoint_number']

    def __str__(self):
        return f"{self.intervention.title} - {self.get_evaluation_type_display()} #{self.checkpoint_number}: {self.get_classification_display()}"


class InterventionAcknowledgement(TimeStampedModel):
    """
    Student participation acknowledgment and communication record.
    """
    class AckStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Acknowledgment')
        ACCEPTED = 'ACCEPTED', _('Accepted & Acknowledged by Student')
        CLARIFICATION_REQUESTED = 'CLARIFICATION_REQUESTED', _('Clarification Requested by Student')

    intervention = models.OneToOneField(
        Intervention,
        on_delete=models.CASCADE,
        related_name='acknowledgement',
        verbose_name=_('parent intervention')
    )
    status = models.CharField(
        _('acknowledgment status'),
        max_length=30,
        choices=AckStatus.choices,
        default=AckStatus.PENDING
    )
    acknowledged_at = models.DateTimeField(_('acknowledged timestamp'), null=True, blank=True)
    student_notes = models.TextField(_('student feedback / clarification question'), blank=True)

    class Meta:
        verbose_name = _('intervention student acknowledgment')
        verbose_name_plural = _('intervention student acknowledgments')

    def __str__(self):
        return f"Acknowledgment for {self.intervention.title}: {self.get_status_display()}"


class InterventionEscalation(TimeStampedModel):
    """
    Structured escalation record tracking role transfers and reasons.
    """
    intervention = models.ForeignKey(
        Intervention,
        on_delete=models.CASCADE,
        related_name='escalations',
        verbose_name=_('parent intervention')
    )
    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='triggered_escalations',
        verbose_name=_('escalating actor')
    )
    escalated_to_role = models.CharField(_('target authority role'), max_length=50)
    reason = models.TextField(_('escalation justification'))
    previous_status = models.CharField(_('status prior to escalation'), max_length=30)

    class Meta:
        verbose_name = _('intervention escalation record')
        verbose_name_plural = _('intervention escalation records')
        ordering = ['-created_at']

    def __str__(self):
        return f"Escalation of {self.intervention.title} to {self.escalated_to_role}"
