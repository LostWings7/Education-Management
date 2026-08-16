"""
Unit tests for EnrollmentService: capacity enforcement, program eligibility, duplicate prevention.
"""

from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    ClassSection,
    Enrollment,
    AcademicYear,
    Semester
)
from apps.academic.services import EnrollmentService


class EnrollmentServiceTest(TestCase):
    def setUp(self):
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science')
        self.dept_ece = Department.objects.create(code='ECE', name='Electronics')

        self.prog_cse = Program.objects.create(department=self.dept_cse, code='BT-CSE', name='B.Tech CSE')
        self.prog_ece = Program.objects.create(department=self.dept_ece, code='BT-ECE', name='B.Tech ECE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Teacher
        t_user = User.objects.create_user(email='prof@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_user, employee_id='T-01', department=self.dept_cse)

        # Courses
        self.course_cse = Course.objects.create(department=self.dept_cse, code='CS201', title='Data Structures', credits=4)
        self.course_cse.programs.add(self.prog_cse)

        self.course_ece = Course.objects.create(department=self.dept_ece, code='EC201', title='Digital Signals', credits=4)
        self.course_ece.programs.add(self.prog_ece)

        # Class Section with capacity = 2
        self.sec_cse = ClassSection.objects.create(
            course=self.course_cse,
            semester=self.sem,
            section_code='A',
            primary_teacher=self.teacher,
            capacity=2
        )

        # Students
        s1_user = User.objects.create_user(email='s1@example.com', password='Password@123', role=Role.STUDENT)
        self.student_cse_1 = StudentProfile.objects.create(user=s1_user, student_id='STU-1', department=self.dept_cse, program=self.prog_cse)

        s2_user = User.objects.create_user(email='s2@example.com', password='Password@123', role=Role.STUDENT)
        self.student_cse_2 = StudentProfile.objects.create(user=s2_user, student_id='STU-2', department=self.dept_cse, program=self.prog_cse)

        s3_user = User.objects.create_user(email='s3@example.com', password='Password@123', role=Role.STUDENT)
        self.student_cse_3 = StudentProfile.objects.create(user=s3_user, student_id='STU-3', department=self.dept_cse, program=self.prog_cse)

        s_ece_user = User.objects.create_user(email='sece@example.com', password='Password@123', role=Role.STUDENT)
        self.student_ece = StudentProfile.objects.create(user=s_ece_user, student_id='STU-ECE', department=self.dept_ece, program=self.prog_ece)

    def test_successful_enrollment(self):
        """Student in valid program can enroll in available class section."""
        enr = EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        self.assertEqual(enr.status, Enrollment.EnrollmentStatus.ENROLLED)
        self.assertEqual(self.sec_cse.enrolled_count, 1)

    def test_program_eligibility_rejection(self):
        """ECE student cannot enroll in CSE course that is not part of ECE curriculum."""
        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student_ece, self.sec_cse)
        self.assertIn("not included in the curriculum", str(ctx.exception))

    def test_section_capacity_limit_enforcement(self):
        """Section with capacity 2 rejects 3rd student enrollment."""
        EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        EnrollmentService.enroll_student(self.student_cse_2, self.sec_cse)
        self.assertTrue(self.sec_cse.is_full)

        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student_cse_3, self.sec_cse)
        self.assertIn("maximum capacity", str(ctx.exception))

    def test_duplicate_active_enrollment_prevention(self):
        """Attempting to enroll the same student twice in the same section raises ValidationError."""
        EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        self.assertIn("already actively enrolled", str(ctx.exception))

    def test_drop_and_re_enrollment(self):
        """Dropping course marks status as DROPPED, and re-enrolling restores it."""
        enr = EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        dropped_enr = EnrollmentService.drop_student(self.student_cse_1, self.sec_cse)
        self.assertEqual(dropped_enr.status, Enrollment.EnrollmentStatus.DROPPED)
        self.assertEqual(self.sec_cse.enrolled_count, 0)

        # Re-enroll
        re_enr = EnrollmentService.enroll_student(self.student_cse_1, self.sec_cse)
        self.assertEqual(re_enr.status, Enrollment.EnrollmentStatus.ENROLLED)
        self.assertEqual(self.sec_cse.enrolled_count, 1)
