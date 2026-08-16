"""
Deterministic Academic What-If Simulation Service.
Computes hypothetical score projections, attendance delta impacts, and target grade solvers
strictly aligned with the Phase 2 GradingService architecture.
"""

from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Assessment
from apps.analytics.schemas.insight import WhatIfResult, DataQuality
from .data_preparation import AnalyticsDataPreparationService
from .performance import PerformanceAnalyticsService
from .attendance import AttendanceAnalyticsService


class WhatIfSimulationService:
    """
    Simulates academic trajectories and solves target grade requirements deterministically without modifying records.
    """

    @classmethod
    def simulate_next_assessment(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        hypothetical_score: float,
        assessment_weight: float = 20.0
    ) -> WhatIfResult:
        """
        Simulates the new weighted course grade if the student scores hypothetical_score (0.0-100.0) on an upcoming evaluation.
        """
        perf = PerformanceAnalyticsService.calculate_course_performance(student, class_section)
        current_val = perf.weighted_score if perf.weighted_score is not None else 0.0

        current_weight_frac = perf.completed_weight / 100.0
        next_weight_frac = assessment_weight / 100.0

        total_new_weight = current_weight_frac + next_weight_frac
        if total_new_weight > 0:
            current_points = current_val * current_weight_frac
            new_points = hypothetical_score * next_weight_frac
            projected_val = (current_points + new_points) / total_new_weight
        else:
            projected_val = hypothetical_score

        delta = projected_val - current_val
        direction_str = f"+{round(delta, 1)}%" if delta >= 0 else f"{round(delta, 1)}%"

        explanation = (
            f"If you score {hypothetical_score}% on a {assessment_weight}% component, "
            f"your weighted course grade will move from {round(current_val, 1)}% to {round(projected_val, 1)}% ({direction_str})."
        )

        return WhatIfResult(
            simulation_type="NEXT_ASSESSMENT",
            current_value=round(current_val, 2),
            projected_value=round(projected_val, 2),
            required_score=None,
            is_feasible=True,
            explanation=explanation,
            data_quality=DataQuality.VALID
        )

    @classmethod
    def simulate_attendance_impact(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        attended_delta: int = 0,
        missed_delta: int = 0
    ) -> WhatIfResult:
        """
        Simulates attendance percentage change if student attends/misses additional sessions.
        """
        att = AttendanceAnalyticsService.calculate_course_attendance(student, class_section)
        current_pct = att.attendance_percentage

        current_credits = float(att.present_count) + (0.5 * float(att.late_count))
        current_conducted = float(att.total_conducted)

        new_credits = current_credits + float(attended_delta)
        new_conducted = current_conducted + float(attended_delta + missed_delta)

        if new_conducted > 0:
            projected_pct = (new_credits / new_conducted) * 100.0
        else:
            projected_pct = 100.0

        delta = projected_pct - current_pct
        direction_str = f"+{round(delta, 1)}%" if delta >= 0 else f"{round(delta, 1)}%"

        explanation = (
            f"Attending {attended_delta} and missing {missed_delta} upcoming sessions moves your attendance from "
            f"{round(current_pct, 1)}% to {round(projected_pct, 1)}% ({direction_str})."
        )

        return WhatIfResult(
            simulation_type="ATTENDANCE_IMPACT",
            current_value=round(current_pct, 2),
            projected_value=round(projected_pct, 2),
            required_score=None,
            is_feasible=True,
            explanation=explanation,
            data_quality=DataQuality.VALID
        )

    @classmethod
    def solve_required_score_for_target(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        target_grade_percentage: float
    ) -> WhatIfResult:
        """
        Solves the required average score on all remaining assessments to achieve target_grade_percentage (0.0-100.0).
        """
        dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)
        assessments = dataset['assessments']
        results = dataset['results']
        submissions = dataset['submissions']

        evaluated_points = 0.0
        evaluated_weight = 0.0

        for a in assessments:
            weight = float(a.weightage_percentage)
            if a.assessment_type == Assessment.AssessmentType.ASSIGNMENTS:
                valid_subs = [sub for sub in submissions.values() if sub.obtained_marks is not None and sub.assignment.max_marks > 0]
                if valid_subs:
                    tot_obtained = sum(float(sub.obtained_marks) for sub in valid_subs)
                    tot_max = sum(float(sub.assignment.max_marks) for sub in valid_subs)
                    score_pct = (tot_obtained / tot_max) * 100.0 if tot_max > 0 else 0.0
                    evaluated_points += score_pct * weight
                    evaluated_weight += weight
            else:
                res = results.get(a.pk)
                if res and res.marks_obtained is not None and a.max_marks > 0:
                    score_pct = (float(res.marks_obtained) / float(a.max_marks)) * 100.0
                    evaluated_points += score_pct * weight
                    evaluated_weight += weight

        remaining_weight = max(0.0, 100.0 - evaluated_weight)
        current_weighted_avg = (evaluated_points / evaluated_weight) if evaluated_weight > 0 else 0.0

        if remaining_weight <= 0.0:
            # 100% of course completed
            is_feasible = (current_weighted_avg >= target_grade_percentage)
            explanation = (
                f"Course evaluations are 100% completed. Final grade is locked at {round(current_weighted_avg, 1)}%. "
                f"{'Target achieved.' if is_feasible else 'Target unattainable.'}"
            )
            return WhatIfResult(
                simulation_type="TARGET_GRADE_SOLVER",
                current_value=round(current_weighted_avg, 2),
                projected_value=round(current_weighted_avg, 2),
                required_score=None,
                is_feasible=is_feasible,
                explanation=explanation,
                data_quality=DataQuality.VALID
            )

        # Formula: S_req = (Target * 100 - Evaluated_Points) / Remaining_Weight
        target_total_points = target_grade_percentage * 100.0
        needed_points = target_total_points - evaluated_points
        required_score = needed_points / remaining_weight

        if required_score <= 0.0:
            is_feasible = True
            req_clamped = 0.0
            explanation = (
                f"You already have enough accumulated points to secure a target of {target_grade_percentage}%. "
                f"Required average on the remaining {round(remaining_weight, 1)}% coursework is 0.0%."
            )
        elif required_score <= 100.0:
            is_feasible = True
            req_clamped = round(required_score, 1)
            explanation = (
                f"To achieve a final course grade of {target_grade_percentage}%, you need an average score of "
                f"{req_clamped}% across the remaining {round(remaining_weight, 1)}% of course assessments."
            )
        else:
            is_feasible = False
            req_clamped = round(required_score, 1)
            explanation = (
                f"Target grade of {target_grade_percentage}% is mathematically impossible with remaining assessments "
                f"because it requires scoring {req_clamped}% across the remaining {round(remaining_weight, 1)}% weight."
            )

        return WhatIfResult(
            simulation_type="TARGET_GRADE_SOLVER",
            current_value=round(current_weighted_avg, 2),
            projected_value=round(target_grade_percentage, 2),
            required_score=round(required_score, 2),
            is_feasible=is_feasible,
            explanation=explanation,
            data_quality=DataQuality.VALID
        )
