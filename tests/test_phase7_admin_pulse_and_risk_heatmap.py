"""
Phase 7 Automated Tests: Institutional Pulse Change Detection, Risk Heatmap Privacy & Intervention Outcomes.
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
    AcademicYear,
    Semester,
    Course,
    ClassSection,
    Enrollment
)
from apps.analytics.services import InstitutionalChangeDetectionService
from apps.interventions.models import Intervention


class Phase7AdminPulseAndRiskHeatmapTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            role=Role.ADMINISTRATOR,
            first_name="Grace",
            last_name="Hopper"
        )

        self.dept_small = Department.objects.create(name="Philosophy", code="PHIL")
        self.prog_small = Program.objects.create(name="B.A. Philosophy", code="BAPHIL", department=self.dept_small)

        self.dept_large = Department.objects.create(name="Computer Science", code="CS")
        self.prog_large = Program.objects.create(name="B.Sc. CS", code="BSCS", department=self.dept_large)

        # Create 1 student in small dept (N=1 < 3 -> should be suppressed)
        u1 = User.objects.create_user(email="s1@example.com", password="Password123!", role=Role.STUDENT)
        self.s1 = StudentProfile.objects.create(user=u1, student_id="STU-101", department=self.dept_small, program=self.prog_small)

        # Create 4 students in large dept (N=4 >= 3 -> not suppressed)
        for i in range(2, 6):
            u = User.objects.create_user(email=f"s{i}@example.com", password="Password123!", role=Role.STUDENT)
            StudentProfile.objects.create(user=u, student_id=f"STU-10{i}", department=self.dept_large, program=self.prog_large)

        self.ay = AcademicYear.objects.create(name="2025-2026", start_date=date(2025, 9, 1), end_date=date(2026, 6, 30))
        self.sem_prev = Semester.objects.create(academic_year=self.ay, semester_number=1, name="Fall 2025", start_date=date(2025, 9, 1), end_date=date(2025, 12, 31), is_completed=True)
        self.sem_curr = Semester.objects.create(academic_year=self.ay, semester_number=2, name="Spring 2026", start_date=date(2026, 2, 1), end_date=date(2026, 6, 30), is_active=True)

    def test_institutional_change_detection_service(self):
        """
        Verify that InstitutionalChangeDetectionService compares active vs previous semester metrics.
        """
        changes = InstitutionalChangeDetectionService.evaluate_institutional_changes()
        self.assertEqual(changes['status'], 'VALID')
        self.assertEqual(changes['active_semester'], 'Spring 2026')
        self.assertEqual(changes['previous_semester'], 'Fall 2025')
        self.assertIn('attendance', changes['metrics'])
        self.assertIn('performance', changes['metrics'])
        self.assertIn('interventions', changes['metrics'])

    def test_admin_risk_heatmap_privacy_guard(self):
        """
        Verify that AdminRiskHeatmapView suppresses risk cells when population < 3.
        """
        self.client.login(email="admin@example.com", password="Password123!")
        url = reverse('portal_admin:risk_heatmap')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('dept_matrix', response.context)

        # Small department (N=1) must be suppressed
        small_row = next(r for r in response.context['dept_matrix'] if r['department'].code == 'PHIL')
        self.assertTrue(small_row['is_suppressed'])
        self.assertIn('Minimum Threshold', small_row['suppression_reason'])

        # Large department (N=4) must NOT be suppressed
        large_row = next(r for r in response.context['dept_matrix'] if r['department'].code == 'CS')
        self.assertFalse(large_row['is_suppressed'])
        self.assertEqual(large_row['total_students'], 4)

    def test_admin_intervention_outcome_analysis_view(self):
        """
        Verify Intervention Outcome Analysis view renders category outcomes and non-causal disclaimer.
        """
        self.client.login(email="admin@example.com", password="Password123!")
        url = reverse('portal_admin:intervention_outcomes')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('category_analytics', response.context)
        self.assertIn('non_causal_disclaimer', response.context)
        self.assertIn('statistical associations', response.context['non_causal_disclaimer'])
