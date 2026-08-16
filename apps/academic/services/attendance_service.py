"""
Session-based attendance management service.
Calculates dynamic attendance metrics and enforces integrity.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import date, time
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.academic.models import (
    ClassSection,
    ClassSession,
    AttendanceRecord,
    StudentProfile,
    TeacherProfile,
    Enrollment,
    Semester,
    Topic
)
from apps.core.models import AuditLog


class AttendanceService:
    """
    Authoritative service for creating class sessions, logging attendance,
    and dynamically calculating student attendance percentages without hardcoding.
    """

    @classmethod
    @transaction.atomic
    def create_session_with_roster(
        cls,
        class_section: ClassSection,
        teacher: TeacherProfile,
        session_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        title: str = "Lecture Session",
        topic: Optional[Topic] = None,
        default_status: str = AttendanceRecord.AttendanceStatus.PRESENT,
        actor=None
    ) -> ClassSession:
        """
        Create a lecture session and initialize attendance records for all active enrolled students.
        """
        session = ClassSession.objects.create(
            class_section=class_section,
            teacher=teacher,
            session_date=session_date,
            start_time=start_time,
            end_time=end_time,
            title=title,
            topic=topic,
            is_completed=True
        )

        active_enrollments = Enrollment.objects.filter(
            class_section=class_section,
            status=Enrollment.EnrollmentStatus.ENROLLED
        ).select_related('student')

        records = [
            AttendanceRecord(
                session=session,
                student=enrollment.student,
                status=default_status
            )
            for enrollment in active_enrollments
        ]

        if records:
            AttendanceRecord.objects.bulk_create(records)

        if actor:
            AuditLog.log_action(
                user=actor,
                action='CREATE_CLASS_SESSION',
                details={
                    'session_id': session.pk,
                    'section_id': class_section.pk,
                    'session_date': str(session_date),
                    'student_count': len(records)
                }
            )

        return session

    @classmethod
    @transaction.atomic
    def mark_attendance(
        cls,
        session: ClassSession,
        attendance_dict: Dict[int, str],
        remarks_dict: Optional[Dict[int, str]] = None,
        actor=None
    ) -> int:
        """
        Update attendance status for students in a session.
        attendance_dict maps student_id (int PK of StudentProfile) -> status ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED').
        """
        remarks_dict = remarks_dict or {}
        updated_count = 0

        valid_statuses = set(AttendanceRecord.AttendanceStatus.values)

        for student_id, status in attendance_dict.items():
            if status not in valid_statuses:
                raise ValidationError(_(f"Invalid attendance status: '{status}'."))

            record = AttendanceRecord.objects.filter(
                session=session,
                student_id=student_id
            ).first()

            if record:
                record.status = status
                if student_id in remarks_dict:
                    record.remarks = remarks_dict[student_id].strip()
                record.save()
                updated_count += 1
            else:
                # Student enrolled after session was initialized
                student = StudentProfile.objects.filter(pk=student_id).first()
                if student:
                    AttendanceRecord.objects.create(
                        session=session,
                        student=student,
                        status=status,
                        remarks=remarks_dict.get(student_id, '').strip()
                    )
                    updated_count += 1

        if actor:
            AuditLog.log_action(
                user=actor,
                action='MARK_ATTENDANCE',
                details={
                    'session_id': session.pk,
                    'updated_records': updated_count
                }
            )

        return updated_count

    @classmethod
    def calculate_student_attendance(
        cls,
        student: StudentProfile,
        class_section: Optional[ClassSection] = None,
        semester: Optional[Semester] = None
    ) -> Dict[str, Any]:
        """
        Dynamically calculate attendance metrics for a student from underlying AttendanceRecords.
        """
        records = AttendanceRecord.objects.filter(student=student)

        if class_section:
            records = records.filter(session__class_section=class_section)
        elif semester:
            records = records.filter(session__class_section__semester=semester)

        total_sessions = records.count()
        present_count = records.filter(status=AttendanceRecord.AttendanceStatus.PRESENT).count()
        late_count = records.filter(status=AttendanceRecord.AttendanceStatus.LATE).count()
        excused_count = records.filter(status=AttendanceRecord.AttendanceStatus.EXCUSED).count()
        absent_count = records.filter(status=AttendanceRecord.AttendanceStatus.ABSENT).count()

        # Calculation policy: Present counts 100%, Late counts 100% attendance (or half depending on rules; standard is attended), Excused is counted toward attended
        attended_sessions = present_count + late_count + excused_count

        if total_sessions > 0:
            percentage = round((attended_sessions / total_sessions) * 100.0, 2)
        else:
            percentage = 100.0

        if percentage >= 85.0:
            status_label = 'EXCELLENT'
            badge_class = 'badge-success'
        elif percentage >= 75.0:
            status_label = 'GOOD'
            badge_class = 'badge-info'
        elif percentage >= 65.0:
            status_label = 'WARNING'
            badge_class = 'badge-warning'
        else:
            status_label = 'CRITICAL'
            badge_class = 'badge-danger'

        return {
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'present_count': present_count,
            'late_count': late_count,
            'excused_count': excused_count,
            'absent_count': absent_count,
            'attendance_percentage': percentage,
            'status': status_label,
            'badge_class': badge_class,
            'is_below_minimum': percentage < 75.0
        }

    @classmethod
    def get_student_course_attendance_matrix(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None
    ) -> List[Dict[str, Any]]:
        """
        Return attendance breakdown across all enrolled courses for a student.
        """
        enrollments = Enrollment.objects.filter(
            student=student,
            status__in=[Enrollment.EnrollmentStatus.ENROLLED, Enrollment.EnrollmentStatus.COMPLETED]
        ).select_related('class_section__course', 'class_section__semester')

        if semester:
            enrollments = enrollments.filter(class_section__semester=semester)

        results = []
        for enrollment in enrollments:
            metrics = cls.calculate_student_attendance(student, class_section=enrollment.class_section)
            results.append({
                'enrollment': enrollment,
                'class_section': enrollment.class_section,
                'course': enrollment.class_section.course,
                'semester': enrollment.class_section.semester,
                'metrics': metrics
            })

        return results
