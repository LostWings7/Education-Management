"""
Deterministic Academic Anomaly Detection Service.
Detects acute score plunges and unusual surges using baseline deviations and floor-guarded Z-scores without hardcoded personas.
"""

import math
from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Assessment
from apps.analytics.schemas.insight import AnomalyEvent, DataQuality
from .data_preparation import AnalyticsDataPreparationService


class AnomalyDetectionService:
    """
    Computes statistical baseline deviations and detects sudden acute performance changes.
    """

    MIN_BASELINE_OBSERVATIONS = 3
    STD_DEV_FLOOR = 3.0
    SUDDEN_DROP_THRESHOLD = 25.0   # Percentage points
    SUDDEN_SURGE_THRESHOLD = 30.0  # Percentage points
    Z_THRESHOLD = 2.5

    @classmethod
    def detect_course_anomaly(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> AnomalyEvent:
        """
        Detects anomalies in assessment evaluations within a class section.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        assessments = dataset['assessments']
        results = dataset['results']

        scores: List[float] = []
        for a in assessments:
            res = results.get(a.pk)
            if res and res.marks_obtained is not None and a.max_marks > 0:
                score_pct = (float(res.marks_obtained) / float(a.max_marks)) * 100.0
                scores.append(score_pct)

        return cls.detect_from_sequence(scores, context_name=f"{class_section.course.code}")

    @classmethod
    def detect_from_sequence(cls, scores: List[float], context_name: str = "Coursework") -> AnomalyEvent:
        """
        Detects anomaly given an ordered sequence of numeric percentage scores.
        """
        total_evals = len(scores)

        if total_evals <= cls.MIN_BASELINE_OBSERVATIONS:
            return AnomalyEvent(
                is_anomaly=False,
                anomaly_type="NONE",
                severity="NONE",
                baseline_mean=None,
                baseline_std=None,
                current_score=scores[-1] if scores else None,
                delta=None,
                z_score=None,
                summary="Insufficient baseline observations for anomaly detection.",
                evidence={},
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        baseline_scores = scores[:-1]
        current_score = scores[-1]
        k = len(baseline_scores)

        baseline_mean = sum(baseline_scores) / k
        variance = sum((s - baseline_mean) ** 2 for s in baseline_scores) / k
        baseline_std = math.sqrt(variance)

        effective_std = max(baseline_std, cls.STD_DEV_FLOOR)
        z_score = (current_score - baseline_mean) / effective_std
        drop_delta = baseline_mean - current_score

        # Check for Acute Drop
        if drop_delta >= cls.SUDDEN_DROP_THRESHOLD or z_score <= -cls.Z_THRESHOLD:
            summary = (
                f"Acute performance drop detected in {context_name}: "
                f"Recent score of {round(current_score, 1)}% is {round(drop_delta, 1)} points below "
                f"the historical baseline mean of {round(baseline_mean, 1)}% (Z = {round(z_score, 2)})."
            )
            return AnomalyEvent(
                is_anomaly=True,
                anomaly_type="ACUTE_DROP",
                severity="CRITICAL",
                baseline_mean=round(baseline_mean, 2),
                baseline_std=round(baseline_std, 2),
                current_score=round(current_score, 2),
                delta=round(drop_delta, 2),
                z_score=round(z_score, 2),
                summary=summary,
                evidence={
                    'baseline_scores': [round(s, 1) for s in baseline_scores],
                    'baseline_mean': round(baseline_mean, 2),
                    'baseline_std': round(baseline_std, 2),
                    'current_score': round(current_score, 2),
                    'drop_points': round(drop_delta, 2),
                    'z_score': round(z_score, 2),
                    'threshold_drop': cls.SUDDEN_DROP_THRESHOLD
                },
                data_quality=DataQuality.VALID
            )

        # Check for Acute Surge
        surge_delta = current_score - baseline_mean
        if surge_delta >= cls.SUDDEN_SURGE_THRESHOLD or z_score >= cls.Z_THRESHOLD:
            summary = (
                f"Unusual performance surge detected in {context_name}: "
                f"Recent score of {round(current_score, 1)}% is +{round(surge_delta, 1)} points above "
                f"the baseline mean of {round(baseline_mean, 1)}% (Z = {round(z_score, 2)})."
            )
            return AnomalyEvent(
                is_anomaly=True,
                anomaly_type="ACUTE_SURGE",
                severity="WARNING",
                baseline_mean=round(baseline_mean, 2),
                baseline_std=round(baseline_std, 2),
                current_score=round(current_score, 2),
                delta=round(surge_delta, 2),
                z_score=round(z_score, 2),
                summary=summary,
                evidence={
                    'baseline_scores': [round(s, 1) for s in baseline_scores],
                    'baseline_mean': round(baseline_mean, 2),
                    'baseline_std': round(baseline_std, 2),
                    'current_score': round(current_score, 2),
                    'surge_points': round(surge_delta, 2),
                    'z_score': round(z_score, 2)
                },
                data_quality=DataQuality.VALID
            )

        return AnomalyEvent(
            is_anomaly=False,
            anomaly_type="NONE",
            severity="NONE",
            baseline_mean=round(baseline_mean, 2),
            baseline_std=round(baseline_std, 2),
            current_score=round(current_score, 2),
            delta=round(drop_delta, 2),
            z_score=round(z_score, 2),
            summary="Performance within normal expected variance.",
            evidence={'baseline_mean': round(baseline_mean, 2), 'current_score': round(current_score, 2)},
            data_quality=DataQuality.VALID
        )
