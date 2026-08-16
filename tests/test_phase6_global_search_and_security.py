"""
Phase 6 Automated Tests: Global Role-Scoped Search & Security Hardening.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    ClassSection,
    Enrollment
)
from apps.portal.services.search_service import GlobalSearchService
from apps.core.validators import validate_file_upload


class Phase6SearchAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="Computer Science", code="CS")
        self.prog = Program.objects.create(name="B.Sc. CS", code="BSCS", department=self.dept)

        self.student_user = User.objects.create_user(
            email="student@example.com",
            password="Password123!",
            role=Role.STUDENT,
            first_name="Ada",
            last_name="Lovelace"
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-001",
            department=self.dept,
            program=self.prog
        )

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            role=Role.ADMINISTRATOR,
            first_name="Admin",
            last_name="User"
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            password="Password123!",
            role=Role.TEACHER,
            first_name="Alan",
            last_name="Turing"
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id="FAC-001",
            department=self.dept
        )

        self.ay = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        self.sem = Semester.objects.create(
            academic_year=self.ay,
            semester_number=1,
            name="Fall 2026",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 31),
            is_active=True
        )
        self.course = Course.objects.create(department=self.dept, code="CS101", title="Intro to CS", credits=Decimal('4.0'))
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code="A", primary_teacher=self.teacher)
        self.enr = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_global_search_student_scope(self):
        """Verify students only find courses they are enrolled in and not other students."""
        results = GlobalSearchService.search(self.student_user, "CS101")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['category'], 'Course')

        # Student searches for another student -> Must return 0
        hidden_results = GlobalSearchService.search(self.student_user, "STU-001")
        self.assertEqual(len(hidden_results), 0)

    def test_global_search_admin_scope(self):
        """Verify administrators can search across all entities."""
        results = GlobalSearchService.search(self.admin_user, "STU-001")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['category'], 'Student')

    def test_file_upload_security_validator(self):
        """Verify upload validator blocks dangerous extensions and oversized files."""
        # Allowed file
        safe_file = SimpleUploadedFile("assignment.pdf", b"sample content", content_type="application/pdf")
        validate_file_upload(safe_file) # Should not raise

        # Dangerous extension (.exe)
        dangerous_file = SimpleUploadedFile("malware.exe", b"binary content", content_type="application/x-msdownload")
        with self.assertRaises(ValidationError):
            validate_file_upload(dangerous_file)

    def test_system_health_endpoint(self):
        """Verify /health/ endpoint returns valid JSON with database and auth status."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'HEALTHY')
        self.assertEqual(data['checks']['database'], 'HEALTHY')
