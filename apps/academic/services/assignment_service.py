"""
Assignment and submission management service.
Handles deadline enforcement, submission grading, and topic tracking.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.academic.models import (
    Assignment,
    AssignmentSubmission,
    ClassSection,
    StudentProfile,
    TeacherProfile,
    Enrollment,
    Topic,
    Semester
)
from apps.core.models import AuditLog


class AssignmentService:
    """
    Service for creating coursework assignments, tracking submissions,
    enforcing deadlines, and grading.
    """

    @classmethod
    @transaction.atomic
    def create_assignment(
        cls,
        class_section: ClassSection,
        teacher: TeacherProfile,
        title: str,
        description: str,
        max_marks: Decimal,
        due_date: datetime,
        issue_date: Optional[datetime] = None,
        topic: Optional[Topic] = None,
        attachment=None,
        allow_late: bool = True,
        is_published: bool = True,
        actor=None
    ) -> Assignment:
        """
        Create a new assignment for a class section.
        """
        issue_date = issue_date or timezone.now()
        if issue_date >= due_date:
            raise ValidationError({'due_date': _('Deadline must be strictly after the issue date.')})

        if max_marks <= 0:
            raise ValidationError({'max_marks': _('Maximum marks must be greater than 0.')})

        assignment = Assignment.objects.create(
            class_section=class_section,
            teacher=teacher,
            title=title.strip(),
            description=description.strip(),
            max_marks=max_marks,
            issue_date=issue_date,
            due_date=due_date,
            topic=topic,
            attachment=attachment,
            allow_late_submission=allow_late,
            is_published=is_published
        )

        if actor:
            AuditLog.log_action(
                user=actor,
                action='CREATE_ASSIGNMENT',
                details={
                    'assignment_id': assignment.pk,
                    'section_id': class_section.pk,
                    'title': title
                }
            )

        return assignment

    @classmethod
    @transaction.atomic
    def submit_assignment(
        cls,
        assignment: Assignment,
        student: StudentProfile,
        submission_text: str = '',
        attachment=None,
        actor=None
    ) -> AssignmentSubmission:
        """
        Submit or update an assignment solution.
        Automatically sets status to SUBMITTED or LATE based on current time.
        """
        # Verify enrollment
        is_enrolled = Enrollment.objects.filter(
            student=student,
            class_section=assignment.class_section,
            status=Enrollment.EnrollmentStatus.ENROLLED
        ).exists()

        if not is_enrolled:
            raise ValidationError(_(f"Student '{student.student_id}' is not enrolled in '{assignment.class_section}'."))

        now = timezone.now()
        if now > assignment.due_date:
            if not assignment.allow_late_submission:
                raise ValidationError(_('Submissions for this assignment are closed.'))
            status = AssignmentSubmission.SubmissionStatus.LATE
        else:
            status = AssignmentSubmission.SubmissionStatus.SUBMITTED

        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={
                'submission_text': submission_text.strip(),
                'attachment': attachment,
                'submission_date': now,
                'status': status
            }
        )

        if not created:
            submission.submission_text = submission_text.strip()
            if attachment:
                submission.attachment = attachment
            submission.submission_date = now
            submission.status = AssignmentSubmission.SubmissionStatus.RESUBMITTED if now <= assignment.due_date else AssignmentSubmission.SubmissionStatus.LATE
            submission.save()

        if actor:
            AuditLog.log_action(
                user=actor,
                action='SUBMIT_ASSIGNMENT',
                details={
                    'assignment_id': assignment.pk,
                    'student_id': student.student_id,
                    'status': submission.status
                }
            )

        return submission

    @classmethod
    @transaction.atomic
    def grade_submission(
        cls,
        submission: AssignmentSubmission,
        teacher: TeacherProfile,
        marks: Decimal,
        feedback: str = '',
        actor=None
    ) -> AssignmentSubmission:
        """
        Grade a student submission with score bounds validation.
        """
        if marks < Decimal('0.00') or marks > submission.assignment.max_marks:
            raise ValidationError(
                _(f"Marks ({marks}) must be between 0.00 and maximum marks ({submission.assignment.max_marks}).")
            )

        submission.obtained_marks = marks
        submission.feedback = feedback.strip()
        submission.status = AssignmentSubmission.SubmissionStatus.GRADED
        submission.graded_by = teacher
        submission.graded_at = timezone.now()
        submission.save()

        if actor:
            AuditLog.log_action(
                user=actor,
                action='GRADE_ASSIGNMENT_SUBMISSION',
                details={
                    'submission_id': submission.pk,
                    'student_id': submission.student.student_id,
                    'marks': float(marks),
                    'max_marks': float(submission.assignment.max_marks)
                }
            )

        return submission

    @classmethod
    def get_student_assignments_overview(cls, student: StudentProfile, semester: Optional[Semester] = None):
        """
        Return all assignments for student's enrolled courses, with current submission details.
        """
        enrollments = Enrollment.objects.filter(
            student=student,
            status=Enrollment.EnrollmentStatus.ENROLLED
        )
        if semester:
            enrollments = enrollments.filter(class_section__semester=semester)

        section_ids = enrollments.values_list('class_section_id', flat=True)

        assignments = Assignment.objects.filter(
            class_section_id__in=section_ids,
            is_published=True
        ).select_related(
            'class_section__course',
            'topic',
            'teacher__user'
        ).order_by('due_date')

        # Map submissions
        submissions = {
            s.assignment_id: s
            for s in AssignmentSubmission.objects.filter(student=student, assignment__in=assignments)
        }

        results = []
        for assignment in assignments:
            submission = submissions.get(assignment.pk)
            results.append({
                'assignment': assignment,
                'submission': submission,
                'is_overdue': timezone.now() > assignment.due_date and not submission,
                'status': submission.get_status_display() if submission else ('Overdue / Missing' if timezone.now() > assignment.due_date else 'Pending')
            })

        return results
