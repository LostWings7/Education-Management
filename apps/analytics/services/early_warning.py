"""
Deterministic Early Warning Detection Service.
Identifies critical early warning triggers and acute risk events before severe outcomes materialize.
"""

from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Semester
from apps.analytics.schemas.insight import InsightObject, Severity, DataQuality, ConfidenceLevel
from .data_preparation import AnalyticsDataPreparationService
from .attendance import AttendanceAnalyticsService
from .assignments import AssignmentAnalyticsService
from .trends import TrendAnalyticsService
from .anomalies import AnomalyDetectionService


class EarlyWarningService:
    """
    Scans student academic signals and generates deterministic early-warning alerts for instructors and advisors.
    """

    @classmethod
    def scan_course_signals(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> List[InsightObject]:
        """
        Scans a student's course record and produces any triggered early warning insight objects.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        warnings: List[InsightObject] = []
        course = class_section.course

        # 1. Check Three Consecutive Scores Below 50%
        trend_res = TrendAnalyticsService.calculate_course_trajectory(student, class_section, dataset=dataset)
        if trend_res.data_quality != DataQuality.INSUFFICIENT_DATA and len(trend_res.scores_sequence) >= 3:
            last_3 = trend_res.scores_sequence[-3:]
            if all(s < 50.0 for s in last_3):
                warnings.append(InsightObject(
                    insight_type="FAILING_STREAK",
                    severity=Severity.DANGER,
                    title=f"Three Consecutive Failing Evaluations ({course.code})",
                    summary=f"Student has scored below 50% on the last 3 consecutive assessments: {last_3[0]}%, {last_3[1]}%, {last_3[2]}%.",
                    evidence={'last_3_scores': last_3, 'threshold': 50.0},
                    metrics={'last_score': last_3[-1]},
                    student_id=student.pk,
                    course_id=course.pk,
                    section_id=class_section.pk,
                    data_quality=DataQuality.VALID,
                    confidence=ConfidenceLevel.HIGH
                ))

        # 2. Check Acute Score Anomaly
        anomaly = AnomalyDetectionService.detect_course_anomaly(student, class_section, dataset=dataset)
        if anomaly.is_anomaly and anomaly.anomaly_type == "ACUTE_DROP":
            warnings.append(InsightObject(
                insight_type="ANOMALY_DETECTED",
                severity=Severity.CRITICAL,
                title=f"Acute Performance Drop ({course.code})",
                summary=anomaly.summary,
                evidence=anomaly.evidence,
                metrics={'z_score': anomaly.z_score or 0.0, 'drop_points': anomaly.delta or 0.0},
                student_id=student.pk,
                course_id=course.pk,
                section_id=class_section.pk,
                data_quality=DataQuality.VALID,
                confidence=ConfidenceLevel.HIGH
            ))

        # 3. Check Critical Attendance Deficit
        att_res = AttendanceAnalyticsService.calculate_course_attendance(student, class_section, dataset=dataset)
        if att_res.data_quality != DataQuality.INSUFFICIENT_DATA:
            if att_res.attendance_percentage < 60.0:
                warnings.append(InsightObject(
                    insight_type="ATTENDANCE_DEFICIT",
                    severity=Severity.CRITICAL if att_res.attendance_percentage < 50.0 else Severity.DANGER,
                    title=f"Severe Attendance Shortfall ({course.code})",
                    summary=f"Attendance is {att_res.attendance_percentage}% ({att_res.absent_count} absences). Buffer is {att_res.absence_buffer} sessions.",
                    evidence={
                        'attendance_percentage': att_res.attendance_percentage,
                        'absent_count': att_res.absent_count,
                        'absence_buffer': att_res.absence_buffer,
                        'required_sessions': att_res.required_sessions,
                        'is_recovery_possible': att_res.is_recovery_possible
                    },
                    metrics={'attendance_pct': att_res.attendance_percentage},
                    student_id=student.pk,
                    course_id=course.pk,
                    section_id=class_section.pk,
                    data_quality=DataQuality.VALID,
                    confidence=ConfidenceLevel.HIGH
                ))

        # 4. Check High Missing Assignment Rate
        assign_res = AssignmentAnalyticsService.calculate_course_assignments(student, class_section, dataset=dataset)
        if assign_res.data_quality != DataQuality.INSUFFICIENT_DATA and assign_res.missing_rate >= 50.0:
            warnings.append(InsightObject(
                insight_type="MISSING_COURSEWORK",
                severity=Severity.WARNING if assign_res.missing_rate < 75.0 else Severity.DANGER,
                title=f"Elevated Missing Assignments ({course.code})",
                summary=f"Student has missed {assign_res.missing_count} of {assign_res.total_assigned} assignments ({assign_res.missing_rate}% missing rate).",
                evidence={'missing_count': assign_res.missing_count, 'total_assigned': assign_res.total_assigned, 'missing_rate': assign_res.missing_rate},
                metrics={'missing_rate': assign_res.missing_rate},
                student_id=student.pk,
                course_id=course.pk,
                section_id=class_section.pk,
                data_quality=DataQuality.VALID,
                confidence=ConfidenceLevel.HIGH
            ))

        # 5. Check Discordance Flag
        if assign_res.discordance_flag:
            warnings.append(InsightObject(
                insight_type="EFFORT_DISCORDANCE",
                severity=Severity.WARNING,
                title=f"Coursework Discordance Detected ({course.code})",
                summary=f"{assign_res.discordance_flag} in {course.code}.",
                evidence={'completion_rate': assign_res.completion_rate, 'average_score': assign_res.average_score},
                metrics={'completion_rate': assign_res.completion_rate},
                student_id=student.pk,
                course_id=course.pk,
                section_id=class_section.pk,
                data_quality=DataQuality.VALID,
                confidence=ConfidenceLevel.HIGH
            ))

        return warnings
