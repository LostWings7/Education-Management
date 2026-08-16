"""
Deterministic Assessment Trajectory and Trend Service.
Calculates OLS linear slope on sequential assessment evaluations (0.0 - 100.0) with minimum-data guards (n >= 3).
"""

import math
from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Assessment, AssessmentResult, Semester
from apps.analytics.schemas.insight import TrendResult, TrendDirection, DataQuality
from .data_preparation import AnalyticsDataPreparationService


class TrendAnalyticsService:
    """
    Computes deterministic assessment trajectory slopes and performance trend classifications.
    """

    MINIMUM_OBSERVATIONS = 3  # Minimum 3 sequential evaluations required

    @classmethod
    def calculate_course_trajectory(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> TrendResult:
        """
        Calculates the assessment trajectory slope for a student in a class section.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        assessments = dataset['assessments']
        results = dataset['results']

        scores_sequence: List[float] = []

        for assessment in assessments:
            res = results.get(assessment.pk)
            if res and res.marks_obtained is not None and assessment.max_marks > 0:
                score_pct = (float(res.marks_obtained) / float(assessment.max_marks)) * 100.0
                scores_sequence.append(score_pct)

        return cls._compute_trajectory_from_sequence(scores_sequence)

    @classmethod
    def calculate_overall_trajectory(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None
    ) -> TrendResult:
        """
        Calculates chronological assessment trajectory across all active courses in a semester.
        """
        dataset = AnalyticsDataPreparationService.get_student_overall_dataset(student, semester)
        course_datasets = dataset['course_datasets']

        all_dated_results = []
        for cds in course_datasets:
            for assessment in cds['assessments']:
                res = cds['results'].get(assessment.pk)
                if res and res.marks_obtained is not None and assessment.max_marks > 0:
                    score_pct = (float(res.marks_obtained) / float(assessment.max_marks)) * 100.0
                    all_dated_results.append((assessment.date, res.created_at, score_pct))

        # Sort chronologically
        all_dated_results.sort(key=lambda x: (x[0], x[1]))
        scores_sequence = [item[2] for item in all_dated_results]

        return cls._compute_trajectory_from_sequence(scores_sequence)

    @classmethod
    def calculate_linear_trend(cls, scores: List[float]) -> TrendResult:
        """
        Public method to compute deterministic trajectory and OLS linear trend from a sequence of float values.
        """
        return cls._compute_trajectory_from_sequence(scores)

    @classmethod
    def _compute_trajectory_from_sequence(cls, scores: List[float]) -> TrendResult:
        n = len(scores)

        if n < cls.MINIMUM_OBSERVATIONS:
            return TrendResult(
                direction=TrendDirection.INSUFFICIENT_DATA,
                slope=None,
                observations_count=n,
                scores_sequence=scores,
                std_dev=0.0,
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        # OLS slope calculation on sequence index t = 1, 2, ... n
        sum_t = sum(range(1, n + 1))
        sum_t2 = sum(i * i for i in range(1, n + 1))
        sum_s = sum(scores)
        sum_ts = sum(i * score for i, score in enumerate(scores, start=1))

        numerator = (n * sum_ts) - (sum_t * sum_s)
        denominator = (n * sum_t2) - (sum_t * sum_t)

        slope = (numerator / denominator) if denominator != 0 else 0.0

        mean_s = sum_s / n
        variance = sum((s - mean_s) ** 2 for s in scores) / n
        std_dev = math.sqrt(variance)

        # Classification boundaries
        if slope >= 2.5:
            direction = TrendDirection.IMPROVING
        elif slope <= -2.5:
            direction = TrendDirection.DECLINING
        elif std_dev <= 8.0:
            direction = TrendDirection.STABLE
        else:
            direction = TrendDirection.VOLATILE

        return TrendResult(
            direction=direction,
            slope=round(slope, 2),
            observations_count=n,
            scores_sequence=[round(s, 2) for s in scores],
            std_dev=round(std_dev, 2),
            data_quality=DataQuality.VALID
        )
