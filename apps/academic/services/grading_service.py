"""
Authoritative Grading and Assessment Evaluation Service.
Eliminates double-counting and maintains read-only published grade snapshots.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.academic.models import (
    ClassSection,
    Assessment,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    StudentProfile,
    TeacherProfile,
    Enrollment,
    Semester
)
from apps.core.models import AuditLog


class GradingService:
    """
    Sole authoritative source for score aggregation, weighted course grades,
    letter grade mapping, and published enrollment snapshots.
    """

    GRADE_SCALE = [
        (Decimal('90.00'), 'A+', Decimal('4.00')),
        (Decimal('80.00'), 'A', Decimal('3.75')),
        (Decimal('75.00'), 'B+', Decimal('3.50')),
        (Decimal('70.00'), 'B', Decimal('3.00')),
        (Decimal('60.00'), 'C', Decimal('2.00')),
        (Decimal('50.00'), 'D', Decimal('1.00')),
        (Decimal('0.00'), 'F', Decimal('0.00')),
    ]

    @classmethod
    def get_letter_grade(cls, percentage: Decimal) -> tuple[str, Decimal]:
        """Map percentage score to (letter_grade, grade_points)."""
        for threshold, letter, points in cls.GRADE_SCALE:
            if percentage >= threshold:
                return letter, points
        return 'F', Decimal('0.00')

    @classmethod
    @transaction.atomic
    def record_assessment_marks(
        cls,
        assessment: Assessment,
        teacher: TeacherProfile,
        marks_dict: Dict[int, Decimal],
        remarks_dict: Optional[Dict[int, str]] = None,
        actor=None
    ) -> int:
        """
        Record or update examination marks for a class section.
        marks_dict maps student_id (int PK) -> marks (Decimal).
        """
        remarks_dict = remarks_dict or {}
        updated_count = 0

        for student_id, marks in marks_dict.items():
            if marks is None:
                continue

            marks_dec = Decimal(str(marks))
            if marks_dec < Decimal('0.00') or marks_dec > assessment.max_marks:
                raise ValidationError(
                    _(f"Marks ({marks_dec}) for student ID {student_id} must be between 0.00 and max marks ({assessment.max_marks}).")
                )

            result, created = AssessmentResult.objects.update_or_create(
                assessment=assessment,
                student_id=student_id,
                defaults={
                    'marks_obtained': marks_dec,
                    'remarks': remarks_dict.get(student_id, '').strip(),
                    'graded_by': teacher
                }
            )
            updated_count += 1

        if actor:
            AuditLog.log_action(
                user=actor,
                action='RECORD_ASSESSMENT_MARKS',
                details={
                    'assessment_id': assessment.pk,
                    'section_id': assessment.class_section.pk,
                    'updated_students': updated_count
                }
            )

        return updated_count

    @classmethod
    def calculate_student_course_grade(
        cls,
        student: StudentProfile,
        class_section: ClassSection
    ) -> Dict[str, Any]:
        """
        Authoritative calculation of final course percentage and letter grade.
        Guarantees zero double counting between assignments and assessments.
        """
        assessments = Assessment.objects.filter(
            class_section=class_section,
            is_published=True
        ).select_related('topic').order_by('date')

        breakdowns = []
        weighted_sum = Decimal('0.00')
        total_evaluated_weights = Decimal('0.00')

        for assessment in assessments:
            weight = assessment.weightage_percentage

            if assessment.assessment_type == Assessment.AssessmentType.ASSIGNMENTS:
                # Aggregate student's evaluated assignment performance for this section
                submissions = AssignmentSubmission.objects.filter(
                    assignment__class_section=class_section,
                    student=student,
                    status=AssignmentSubmission.SubmissionStatus.GRADED
                )
                total_obtained = sum((s.obtained_marks for s in submissions if s.obtained_marks is not None), Decimal('0.00'))
                total_max = sum((s.assignment.max_marks for s in submissions), Decimal('0.00'))

                if total_max > Decimal('0.00'):
                    score_pct = (total_obtained / total_max) * Decimal('100.00')
                else:
                    score_pct = Decimal('0.00')

                breakdowns.append({
                    'assessment': assessment,
                    'title': assessment.title,
                    'type': assessment.get_assessment_type_display(),
                    'marks_obtained': total_obtained,
                    'max_marks': total_max,
                    'percentage': round(score_pct, 2),
                    'weightage': weight,
                    'weighted_contribution': round((score_pct * weight) / Decimal('100.00'), 2)
                })

            else:
                # Standard Exam / Quiz / Practical / Project
                result = AssessmentResult.objects.filter(
                    assessment=assessment,
                    student=student
                ).first()

                if result and result.marks_obtained is not None:
                    score_pct = result.percentage
                    marks_obtained = result.marks_obtained
                else:
                    score_pct = Decimal('0.00')
                    marks_obtained = Decimal('0.00')

                breakdowns.append({
                    'assessment': assessment,
                    'title': assessment.title,
                    'type': assessment.get_assessment_type_display(),
                    'marks_obtained': marks_obtained,
                    'max_marks': assessment.max_marks,
                    'percentage': round(score_pct, 2),
                    'weightage': weight,
                    'weighted_contribution': round((score_pct * weight) / Decimal('100.00'), 2)
                })

            weighted_sum += (score_pct * weight)
            total_evaluated_weights += weight

        if total_evaluated_weights > Decimal('0.00'):
            # Normalized to the sum of evaluated weights
            final_percentage = round((weighted_sum / total_evaluated_weights), 2)
        else:
            final_percentage = Decimal('0.00')

        letter_grade, grade_points = cls.get_letter_grade(final_percentage)

        return {
            'student': student,
            'class_section': class_section,
            'final_percentage': final_percentage,
            'final_grade_letter': letter_grade,
            'grade_points': grade_points,
            'total_evaluated_weights': total_evaluated_weights,
            'breakdowns': breakdowns
        }

    @classmethod
    def calculate_section_gradebook(cls, class_section: ClassSection) -> Dict[str, Any]:
        """
        Build the complete gradebook matrix for an entire class section.
        """
        assessments = Assessment.objects.filter(
            class_section=class_section,
            is_published=True
        ).order_by('date')

        enrollments = Enrollment.objects.filter(
            class_section=class_section,
            status__in=[Enrollment.EnrollmentStatus.ENROLLED, Enrollment.EnrollmentStatus.COMPLETED]
        ).select_related('student__user', 'student__program').order_by('student__student_id')

        student_rows = []
        for enrollment in enrollments:
            calc = cls.calculate_student_course_grade(enrollment.student, class_section)
            student_rows.append({
                'enrollment': enrollment,
                'student': enrollment.student,
                'breakdowns': calc['breakdowns'],
                'calculated_percentage': calc['final_percentage'],
                'calculated_grade_letter': calc['final_grade_letter'],
                'is_published': enrollment.is_grade_published,
                'published_percentage': enrollment.final_percentage,
                'published_grade_letter': enrollment.final_grade_letter
            })

        return {
            'class_section': class_section,
            'assessments': assessments,
            'student_rows': student_rows
        }

    @classmethod
    @transaction.atomic
    def publish_section_grades(cls, class_section: ClassSection, actor=None) -> int:
        """
        Finalize and publish calculated grades into Enrollment read-only snapshots.
        """
        enrollments = Enrollment.objects.filter(
            class_section=class_section,
            status__in=[Enrollment.EnrollmentStatus.ENROLLED, Enrollment.EnrollmentStatus.COMPLETED]
        ).select_related('student')

        now = timezone.now()
        published_count = 0

        for enrollment in enrollments:
            calc = cls.calculate_student_course_grade(enrollment.student, class_section)
            enrollment.final_percentage = calc['final_percentage']
            enrollment.final_grade_letter = calc['final_grade_letter']
            enrollment.is_grade_published = True
            enrollment.published_at = now
            enrollment.save()
            published_count += 1

        if actor:
            AuditLog.log_action(
                user=actor,
                action='PUBLISH_SECTION_GRADES',
                details={
                    'section_id': class_section.pk,
                    'course_code': class_section.course.code,
                    'students_published': published_count
                }
            )

        return published_count

    @classmethod
    @transaction.atomic
    def recalculate_and_update_enrollment_snapshot(cls, enrollment: Enrollment, actor=None) -> Enrollment:
        """
        Recalculate an individual student's grade after score corrections and update snapshot with audit log.
        """
        old_pct = enrollment.final_percentage
        old_grade = enrollment.final_grade_letter

        calc = cls.calculate_student_course_grade(enrollment.student, enrollment.class_section)
        enrollment.final_percentage = calc['final_percentage']
        enrollment.final_grade_letter = calc['final_grade_letter']
        enrollment.save()

        if actor:
            AuditLog.log_action(
                user=actor,
                action='RECALCULATE_ENROLLMENT_GRADE',
                details={
                    'enrollment_id': enrollment.pk,
                    'student_id': enrollment.student.student_id,
                    'old_percentage': float(old_pct) if old_pct else None,
                    'new_percentage': float(enrollment.final_percentage),
                    'old_grade': old_grade,
                    'new_grade': enrollment.final_grade_letter
                }
            )

        return enrollment
