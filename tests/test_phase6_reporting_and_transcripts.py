"""
Phase 6 Automated Tests: Academic Transcripts, Reporting & CSV Exports.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
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
from apps.portal.reporting import TranscriptService, ReportingService


class Phase6ReportingTests(TestCase):
    def setUp(self):
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

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            role=Role.ADMINISTRATOR,
            first_name="Admin",
            last_name="User"
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

        # Enrolled with 92% (A grade)
        self.enr = Enrollment.objects.create(
            student=self.student,
            class_section=self.section,
            status=Enrollment.EnrollmentStatus.ENROLLED,
            final_percentage=Decimal('92.00'),
            final_grade_letter='A',
            is_grade_published=True
        )

    def test_student_transcript_calculations(self):
        """Verify Term GPA, Cumulative GPA, and standing calculations."""
        transcript = TranscriptService.get_student_transcript(self.student)

        self.assertEqual(transcript['student_id'], "STU-001")
        self.assertEqual(transcript['cumulative_gpa'], 4.0)
        self.assertEqual(transcript['total_credits_earned'], 4.0)
        self.assertEqual(transcript['academic_standing'], "Dean's List / Distinction")
        self.assertEqual(len(transcript['semesters']), 1)
        self.assertEqual(transcript['semesters'][0]['term_gpa'], 4.0)

    def test_student_transcript_csv_export(self):
        """Verify student CSV export contains authoritative headers and data."""
        response = ReportingService.export_student_transcript_csv(self.student)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn("OFFICIAL ACADEMIC TRANSCRIPT", content)
        self.assertIn("Ada Lovelace", content)
        self.assertIn("CS101", content)

    def test_teacher_section_csv_export(self):
        """Verify teacher section CSV export."""
        response = ReportingService.export_teacher_section_csv(self.teacher, self.section.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn("CLASS SECTION PERFORMANCE", content)
        self.assertIn("Alan Turing", content)

    def test_admin_institutional_csv_export(self):
        """Verify administrator macro institutional CSV export."""
        response = ReportingService.export_admin_institutional_csv(self.admin_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn("UNIVERSITY-WIDE ACADEMIC INTELLIGENCE STATEMENT", content)
        self.assertIn("Computer Science", content)
