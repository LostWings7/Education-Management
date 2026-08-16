"""
Deterministic Class Relative Analytics Service.
Computes section distributions, class averages, standard deviation, and student relative standing.
"""

import math
from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection
from apps.analytics.schemas.insight import DataQuality
from .data_preparation import AnalyticsDataPreparationService
from .performance import PerformanceAnalyticsService


class ClassRelativeAnalyticsService:
    """
    Computes class section performance distributions and non-evaluative student standing.
    """

    @classmethod
    def calculate_section_distribution(cls, class_section: ClassSection) -> Dict[str, Any]:
        """
        Calculates aggregate statistics and distribution metrics for an entire class section.
        """
        dataset = AnalyticsDataPreparationService.get_section_full_dataset(class_section)
        students = dataset['students']

        student_scores = []
        for s in students:
            perf = PerformanceAnalyticsService.calculate_course_performance(s, class_section)
            if perf.weighted_score is not None:
                student_scores.append(perf.weighted_score)

        n = len(student_scores)
        if n == 0:
            return {
                'class_mean': None,
                'class_median': None,
                'class_min': None,
                'class_max': None,
                'std_dev': None,
                'enrolled_count': len(students),
                'evaluated_count': 0,
                'data_quality': DataQuality.INSUFFICIENT_DATA
            }

        student_scores.sort()
        mean_score = sum(student_scores) / n
        median_score = student_scores[n // 2] if n % 2 != 0 else (student_scores[n // 2 - 1] + student_scores[n // 2]) / 2.0
        min_score = student_scores[0]
        max_score = student_scores[-1]

        variance = sum((s - mean_score) ** 2 for s in student_scores) / n
        std_dev = math.sqrt(variance)

        return {
            'class_mean': round(mean_score, 2),
            'class_median': round(median_score, 2),
            'class_min': round(min_score, 2),
            'class_max': round(max_score, 2),
            'std_dev': round(std_dev, 2),
            'enrolled_count': len(students),
            'evaluated_count': n,
            'data_quality': DataQuality.VALID
        }

    @classmethod
    def calculate_student_standing(
        cls,
        student: StudentProfile,
        class_section: ClassSection
    ) -> Dict[str, Any]:
        """
        Calculates student standing relative to their peers in a section without judgmental labeling.
        """
        dist = cls.calculate_section_distribution(class_section)
        if dist['data_quality'] == DataQuality.INSUFFICIENT_DATA:
            return {
                'student_score': None,
                'class_mean': None,
                'delta_from_mean': None,
                'percentile_rank': None,
                'standing_summary': "Insufficient class data",
                'data_quality': DataQuality.INSUFFICIENT_DATA
            }

        perf = PerformanceAnalyticsService.calculate_course_performance(student, class_section)
        student_score = perf.weighted_score

        if student_score is None:
            return {
                'student_score': None,
                'class_mean': dist['class_mean'],
                'delta_from_mean': None,
                'percentile_rank': None,
                'standing_summary': "No student evaluations yet",
                'data_quality': DataQuality.NOT_AVAILABLE
            }

        delta = student_score - dist['class_mean']

        # Get all scores for percentile calculation
        dataset = AnalyticsDataPreparationService.get_section_full_dataset(class_section)
        all_scores = []
        for s in dataset['students']:
            p = PerformanceAnalyticsService.calculate_course_performance(s, class_section)
            if p.weighted_score is not None:
                all_scores.append(p.weighted_score)

        count_below = sum(1 for s in all_scores if s < student_score)
        count_equal = sum(1 for s in all_scores if s == student_score)
        percentile = ((count_below + (0.5 * count_equal)) / len(all_scores)) * 100.0 if all_scores else 50.0

        if delta >= 2.0:
            summary = f"Above the current class average (+{round(delta, 1)}%)"
        elif delta <= -2.0:
            summary = f"Below the current class average ({round(delta, 1)}%)"
        else:
            summary = "Consistent with the class average"

        return {
            'student_score': round(student_score, 2),
            'class_mean': dist['class_mean'],
            'delta_from_mean': round(delta, 2),
            'percentile_rank': round(percentile, 1),
            'standing_summary': summary,
            'data_quality': DataQuality.VALID
        }
