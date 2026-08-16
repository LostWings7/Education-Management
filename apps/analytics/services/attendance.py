"""
Deterministic Attendance Intelligence Service.
Calculates session-based percentages (0.0 - 100.0), consecutive absences,
absence buffer b = floor(P + R - T(N+R)/100), and required sessions to reach threshold T.
"""

import math
from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, AttendanceRecord, Semester
from apps.analytics.schemas.insight import AttendanceAnalyticsResult, DataQuality
from .data_preparation import AnalyticsDataPreparationService


class AttendanceAnalyticsService:
    """
    Computes deterministic attendance analytics, projection buffers, and required sessions.
    """

    DEFAULT_THRESHOLD = 75.0  # 75.0%

    @classmethod
    def calculate_course_attendance(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        target_threshold: float = DEFAULT_THRESHOLD,
        estimated_total_term_sessions: int = 25,
        dataset: Optional[Dict[str, Any]] = None
    ) -> AttendanceAnalyticsResult:
        """
        Calculates attendance statistics and absence buffer for a student in a class section.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        records: List[AttendanceRecord] = dataset['attendance_records']
        total_conducted = len(records)

        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0

        for r in records:
            if r.status == AttendanceRecord.AttendanceStatus.PRESENT:
                present_count += 1
            elif r.status == AttendanceRecord.AttendanceStatus.ABSENT:
                absent_count += 1
            elif r.status == AttendanceRecord.AttendanceStatus.LATE:
                late_count += 1
            elif r.status == AttendanceRecord.AttendanceStatus.EXCUSED:
                excused_count += 1

        # Attendance credits P = Present + 0.5 * Late
        p_credits = float(present_count) + (0.5 * float(late_count))

        if total_conducted == 0:
            return AttendanceAnalyticsResult(
                attendance_percentage=100.0,
                total_conducted=0,
                present_count=0,
                absent_count=0,
                late_count=0,
                excused_count=0,
                remaining_sessions=estimated_total_term_sessions,
                target_threshold=target_threshold,
                absence_buffer=estimated_total_term_sessions,
                required_sessions=0,
                is_below_threshold=False,
                is_recovery_possible=True,
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        attendance_pct = (p_credits / float(total_conducted)) * 100.0

        # Estimated remaining sessions R
        remaining_sessions = max(0, estimated_total_term_sessions - total_conducted)

        # Exact absence buffer formula: b = floor(P + R - T(N + R)/100)
        t_fraction = target_threshold / 100.0
        n_plus_r = float(total_conducted + remaining_sessions)
        raw_b = math.floor(p_credits + float(remaining_sessions) - (t_fraction * n_plus_r))
        clamped_buffer = max(0, min(remaining_sessions, raw_b))

        # Required sessions to reach target T: x = ceil((T*N - 100*P) / (100 - T))
        if target_threshold < 100.0:
            numerator = (target_threshold * float(total_conducted)) - (100.0 * p_credits)
            denominator = 100.0 - target_threshold
            raw_x = math.ceil(numerator / denominator)
            required_sessions = max(0, raw_x)
        else:
            required_sessions = total_conducted - int(p_credits)

        is_below = attendance_pct < target_threshold
        is_recovery_possible = (required_sessions <= remaining_sessions)

        return AttendanceAnalyticsResult(
            attendance_percentage=round(attendance_pct, 2),
            total_conducted=total_conducted,
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            excused_count=excused_count,
            remaining_sessions=remaining_sessions,
            target_threshold=target_threshold,
            absence_buffer=clamped_buffer,
            required_sessions=required_sessions,
            is_below_threshold=is_below,
            is_recovery_possible=is_recovery_possible,
            data_quality=DataQuality.VALID
        )

    @classmethod
    def calculate_overall_attendance(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None,
        target_threshold: float = DEFAULT_THRESHOLD
    ) -> AttendanceAnalyticsResult:
        """
        Calculates cumulative attendance statistics across all active courses in a semester.
        """
        dataset = AnalyticsDataPreparationService.get_student_overall_dataset(student, semester)
        course_datasets = dataset['course_datasets']

        total_conducted = 0
        total_present = 0
        total_absent = 0
        total_late = 0
        total_excused = 0
        total_remaining = 0

        for cds in course_datasets:
            res = cls.calculate_course_attendance(student, cds['class_section'], target_threshold=target_threshold, dataset=cds)
            total_conducted += res.total_conducted
            total_present += res.present_count
            total_absent += res.absent_count
            total_late += res.late_count
            total_excused += res.excused_count
            total_remaining += res.remaining_sessions

        p_credits = float(total_present) + (0.5 * float(total_late))

        if total_conducted == 0:
            return AttendanceAnalyticsResult(
                attendance_percentage=100.0,
                total_conducted=0,
                present_count=0,
                absent_count=0,
                late_count=0,
                excused_count=0,
                remaining_sessions=total_remaining,
                target_threshold=target_threshold,
                absence_buffer=total_remaining,
                required_sessions=0,
                is_below_threshold=False,
                is_recovery_possible=True,
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        overall_pct = (p_credits / float(total_conducted)) * 100.0

        t_fraction = target_threshold / 100.0
        n_plus_r = float(total_conducted + total_remaining)
        raw_b = math.floor(p_credits + float(total_remaining) - (t_fraction * n_plus_r))
        clamped_buffer = max(0, min(total_remaining, raw_b))

        if target_threshold < 100.0:
            numerator = (target_threshold * float(total_conducted)) - (100.0 * p_credits)
            denominator = 100.0 - target_threshold
            raw_x = math.ceil(numerator / denominator)
            required_sessions = max(0, raw_x)
        else:
            required_sessions = total_conducted - int(p_credits)

        return AttendanceAnalyticsResult(
            attendance_percentage=round(overall_pct, 2),
            total_conducted=total_conducted,
            present_count=total_present,
            absent_count=total_absent,
            late_count=total_late,
            excused_count=total_excused,
            remaining_sessions=total_remaining,
            target_threshold=target_threshold,
            absence_buffer=clamped_buffer,
            required_sessions=required_sessions,
            is_below_threshold=overall_pct < target_threshold,
            is_recovery_possible=(required_sessions <= total_remaining),
            data_quality=DataQuality.VALID
        )
