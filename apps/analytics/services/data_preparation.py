"""
Data preparation and prefetching layer for academic analytics.
Aggregates raw academic records into memory-efficient, optimized structures to prevent N+1 queries.
"""

from typing import Dict, Any, List, Optional
from django.db.models import Prefetch
from apps.academic.models import (
    StudentProfile,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    Semester,
    Course,
    Topic
)


class AnalyticsDataPreparationService:
    """
    Retrieves and prepares structured academic datasets for downstream deterministic engines.
    """

    @staticmethod
    def get_student_course_dataset(student: StudentProfile, class_section: ClassSection) -> Dict[str, Any]:
        """
        Prepares all granular records for a student within a specific class section.
        """
        # 1. Enrollment record
        enrollment = Enrollment.objects.filter(student=student, class_section=class_section).first()

        # 2. Attendance records for this student in this section
        attendance_records = list(
            AttendanceRecord.objects.filter(
                student=student,
                session__class_section=class_section
            ).select_related('session', 'session__topic').order_by('session__session_date', 'session__created_at')
        )

        # 3. Total conducted sessions in this section
        total_conducted_sessions = ClassSession.objects.filter(class_section=class_section, is_completed=True).count()

        # 4. Assignment submissions for this student in this section
        assignments = list(
            Assignment.objects.filter(
                class_section=class_section,
                is_published=True
            ).select_related('topic').order_by('due_date')
        )
        submissions = {
            sub.assignment_id: sub for sub in AssignmentSubmission.objects.filter(
                student=student,
                assignment__class_section=class_section
            ).select_related('assignment')
        }

        # 5. Assessment results for this student in this section
        assessments = list(
            Assessment.objects.filter(
                class_section=class_section,
                is_published=True
            ).select_related('topic').order_by('date')
        )
        results = {
            res.assessment_id: res for res in AssessmentResult.objects.filter(
                student=student,
                assessment__class_section=class_section
            ).select_related('assessment')
        }

        # 6. Historical completed enrollments (past semesters)
        past_enrollments = list(
            Enrollment.objects.filter(
                student=student,
                class_section__semester__is_completed=True,
                status=Enrollment.EnrollmentStatus.COMPLETED
            ).select_related('class_section__course', 'class_section__semester')
        )

        return {
            'student': student,
            'class_section': class_section,
            'enrollment': enrollment,
            'attendance_records': attendance_records,
            'total_conducted_sessions': total_conducted_sessions,
            'assignments': assignments,
            'submissions': submissions,
            'assessments': assessments,
            'results': results,
            'past_enrollments': past_enrollments
        }

    @staticmethod
    def get_student_overall_dataset(student: StudentProfile, semester: Optional[Semester] = None) -> Dict[str, Any]:
        """
        Prepares all active course enrollments and records for a student in a semester.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        active_enrollments = list(
            Enrollment.objects.filter(
                student=student,
                class_section__semester=semester
            ).select_related(
                'class_section__course__department',
                'class_section__semester',
                'class_section__primary_teacher__user'
            )
        )

        past_enrollments = list(
            Enrollment.objects.filter(
                student=student,
                class_section__semester__is_completed=True,
                status=Enrollment.EnrollmentStatus.COMPLETED
            ).select_related('class_section__course', 'class_section__semester')
        )

        course_datasets = []
        for enr in active_enrollments:
            ds = AnalyticsDataPreparationService.get_student_course_dataset(student, enr.class_section)
            course_datasets.append(ds)

        return {
            'student': student,
            'semester': semester,
            'active_enrollments': active_enrollments,
            'past_enrollments': past_enrollments,
            'course_datasets': course_datasets
        }

    @staticmethod
    def get_section_full_dataset(class_section: ClassSection) -> Dict[str, Any]:
        """
        Prepares bulk records for an entire class section (all enrolled students, scores, attendance).
        """
        enrollments = list(
            Enrollment.objects.filter(
                class_section=class_section
            ).select_related('student__user', 'student__program', 'student__department').order_by('student__student_id')
        )

        students = [enr.student for enr in enrollments]

        assessments = list(
            Assessment.objects.filter(
                class_section=class_section,
                is_published=True
            ).select_related('topic').order_by('date')
        )

        results = list(
            AssessmentResult.objects.filter(
                assessment__class_section=class_section
            ).select_related('assessment', 'student')
        )

        assignments = list(
            Assignment.objects.filter(
                class_section=class_section,
                is_published=True
            ).select_related('topic').order_by('due_date')
        )

        submissions = list(
            AssignmentSubmission.objects.filter(
                assignment__class_section=class_section
            ).select_related('assignment', 'student')
        )

        sessions = list(
            ClassSession.objects.filter(
                class_section=class_section,
                is_completed=True
            ).order_by('session_date')
        )

        attendance_records = list(
            AttendanceRecord.objects.filter(
                session__class_section=class_section
            ).select_related('session', 'student')
        )

        return {
            'class_section': class_section,
            'enrollments': enrollments,
            'students': students,
            'assessments': assessments,
            'results': results,
            'assignments': assignments,
            'submissions': submissions,
            'sessions': sessions,
            'attendance_records': attendance_records
        }
