"""
Unit tests for Assignment creation, student submissions, and teacher grading.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    ClassSection,
    Enrollment,
    Assignment,
    AssignmentSubmission,
    AcademicYear,
    Semester
)
from apps.academic.services import AssignmentService, EnrollmentService


class AssignmentWorkflowTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_user = User.objects.create_user(email='prof@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_user, employee_id='T-01', department=self.dept)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

        s_user = User.objects.create_user(email='s1@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_user, student_id='S-01', department=self.dept, program=self.prog)
        EnrollmentService.enroll_student(self.student, self.section)

    def test_create_assignment_validation(self):
        """Assignment must enforce valid positive max_marks and issue_date < due_date."""
        with self.assertRaises(ValidationError):
            AssignmentService.create_assignment(
                class_section=self.section,
                teacher=self.teacher,
                title='Invalid Assignment',
                description='desc',
                max_marks=Decimal('0.00'),  # Invalid <= 0
                due_date=timezone.now() + timedelta(days=5)
            )

        with self.assertRaises(ValidationError):
            AssignmentService.create_assignment(
                class_section=self.section,
                teacher=self.teacher,
                title='Invalid Due Date',
                description='desc',
                max_marks=Decimal('50.00'),
                issue_date=timezone.now() + timedelta(days=5),
                due_date=timezone.now() + timedelta(days=2)  # Invalid due before issue
            )

    def test_submission_and_grading_workflow(self):
        """Student submits assignment, and teacher evaluates score within bounds."""
        assignment = AssignmentService.create_assignment(
            class_section=self.section,
            teacher=self.teacher,
            title='Problem Set 1',
            description='BST Implementation',
            max_marks=Decimal('50.00'),
            due_date=timezone.now() + timedelta(days=5)
        )

        # Submit
        sub = AssignmentService.submit_assignment(
            assignment=assignment,
            student=self.student,
            submission_text='https://github.com/student/bst-impl'
        )
        self.assertEqual(sub.status, AssignmentSubmission.SubmissionStatus.SUBMITTED)

        # Grade
        graded_sub = AssignmentService.grade_submission(
            submission=sub,
            teacher=self.teacher,
            marks=Decimal('48.50'),
            feedback='Excellent memory management.'
        )
        self.assertEqual(graded_sub.status, AssignmentSubmission.SubmissionStatus.GRADED)
        self.assertEqual(graded_sub.obtained_marks, Decimal('48.50'))

        # Grading with excessive marks raises ValidationError
        with self.assertRaises(ValidationError):
            AssignmentService.grade_submission(
                submission=sub,
                teacher=self.teacher,
                marks=Decimal('55.00')  # Exceeds max 50.00
            )
