"""
Checkpoint & Intermediate Evaluation Service for Phase 4 Interventions.
Records immutable progress checkpoints throughout an intervention's lifecycle.
"""

from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from apps.core.models import AuditLog
from apps.analytics.schemas.insight import DataQuality
from apps.analytics.services import (
    RiskEngineService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    PerformanceAnalyticsService,
    TopicAnalyticsService
)
from apps.interventions.models import Intervention, InterventionEvaluation


class InterventionCheckpointService:
    """
    Manages progress checkpoints and intermediate diagnostic evaluations.
    """

    @classmethod
    def capture_metrics_snapshot(cls, intervention: Intervention) -> Dict[str, Any]:
        """
        Evaluate current academic metrics for the intervention's student and section.
        """
        student = intervention.student
        section = intervention.class_section

        risk_res = RiskEngineService.evaluate_course_risk(student, section)
        att_res = AttendanceAnalyticsService.calculate_course_attendance(student, section)
        assign_res = AssignmentAnalyticsService.calculate_course_assignments(student, section)
        perf_res = PerformanceAnalyticsService.calculate_course_performance(student, section)

        topic_score = None
        if intervention.topic:
            topics_res = TopicAnalyticsService.calculate_topic_mastery(student, section)
            for t in topics_res:
                if t.get('topic_id') == intervention.topic.pk:
                    topic_score = t.get('score_percentage')
                    break

        return {
            'captured_at': timezone.now().isoformat(),
            'risk_score': risk_res.composite_score if risk_res else 0.0,
            'risk_level': str(risk_res.risk_level) if risk_res else 'LOW',
            'attendance_percentage': att_res.attendance_percentage if att_res else 100.0,
            'missing_assignment_rate': assign_res.missing_rate if assign_res else 0.0,
            'completion_rate': assign_res.completion_rate if assign_res else 100.0,
            'weighted_score': perf_res.weighted_score if perf_res else None,
            'topic_score': topic_score,
            'data_quality': 'VALID'
        }

    @classmethod
    def calculate_metric_deltas(cls, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate deltas between baseline and checkpoint metrics.
        """
        deltas = {}

        # Delta Risk (Positive means risk reduced)
        b_risk = baseline.get('risk_score')
        c_risk = current.get('risk_score')
        if b_risk is not None and c_risk is not None:
            deltas['delta_risk'] = round(float(b_risk) - float(c_risk), 1)

        # Delta Attendance
        b_att = baseline.get('attendance_percentage')
        c_att = current.get('attendance_percentage')
        if b_att is not None and c_att is not None:
            deltas['delta_attendance'] = round(float(c_att) - float(b_att), 1)

        # Delta Assignment Completion
        b_comp = baseline.get('completion_rate')
        c_comp = current.get('completion_rate')
        if b_comp is not None and c_comp is not None:
            deltas['delta_assignment_completion'] = round(float(c_comp) - float(b_comp), 1)

        # Delta Weighted Score
        b_perf = baseline.get('weighted_score')
        c_perf = current.get('weighted_score')
        if b_perf is not None and c_perf is not None:
            deltas['delta_performance'] = round(float(c_perf) - float(b_perf), 1)

        # Delta Topic
        b_topic = baseline.get('topic_score')
        c_topic = current.get('topic_score')
        if b_topic is not None and c_topic is not None:
            deltas['delta_topic'] = round(float(c_topic) - float(b_topic), 1)

        return deltas

    @classmethod
    @transaction.atomic
    def record_checkpoint(
        cls,
        intervention: Intervention,
        evaluator_user,
        notes: str = ""
    ) -> InterventionEvaluation:
        """
        Create an immutable intermediate checkpoint record.
        """
        current_metrics = cls.capture_metrics_snapshot(intervention)
        deltas = cls.calculate_metric_deltas(intervention.baseline_metrics, current_metrics)
        progress_pct = intervention.action_progress_percentage

        next_number = intervention.evaluations.count() + 1
        checkpoint = InterventionEvaluation.objects.create(
            intervention=intervention,
            checkpoint_number=next_number,
            evaluation_type=InterventionEvaluation.EvaluationType.CHECKPOINT,
            classification=InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
            metrics_snapshot=current_metrics,
            delta_metrics=deltas,
            progress_percentage=progress_pct,
            evaluator=evaluator_user,
            evaluation_notes=notes,
            data_quality='VALID'
        )

        AuditLog.log_action(
            user=evaluator_user,
            action="RECORD_INTERVENTION_CHECKPOINT",
            details={
                "intervention_id": intervention.pk,
                "checkpoint_number": next_number,
                "progress_percentage": progress_pct,
                "deltas": deltas
            }
        )
        return checkpoint
