"""
Enrollment service for managing student course registrations,
capacity limits, and program eligibility checks.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.academic.models import (
    StudentProfile,
    ClassSection,
    Enrollment,
    Semester
)
from apps.core.models import AuditLog


class EnrollmentService:
    """
    Authoritative service for student course enrollments.
    """

    @classmethod
    @transaction.atomic
    def enroll_student(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        actor=None,
        enrollment_date=None,
        status=Enrollment.EnrollmentStatus.ENROLLED
    ) -> Enrollment:
        """
        Register a student in a class section with full validation.
        """
        # 1. Check student status
        if student.academic_status != StudentProfile.AcademicStatus.ACTIVE:
            raise ValidationError(
                _(f"Student '{student.student_id}' is not in ACTIVE academic standing ({student.get_academic_status_display()}).")
            )

        # 2. Check course eligibility for student's program
        if not class_section.course.is_eligible_for_program(student.program):
            raise ValidationError(
                _(f"Course '{class_section.course.code}' is not included in the curriculum for program '{student.program.name}'.")
            )

        # 3. Check section capacity
        if class_section.is_full:
            raise ValidationError(
                _(f"Class section '{class_section}' has reached its maximum capacity of {class_section.capacity} students.")
            )

        # 4. Check for duplicate active enrollment
        existing = Enrollment.objects.filter(student=student, class_section=class_section).first()
        if existing:
            if existing.status == Enrollment.EnrollmentStatus.ENROLLED:
                raise ValidationError(_(f"Student '{student.student_id}' is already actively enrolled in '{class_section}'."))
            else:
                # Re-activate previously dropped enrollment
                existing.status = Enrollment.EnrollmentStatus.ENROLLED
                existing.enrollment_date = enrollment_date or timezone.now().date()
                existing.save()
                enrollment = existing
        else:
            enrollment = Enrollment.objects.create(
                student=student,
                class_section=class_section,
                enrollment_date=enrollment_date or timezone.now().date(),
                status=status
            )

        if actor:
            AuditLog.log_action(
                user=actor,
                action='STUDENT_ENROLLMENT',
                details={
                    'student_id': student.student_id,
                    'section_id': class_section.pk,
                    'course_code': class_section.course.code
                }
            )

        return enrollment

    @classmethod
    @transaction.atomic
    def drop_student(cls, student: StudentProfile, class_section: ClassSection, actor=None) -> Enrollment:
        """
        Drop student from a class section.
        """
        enrollment = Enrollment.objects.filter(student=student, class_section=class_section).first()
        if not enrollment:
            raise ValidationError(_(f"No enrollment record found for student '{student.student_id}' in '{class_section}'."))

        enrollment.status = Enrollment.EnrollmentStatus.DROPPED
        enrollment.save()

        if actor:
            AuditLog.log_action(
                user=actor,
                action='STUDENT_COURSE_DROP',
                details={
                    'student_id': student.student_id,
                    'section_id': class_section.pk,
                    'course_code': class_section.course.code
                }
            )

        return enrollment

    @classmethod
    def get_student_enrollments(cls, student: StudentProfile, semester: Semester = None, include_completed: bool = True):
        """
        Query student enrollments, optionally filtered by semester or completed status.
        """
        qs = Enrollment.objects.filter(student=student).select_related(
            'class_section__course__department',
            'class_section__semester__academic_year',
            'class_section__primary_teacher__user'
        )

        if semester:
            qs = qs.filter(class_section__semester=semester)
        elif not include_completed:
            qs = qs.filter(class_section__semester__is_active=True)

        return qs.order_by('-class_section__semester__start_date', 'class_section__course__code')

    @classmethod
    def get_section_roster(cls, class_section: ClassSection, active_only: bool = True):
        """
        Return the list of students enrolled in a class section.
        """
        qs = Enrollment.objects.filter(class_section=class_section).select_related(
            'student__user',
            'student__program',
            'student__department'
        )
        if active_only:
            qs = qs.filter(status=Enrollment.EnrollmentStatus.ENROLLED)
        return qs.order_by('student__student_id')
