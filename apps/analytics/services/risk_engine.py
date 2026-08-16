"""
Deterministic Academic Risk Engine (Academic Risk Index v1.0).
Computes multi-dimensional risk scores (0.0 - 100.0) with dynamic weight renormalization,
transparent factor evidence breakdown, and deterministic escalation rules without LLM dependency.
"""

from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Enrollment, Semester
from apps.analytics.schemas.insight import (
    RiskEvaluationResult,
    RiskLevel,
    ConfidenceLevel,
    TrendDirection,
    DataQuality
)
from .data_preparation import AnalyticsDataPreparationService
from .performance import PerformanceAnalyticsService
from .attendance import AttendanceAnalyticsService
from .assignments import AssignmentAnalyticsService
from .trends import TrendAnalyticsService


class RiskEngineService:
    """
    Computes explainable, reproducible academic risk evaluations based on actual student records.
    """

    MODEL_VERSION = "1.0"

    # Base heuristic weights (Academic Risk Index v1.0)
    BASE_WEIGHTS = {
        'attendance': 0.25,
        'performance': 0.30,
        'trend': 0.20,
        'assignment': 0.15,
        'historical': 0.10
    }

    @classmethod
    def evaluate_course_risk(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> RiskEvaluationResult:
        """
        Evaluates risk for a student within a specific course offering.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        # 1. Evaluate individual dimension analytics
        att_res = AttendanceAnalyticsService.calculate_course_attendance(student, class_section, dataset=dataset)
        perf_res = PerformanceAnalyticsService.calculate_course_performance(student, class_section, dataset=dataset)
        trend_res = TrendAnalyticsService.calculate_course_trajectory(student, class_section, dataset=dataset)
        assign_res = AssignmentAnalyticsService.calculate_course_assignments(student, class_section, dataset=dataset)

        # Historical baseline
        past_enrollments = dataset.get('past_enrollments', [])

        return cls._compute_composite_risk(
            student=student,
            att_res=att_res,
            perf_res=perf_res,
            trend_res=trend_res,
            assign_res=assign_res,
            past_enrollments=past_enrollments,
            scope_name=f"{class_section.course.code}"
        )

    @classmethod
    def evaluate_overall_risk(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None
    ) -> RiskEvaluationResult:
        """
        Evaluates cumulative institutional academic risk across all active courses.
        """
        dataset = AnalyticsDataPreparationService.get_student_overall_dataset(student, semester)

        att_res = AttendanceAnalyticsService.calculate_overall_attendance(student, semester=semester)
        trend_res = TrendAnalyticsService.calculate_overall_trajectory(student, semester=semester)
        assign_res = AssignmentAnalyticsService.calculate_overall_assignments(student, semester=semester)
        gpa_res = PerformanceAnalyticsService.calculate_overall_gpa(student, semester=semester)

        # Build synthetic PerformanceProfile for overall
        perf_res = PerformanceAnalyticsService.calculate_course_performance(
            student,
            dataset['active_enrollments'][0].class_section,
            dataset['course_datasets'][0]
        ) if dataset['active_enrollments'] else None

        # Override with overall average
        if perf_res and gpa_res['term_average_percentage'] is not None:
            perf_res.weighted_score = gpa_res['term_average_percentage']
            perf_res.average_score = gpa_res['term_average_percentage']
            perf_res.data_quality = DataQuality.VALID

        return cls._compute_composite_risk(
            student=student,
            att_res=att_res,
            perf_res=perf_res,
            trend_res=trend_res,
            assign_res=assign_res,
            past_enrollments=dataset.get('past_enrollments', []),
            scope_name="Institutional Academic Profile"
        )

    @classmethod
    def _compute_composite_risk(
        cls,
        student: StudentProfile,
        att_res: Any,
        perf_res: Any,
        trend_res: Any,
        assign_res: Any,
        past_enrollments: List[Any],
        scope_name: str
    ) -> RiskEvaluationResult:
        contributing_factors = []
        escalations_applied = []

        available_subscores: Dict[str, float] = {}

        # 1. Attendance Dimension (w = 0.25)
        if att_res and att_res.data_quality != DataQuality.INSUFFICIENT_DATA:
            a_pct = att_res.attendance_percentage
            if a_pct >= 85.0:
                r_att = 0.0
                sev = "INFO"
            elif a_pct >= 75.0:
                r_att = 25.0
                sev = "INFO"
            elif a_pct >= 65.0:
                r_att = 60.0
                sev = "WARNING"
            else:
                r_att = 100.0
                sev = "CRITICAL"

            available_subscores['attendance'] = r_att
            contributing_factors.append({
                'dimension': 'Attendance',
                'subscore': r_att,
                'severity': sev,
                'factor': 'Attendance Health',
                'evidence': f"Attendance is {a_pct}% ({att_res.absent_count} absences out of {att_res.total_conducted} sessions), {'below' if a_pct < 75.0 else 'meeting'} the 75.0% threshold."
            })
        else:
            r_att = None

        # 2. Performance Dimension (w = 0.30)
        if perf_res and perf_res.weighted_score is not None:
            s_pct = perf_res.weighted_score
            if s_pct >= 80.0:
                r_perf = 0.0
                sev = "INFO"
            elif s_pct >= 70.0:
                r_perf = 25.0
                sev = "INFO"
            elif s_pct >= 60.0:
                r_perf = 55.0
                sev = "WARNING"
            elif s_pct >= 50.0:
                r_perf = 80.0
                sev = "DANGER"
            else:
                r_perf = 100.0
                sev = "CRITICAL"

            available_subscores['performance'] = r_perf
            contributing_factors.append({
                'dimension': 'Performance',
                'subscore': r_perf,
                'severity': sev,
                'factor': 'Evaluative Course Score',
                'evidence': f"Weighted academic score is {s_pct}% across {perf_res.evaluations_count} evaluated components."
            })
        else:
            r_perf = None

        # 3. Trajectory Dimension (w = 0.20)
        if trend_res and trend_res.data_quality != DataQuality.INSUFFICIENT_DATA:
            direction = trend_res.direction
            slope = trend_res.slope or 0.0
            if direction == TrendDirection.IMPROVING:
                r_trend = 0.0
                sev = "INFO"
            elif direction == TrendDirection.STABLE:
                r_trend = 20.0
                sev = "INFO"
            elif direction == TrendDirection.VOLATILE:
                r_trend = 50.0
                sev = "WARNING"
            elif direction == TrendDirection.DECLINING:
                if slope >= -5.0:
                    r_trend = 70.0
                    sev = "DANGER"
                else:
                    r_trend = 100.0
                    sev = "CRITICAL"
            else:
                r_trend = 20.0
                sev = "INFO"

            available_subscores['trend'] = r_trend
            contributing_factors.append({
                'dimension': 'Trajectory',
                'subscore': r_trend,
                'severity': sev,
                'factor': 'Assessment Trajectory',
                'evidence': f"Assessment trajectory is {direction} with an OLS slope of {slope} points/step."
            })
        else:
            r_trend = None

        # 4. Assignment Dimension (w = 0.15)
        if assign_res and assign_res.data_quality != DataQuality.INSUFFICIENT_DATA:
            m_rate = assign_res.missing_rate
            if m_rate == 0.0:
                r_assign = 0.0
                sev = "INFO"
            elif m_rate <= 15.0:
                r_assign = 25.0
                sev = "INFO"
            elif m_rate <= 30.0:
                r_assign = 55.0
                sev = "WARNING"
            elif m_rate <= 50.0:
                r_assign = 80.0
                sev = "DANGER"
            else:
                r_assign = 100.0
                sev = "CRITICAL"

            available_subscores['assignment'] = r_assign
            contributing_factors.append({
                'dimension': 'Assignments',
                'subscore': r_assign,
                'severity': sev,
                'factor': 'Coursework Completion',
                'evidence': f"Missing {assign_res.missing_count} of {assign_res.total_assigned} assignments ({m_rate}% missing rate)."
            })
        else:
            r_assign = None

        # 5. Historical Baseline Dimension (w = 0.10)
        if past_enrollments:
            past_percentages = [float(e.final_percentage) for e in past_enrollments if e.final_percentage is not None]
            if past_percentages:
                hist_avg = sum(past_percentages) / len(past_percentages)
                if hist_avg >= 80.0:
                    r_hist = 0.0
                    sev = "INFO"
                elif hist_avg >= 70.0:
                    r_hist = 20.0
                    sev = "INFO"
                elif hist_avg >= 60.0:
                    r_hist = 50.0
                    sev = "WARNING"
                else:
                    r_hist = 90.0
                    sev = "DANGER"

                available_subscores['historical'] = r_hist
                contributing_factors.append({
                    'dimension': 'Historical Baseline',
                    'subscore': r_hist,
                    'severity': sev,
                    'factor': 'Prior Semester Baseline',
                    'evidence': f"Historical transcript average across {len(past_percentages)} completed courses is {round(hist_avg, 1)}%."
                })
            else:
                r_hist = None
        else:
            r_hist = None

        # Dynamic Weight Renormalization
        if not available_subscores:
            return RiskEvaluationResult(
                risk_level=RiskLevel.LOW,
                composite_score=0.0,
                risk_model_version=cls.MODEL_VERSION,
                data_confidence=ConfidenceLevel.LOW,
                attendance_risk=None,
                performance_risk=None,
                trend_risk=None,
                assignment_risk=None,
                historical_risk=None,
                contributing_factors=[],
                escalations_applied=[],
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        available_weight_sum = sum(cls.BASE_WEIGHTS[dim] for dim in available_subscores.keys())

        # Confidence rating
        if available_weight_sum >= 1.0:
            confidence = ConfidenceLevel.HIGH
        elif available_weight_sum >= 0.85:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # Composite score
        composite_score = sum(
            (cls.BASE_WEIGHTS[dim] / available_weight_sum) * subscore
            for dim, subscore in available_subscores.items()
        )

        # Baseline Risk Level
        if composite_score < 25.0:
            risk_level = RiskLevel.LOW
        elif composite_score < 50.0:
            risk_level = RiskLevel.MODERATE
        elif composite_score < 75.0:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        # Deterministic Escalation Rules
        # Rule 1: Critical Attendance (<60% -> at least HIGH; <50% -> CRITICAL)
        if att_res and att_res.data_quality != DataQuality.INSUFFICIENT_DATA:
            if att_res.attendance_percentage < 50.0:
                escalations_applied.append(f"Critical attendance deficit ({att_res.attendance_percentage}% < 50.0%).")
                if risk_level != RiskLevel.CRITICAL:
                    risk_level = RiskLevel.CRITICAL
            elif att_res.attendance_percentage < 60.0:
                escalations_applied.append(f"Attendance deficit ({att_res.attendance_percentage}% < 60.0%).")
                if risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]:
                    risk_level = RiskLevel.HIGH

        # Rule 2: Three consecutive results strictly below 50.0%
        if trend_res and trend_res.data_quality != DataQuality.INSUFFICIENT_DATA and len(trend_res.scores_sequence) >= 3:
            last_3 = trend_res.scores_sequence[-3:]
            if all(s < 50.0 for s in last_3):
                escalations_applied.append("Three consecutive failing evaluations (<50.0%) detected.")
                if risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]:
                    risk_level = RiskLevel.HIGH

        return RiskEvaluationResult(
            risk_level=risk_level,
            composite_score=round(composite_score, 1),
            risk_model_version=cls.MODEL_VERSION,
            data_confidence=confidence,
            attendance_risk=r_att,
            performance_risk=r_perf,
            trend_risk=r_trend,
            assignment_risk=r_assign,
            historical_risk=r_hist,
            contributing_factors=contributing_factors,
            escalations_applied=escalations_applied,
            data_quality=DataQuality.VALID
        )
