"""
Unit tests for Academic domain models:
Department, Program, StudentProfile, and TeacherProfile.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.core.models import User, Role
from apps.academic.models import Department, Program, StudentProfile, TeacherProfile


class AcademicModelsTests(TestCase):
    """
    Tests ensuring academic domain relationships and validations.
    """

    def setUp(self):
        self.dept_cs = Department.objects.create(
            code='CS',
            name='Department of Computer Science'
        )
        self.dept_ee = Department.objects.create(
            code='EE',
            name='Department of Electrical Engineering'
        )

        self.prog_cs = Program.objects.create(
            department=self.dept_cs,
            code='BS-CS',
            name='BS Computer Science',
            degree_level=Program.DegreeLevel.BACHELOR,
            duration_years=4,
            total_semesters=8
        )

        self.prog_ee = Program.objects.create(
            department=self.dept_ee,
            code='BS-EE',
            name='BS Electrical Engineering',
            degree_level=Program.DegreeLevel.BACHELOR,
            duration_years=4,
            total_semesters=8
        )

        self.student_user = User.objects.create_user(
            email='student.test@example.com',
            password='Password123!',
            role=Role.STUDENT
        )

        self.teacher_user = User.objects.create_user(
            email='teacher.test@example.com',
            password='Password123!',
            role=Role.TEACHER
        )

    def test_department_and_program_creation(self):
        self.assertEqual(str(self.dept_cs), 'Department of Computer Science (CS)')
        self.assertEqual(self.prog_cs.department, self.dept_cs)
        self.assertEqual(self.prog_cs.duration_years, 4)

    def test_student_profile_with_matching_department_and_program(self):
        student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id='STU-001',
            department=self.dept_cs,
            program=self.prog_cs,
            current_semester=1,
            academic_year=2026
        )
        self.assertEqual(student_profile.user, self.student_user)
        self.assertEqual(student_profile.student_id, 'STU-001')
        self.assertEqual(student_profile.program.department, self.dept_cs)

    def test_student_profile_auto_sets_department_from_program(self):
        profile = StudentProfile(
            user=self.student_user,
            student_id='STU-002',
            program=self.prog_cs,
            current_semester=1
        )
        profile.save()
        self.assertEqual(profile.department, self.dept_cs)

    def test_student_profile_department_mismatch_raises_validation_error(self):
        """
        Ensure assigning program BS-EE (from EE dept) to CS dept raises ValidationError.
        """
        profile = StudentProfile(
            user=self.student_user,
            student_id='STU-003',
            department=self.dept_cs,
            program=self.prog_ee,  # Belongs to EE dept!
            current_semester=1
        )
        with self.assertRaises(ValidationError):
            profile.save()

    def test_teacher_profile_creation(self):
        teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id='FAC-001',
            department=self.dept_cs,
            designation='Professor',
            office_location='Lab 101'
        )
        self.assertEqual(teacher_profile.user, self.teacher_user)
        self.assertEqual(teacher_profile.employee_id, 'FAC-001')
        self.assertEqual(teacher_profile.department, self.dept_cs)
