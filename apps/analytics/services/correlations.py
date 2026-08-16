"""
Deterministic Statistical Correlation Service.
Calculates Pearson product-moment correlation coefficient r with sample size guards (N >= 10),
zero-variance protection, and explicit non-causal disclosures.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from apps.academic.models import ClassSection
from apps.analytics.schemas.insight import CorrelationResult, DataQuality
from .data_preparation import AnalyticsDataPreparationService
from .performance import PerformanceAnalyticsService
from .attendance import AttendanceAnalyticsService


class CorrelationAnalyticsService:
    """
    Computes statistical correlations across paired academic metrics with strict non-causal disclosures.
    """

    MIN_SAMPLE_SIZE = 10  # Minimum 10 paired observations required

    @classmethod
    def calculate_attendance_vs_performance(cls, class_section: ClassSection) -> CorrelationResult:
        """
        Calculates correlation between attendance rate and final weighted score across students in a class section.
        """
        dataset = AnalyticsDataPreparationService.get_section_full_dataset(class_section)
        students = dataset['students']

        pairs: List[Tuple[float, float]] = []
        for s in students:
            att = AttendanceAnalyticsService.calculate_course_attendance(s, class_section)
            perf = PerformanceAnalyticsService.calculate_course_performance(s, class_section)
            if att.data_quality == DataQuality.VALID and perf.weighted_score is not None:
                pairs.append((att.attendance_percentage, perf.weighted_score))

        return cls.compute_pearson(
            pairs,
            metric_x="Attendance Percentage (0-100%)",
            metric_y="Weighted Assessment Score (0-100%)"
        )

    @classmethod
    def compute_pearson(
        cls,
        pairs: List[Tuple[float, float]],
        metric_x: str = "Metric X",
        metric_y: str = "Metric Y"
    ) -> CorrelationResult:
        """
        Computes Pearson r from a list of (x, y) numeric tuples.
        """
        n = len(pairs)

        if n < cls.MIN_SAMPLE_SIZE:
            return CorrelationResult(
                metric_x=metric_x,
                metric_y=metric_y,
                pearson_r=None,
                sample_size=n,
                relationship_description=f"Insufficient sample size (N = {n} < {cls.MIN_SAMPLE_SIZE}) for meaningful correlation analysis.",
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        x_vals = [p[0] for p in pairs]
        y_vals = [p[1] for p in pairs]

        mean_x = sum(x_vals) / n
        mean_y = sum(y_vals) / n

        var_x = sum((x - mean_x) ** 2 for x in x_vals)
        var_y = sum((y - mean_y) ** 2 for y in y_vals)

        # Zero variance guard
        if var_x == 0.0 or var_y == 0.0:
            return CorrelationResult(
                metric_x=metric_x,
                metric_y=metric_y,
                pearson_r=None,
                sample_size=n,
                relationship_description="Correlation undefined because one variable has zero variance across the sample.",
                data_quality=DataQuality.UNDEFINED
            )

        cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
        r = cov_xy / math.sqrt(var_x * var_y)

        # Clamp floating inaccuracies
        r = max(-1.0, min(1.0, r))

        if r >= 0.7:
            rel = f"Strong positive association (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."
        elif r >= 0.4:
            rel = f"Moderate positive association (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."
        elif r >= 0.1:
            rel = f"Weak positive association (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."
        elif r > -0.1:
            rel = f"No meaningful linear correlation (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."
        elif r > -0.4:
            rel = f"Weak negative association (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."
        else:
            rel = f"Negative association (r = {round(r, 2)}) between {metric_x} and {metric_y} across {n} students."

        return CorrelationResult(
            metric_x=metric_x,
            metric_y=metric_y,
            pearson_r=round(r, 3),
            sample_size=n,
            relationship_description=rel,
            data_quality=DataQuality.VALID
        )
