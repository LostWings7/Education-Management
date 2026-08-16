"""
Comprehensive UI/UX smoke and feature discoverability test suite.
Validates that all major pages, navigation links, and role-scoped command centers render
with complete semantic metadata and zero visual or routing breakages.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User, Role
from apps.academic.models import Department, Program, AcademicYear, Semester, StudentProfile, TeacherProfile

class UISmokeAndDiscoverabilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "TestPass@123"

        # Create Core Academic Structure
        self.year = AcademicYear.objects.create(name="2025-2026", start_date="2025-08-01", end_date="2026-06-30")
        self.semester = Semester.objects.create(
            academic_year=self.year,
            name="Spring 2026",
            start_date="2026-01-10",
            end_date="2026-05-20",
            is_active=True
        )
        self.dept = Department.objects.create(code="CSE", name="Computer Science and Engineering")
        self.program = Program.objects.create(department=self.dept, code="BT-CSE", name="B.Tech Computer Science")

        # Create Users
        self.student_user = User.objects.create_user(
            email="ada.lovelace@test.com",
            password=self.password,
            first_name="Ada",
            last_name="Lovelace",
            role=Role.STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-001",
            department=self.dept,
            program=self.program
        )

        self.teacher_user = User.objects.create_user(
            email="alan.turing@test.com",
            password=self.password,
            first_name="Alan",
            last_name="Turing",
            role=Role.TEACHER
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id="FAC-001",
            department=self.dept,
            designation="Professor"
        )

        self.admin_user = User.objects.create_user(
            email="admin.pulse@test.com",
            password=self.password,
            first_name="Admin",
            last_name="Commander",
            role=Role.ADMINISTRATOR
        )

    def test_public_homepage_and_storytelling_flow(self):
        """Public homepage should render with storytelling hero and navigation."""
        res = self.client.get(reverse('public:home'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'From Academic Data')
        self.assertContains(res, 'Academic Intelligence')
        self.assertContains(res, '1. DATA')
        self.assertContains(res, '6. IMPROVE')
        self.assertContains(res, 'Live Demo & 7 Personas')

    def test_student_command_center_discoverability(self):
        """Student command center renders with complete 3-question hierarchy and navigation links."""
        self.client.login(email=self.student_user.email, password=self.password)
        res = self.client.get(reverse('portal:student_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Student Portal')
        self.assertContains(res, 'Academic Command Center')
        self.assertContains(res, 'Cumulative GPA')
        self.assertContains(res, 'Term Attendance')
        self.assertContains(res, 'Academic Risk Index')
        self.assertContains(res, 'Universal Evidence Inspector')
        self.assertContains(res, 'Closed-Loop Academic Intelligence Flow Architecture')

    def test_teacher_attention_radar_discoverability(self):
        """Teacher dashboard renders with 4-tier Attention Radar and action queues."""
        self.client.login(email=self.teacher_user.email, password=self.password)
        res = self.client.get(reverse('portal:teacher_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Faculty Portal')
        self.assertContains(res, 'Attention Radar')
        self.assertContains(res, 'Students Monitored')
        self.assertContains(res, 'CRITICAL ATTENTION')
        self.assertContains(res, 'STABLE & CONSISTENT')

    def test_admin_institutional_pulse_and_crud_discoverability(self):
        """Admin dashboard renders with macro KPIs, period-over-period pulse, and management hubs."""
        self.client.login(email=self.admin_user.email, password=self.password)
        res = self.client.get(reverse('portal_admin:dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Institution Administration Dashboard')
        self.assertContains(res, 'Institutional Pulse')
        self.assertContains(res, 'Institutional Risk Heatmap')
        self.assertContains(res, 'Intervention Outcome Analysis')
        self.assertContains(res, 'Academic Management Hubs')

    def test_judge_mode_toggle_preserves_functionality(self):
        """Judge Mode adds provenance badges without breaking rendering."""
        self.client.login(email=self.admin_user.email, password=self.password)
        res = self.client.get(reverse('portal_admin:dashboard') + '?judge_mode=1')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Judge Mode: <strong>ON</strong>')
