"""
Target-Aware Impact & Effectiveness Evaluation Service for Phase 4.
Evaluates deterministic pre/post movements in primary target metrics and records non-causal disclosures.
"""

from typing import Dict, Any, Tuple
from django.utils import timezone
from django.db import transaction

from apps.core.models import AuditLog
from apps.analytics.schemas.insight import DataQuality
from apps.interventions.models import (
    Intervention,
    InterventionEvaluation
)
from .checkpoint_service import InterventionCheckpointService


class InterventionImpactService:
    """
    Evaluates final outcome effectiveness with target-metric awareness.
    """

    NON_CAUSAL_DISCLAIMER = (
        "Academic performance and participation indicators improved following the completion "
        "of the support plan. Statistical association does not establish sole causality."
    )

    @classmethod
    def evaluate_target_effectiveness(
        cls,
        intervention: Intervention,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        deltas: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """
        Determine target-aware effectiveness classification:
        Returns (Classification, SummaryText, DataQuality).
        """
        target = intervention.primary_target_metric

        # Check primary target availability
        if target == Intervention.TargetMetric.ATTENDANCE:
            b_val = baseline.get('attendance_percentage')
            c_val = current.get('attendance_percentage')
            d_val = deltas.get('delta_attendance')
            if b_val is None or c_val is None or d_val is None:
                return (
                    InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
                    "Insufficient attendance tracking records to evaluate recovery impact.",
                    'INSUFFICIENT_DATA'
                )
            target_improved = (c_val >= 75.0) or (d_val >= 5.0)
            target_deteriorated = (d_val <= -5.0)
            target_summary = f"Attendance moved from {b_val}% to {c_val}% (Delta: {d_val:+}%)."

        elif target == Intervention.TargetMetric.ASSIGNMENT_COMPLETION:
            b_val = baseline.get('completion_rate')
            c_val = current.get('completion_rate')
            d_val = deltas.get('delta_assignment_completion')
            if b_val is None or c_val is None or d_val is None:
                return (
                    InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
                    "Insufficient assignment submission records to evaluate coursework recovery.",
                    'INSUFFICIENT_DATA'
                )
            target_improved = (c_val >= 75.0) or (d_val >= 15.0)
            target_deteriorated = (d_val <= -10.0)
            target_summary = f"Assignment completion rate moved from {b_val}% to {c_val}% (Delta: {d_val:+}%)."

        elif target == Intervention.TargetMetric.TOPIC_MASTERY:
            b_val = baseline.get('topic_score')
            c_val = current.get('topic_score')
            d_val = deltas.get('delta_topic')
            if b_val is None or c_val is None or d_val is None:
                return (
                    InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
                    "No post-intervention assessments covering this specific syllabus topic were recorded.",
                    'INSUFFICIENT_DATA'
                )
            target_improved = (c_val >= 70.0) or (d_val >= 8.0)
            target_deteriorated = (d_val <= -5.0)
            target_summary = f"Topic mastery score moved from {b_val}% to {c_val}% (Delta: {d_val:+}%)."

        elif target in [Intervention.TargetMetric.ASSESSMENT_PERFORMANCE, Intervention.TargetMetric.ANOMALY_RECOVERY, Intervention.TargetMetric.THEORY_PERFORMANCE]:
            b_val = baseline.get('weighted_score')
            c_val = current.get('weighted_score')
            d_val = deltas.get('delta_performance')
            if b_val is None or c_val is None or d_val is None:
                return (
                    InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
                    "No new post-intervention assessment grades recorded to evaluate academic recovery.",
                    'INSUFFICIENT_DATA'
                )
            target_improved = (c_val >= 70.0) or (d_val >= 5.0)
            target_deteriorated = (d_val <= -5.0)
            target_summary = f"Weighted course score moved from {b_val}% to {c_val}% (Delta: {d_val:+}%)."

        else:
            return (
                InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA,
                "Target metric configuration undefined.",
                'NOT_AVAILABLE'
            )

        # Check secondary metrics
        d_risk = deltas.get('delta_risk', 0.0)
        risk_worsened = (d_risk <= -10.0) # Risk score increased by 10+ points

        # Classification Engine
        if target_deteriorated or risk_worsened:
            classification = InterventionEvaluation.EffectivenessClassification.INEFFECTIVE
            summary = f"INEFFECTIVE: {target_summary} Further faculty intervention or advisor escalation recommended."
        elif target_improved:
            if d_risk < -5.0:
                classification = InterventionEvaluation.EffectivenessClassification.PARTIALLY_EFFECTIVE
                summary = f"PARTIALLY EFFECTIVE: {target_summary} Secondary indicators require ongoing monitoring. {cls.NON_CAUSAL_DISCLAIMER}"
            else:
                classification = InterventionEvaluation.EffectivenessClassification.EFFECTIVE
                summary = f"EFFECTIVE: {target_summary} {cls.NON_CAUSAL_DISCLAIMER}"
        elif abs(d_val) < 3.0:
            classification = InterventionEvaluation.EffectivenessClassification.NO_MEASURABLE_CHANGE
            summary = f"NO MEASURABLE CHANGE: {target_summary} Metrics remained within normal variance."
        else:
            classification = InterventionEvaluation.EffectivenessClassification.PARTIALLY_EFFECTIVE
            summary = f"PARTIALLY EFFECTIVE: {target_summary}"

        return (classification, summary, 'VALID')

    @classmethod
    @transaction.atomic
    def evaluate_and_record_outcome(
        cls,
        intervention: Intervention,
        evaluator_user,
        evaluator_notes: str = ""
    ) -> InterventionEvaluation:
        """
        Run final target-aware impact analysis, record final evaluation checkpoint,
        and update intervention status to the resulting outcome.
        """
        current_metrics = InterventionCheckpointService.capture_metrics_snapshot(intervention)
        deltas = InterventionCheckpointService.calculate_metric_deltas(intervention.baseline_metrics, current_metrics)
        progress_pct = intervention.action_progress_percentage

        classification, summary_text, data_quality = cls.evaluate_target_effectiveness(
            intervention=intervention,
            baseline=intervention.baseline_metrics,
            current=current_metrics,
            deltas=deltas
        )

        next_number = intervention.evaluations.count() + 1
        final_eval = InterventionEvaluation.objects.create(
            intervention=intervention,
            checkpoint_number=next_number,
            evaluation_type=InterventionEvaluation.EvaluationType.FINAL_EVALUATION,
            classification=classification,
            metrics_snapshot=current_metrics,
            delta_metrics=deltas,
            progress_percentage=progress_pct,
            evaluator=evaluator_user,
            evaluation_notes=f"{summary_text}\n{evaluator_notes}".strip(),
            data_quality=data_quality
        )

        # Update Intervention record
        intervention.followup_metrics = current_metrics
        intervention.effectiveness_summary = summary_text
        intervention.evaluated_at = timezone.now()

        # Update status based on classification if not already terminal
        status_map = {
            InterventionEvaluation.EffectivenessClassification.EFFECTIVE: Intervention.Status.EFFECTIVE,
            InterventionEvaluation.EffectivenessClassification.PARTIALLY_EFFECTIVE: Intervention.Status.PARTIALLY_EFFECTIVE,
            InterventionEvaluation.EffectivenessClassification.NO_MEASURABLE_CHANGE: Intervention.Status.NO_MEASURABLE_CHANGE,
            InterventionEvaluation.EffectivenessClassification.INEFFECTIVE: Intervention.Status.INEFFECTIVE,
            InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA: Intervention.Status.EVALUATING
        }
        new_status = status_map.get(classification, Intervention.Status.EVALUATING)
        intervention.status = new_status
        intervention.save()

        AuditLog.log_action(
            user=evaluator_user,
            action="EVALUATE_INTERVENTION_OUTCOME",
            details={
                "intervention_id": intervention.pk,
                "student_id": intervention.student.student_id,
                "target_metric": intervention.primary_target_metric,
                "classification": classification,
                "deltas": deltas,
                "new_status": intervention.status
            }
        )
        return final_eval
