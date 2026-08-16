"""
Deterministic Performance Analytics Service.
Calculates component percentages (0.0 - 100.0), authoritative weighted scores, standard deviation consistency,
and theoretical vs practical balance without LLM dependencies.
"""

import math
from decimal import Decimal
from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Assessment, Semester
from apps.academic.services import GradingService
from apps.analytics.schemas.insight import PerformanceProfile, DataQuality
from .data_preparation import AnalyticsDataPreparationService


class PerformanceAnalyticsService:
    """
    Computes deterministic student performance profiles, weighted averages, and consistency metrics.
    """

    @classmethod
    def calculate_course_performance(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> PerformanceProfile:
        """
        Calculates student performance in a specific class section.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        assessments = dataset['assessments']
        results = dataset['results']
        submissions = dataset['submissions']

        component_scores: List[float] = []
        weighted_sum = 0.0
        evaluated_weight_sum = 0.0

        for assessment in assessments:
            weight = float(assessment.weightage_percentage)

            if assessment.assessment_type == Assessment.AssessmentType.ASSIGNMENTS:
                # Aggregate graded assignment submissions
                valid_subs = [sub for sub in submissions.values() if sub.obtained_marks is not None and sub.assignment.max_marks > 0]
                if valid_subs:
                    tot_obtained = sum(float(sub.obtained_marks) for sub in valid_subs)
                    tot_max = sum(float(sub.assignment.max_marks) for sub in valid_subs)
                    score_pct = (tot_obtained / tot_max) * 100.0 if tot_max > 0 else 0.0
                    component_scores.append(score_pct)
                    weighted_sum += (score_pct * (weight / 100.0))
                    evaluated_weight_sum += (weight / 100.0)
            else:
                res = results.get(assessment.pk)
                if res and res.marks_obtained is not None and assessment.max_marks > 0:
                    score_pct = (float(res.marks_obtained) / float(assessment.max_marks)) * 100.0
                    component_scores.append(score_pct)
                    weighted_sum += (score_pct * (weight / 100.0))
                    evaluated_weight_sum += (weight / 100.0)

        eval_count = len(component_scores)

        if eval_count == 0:
            return PerformanceProfile(
                course_id=class_section.course.pk,
                course_code=class_section.course.code,
                course_title=class_section.course.title,
                weighted_score=None,
                average_score=None,
                consistency_metric=None,
                consistency_label="No Evaluations Yet",
                completed_weight=0.0,
                evaluations_count=0,
                data_quality=DataQuality.NOT_AVAILABLE
            )

        # Authoritative weighted average normalized on evaluated weights
        weighted_avg = (weighted_sum / evaluated_weight_sum) if evaluated_weight_sum > 0 else (sum(component_scores) / eval_count)
        simple_avg = sum(component_scores) / eval_count

        # Score Consistency (Sample/Population Standard Deviation)
        variance = sum((s - simple_avg) ** 2 for s in component_scores) / eval_count
        std_dev = math.sqrt(variance)

        if std_dev <= 5.0:
            consistency_label = "High Consistency"
        elif std_dev <= 12.0:
            consistency_label = "Moderate Variation"
        else:
            consistency_label = "High Volatility"

        return PerformanceProfile(
            course_id=class_section.course.pk,
            course_code=class_section.course.code,
            course_title=class_section.course.title,
            weighted_score=round(weighted_avg, 2),
            average_score=round(simple_avg, 2),
            consistency_metric=round(std_dev, 2),
            consistency_label=consistency_label,
            completed_weight=round(evaluated_weight_sum * 100.0, 1),
            evaluations_count=eval_count,
            data_quality=DataQuality.VALID
        )

    @classmethod
    def calculate_overall_gpa(cls, student: StudentProfile, semester: Optional[Semester] = None) -> Dict[str, Any]:
        """
        Calculates term GPA and cumulative GPA on 4.0 scale.
        """
        dataset = AnalyticsDataPreparationService.get_student_overall_dataset(student, semester)
        course_datasets = dataset['course_datasets']

        active_weighted_scores = []
        active_credits = []

        for cds in course_datasets:
            perf = cls.calculate_course_performance(student, cds['class_section'], cds)
            if perf.weighted_score is not None:
                active_weighted_scores.append(perf.weighted_score)
                active_credits.append(cds['class_section'].course.credits)

        if not active_weighted_scores:
            return {
                'term_average_percentage': None,
                'term_gpa_4': None,
                'credits_attempted': sum(active_credits),
                'data_quality': DataQuality.NOT_AVAILABLE
            }

        total_credits = sum(active_credits)
        if total_credits > 0:
            term_percentage = sum(score * cred for score, cred in zip(active_weighted_scores, active_credits)) / total_credits
        else:
            term_percentage = sum(active_weighted_scores) / len(active_weighted_scores)

        # 4.0 scale mapping: GPA = (percentage / 100) * 4.0 (or piecewise)
        gpa_4 = min(4.0, max(0.0, (term_percentage / 20.0) - 1.0)) if term_percentage >= 50.0 else (term_percentage / 50.0) * 1.5

        return {
            'term_average_percentage': round(term_percentage, 2),
            'term_gpa_4': round(gpa_4, 2),
            'credits_attempted': total_credits,
            'courses_evaluated_count': len(active_weighted_scores),
            'data_quality': DataQuality.VALID
        }

    @classmethod
    def calculate_theory_vs_practical(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compares theoretical evaluations (Quizzes, Midterm, Final) against practical/applied evaluations (Labs, Assignments, Projects).
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        assessments = dataset['assessments']
        results = dataset['results']
        submissions = dataset['submissions']

        theory_scores: List[float] = []
        practical_scores: List[float] = []

        for assessment in assessments:
            res = results.get(assessment.pk)
            score_pct = None
            if res and res.marks_obtained is not None and assessment.max_marks > 0:
                score_pct = (float(res.marks_obtained) / float(assessment.max_marks)) * 100.0

            if assessment.assessment_type in [Assessment.AssessmentType.QUIZ, Assessment.AssessmentType.MIDTERM, Assessment.AssessmentType.FINAL]:
                if score_pct is not None:
                    theory_scores.append(score_pct)
            elif assessment.assessment_type in [Assessment.AssessmentType.PRACTICAL, Assessment.AssessmentType.PROJECT]:
                if score_pct is not None:
                    practical_scores.append(score_pct)

        # Also add assignment submissions to practical if present
        valid_subs = [sub for sub in submissions.values() if sub.obtained_marks is not None and sub.assignment.max_marks > 0]
        if valid_subs:
            for sub in valid_subs:
                practical_scores.append((float(sub.obtained_marks) / float(sub.assignment.max_marks)) * 100.0)

        theory_avg = sum(theory_scores) / len(theory_scores) if theory_scores else None
        practical_avg = sum(practical_scores) / len(practical_scores) if practical_scores else None

        imbalance_flag = None
        if theory_avg is not None and practical_avg is not None:
            if practical_avg - theory_avg >= 25.0:
                imbalance_flag = "Theoretical Concept Gap (High Practical / Low Theory)"
            elif theory_avg - practical_avg >= 25.0:
                imbalance_flag = "Practical Application Gap (High Theory / Low Lab)"

        return {
            'theory_average': round(theory_avg, 2) if theory_avg is not None else None,
            'practical_average': round(practical_avg, 2) if practical_avg is not None else None,
            'theory_eval_count': len(theory_scores),
            'practical_eval_count': len(practical_scores),
            'imbalance_flag': imbalance_flag,
            'data_quality': DataQuality.VALID if (theory_avg is not None or practical_avg is not None) else DataQuality.NOT_AVAILABLE
        }
