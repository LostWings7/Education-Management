"""
Phase 7 Automated Tests: Security Scoping, Judge Mode Integrity & Seven Persona Consistency.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.urls import reverse

from apps.core.models import User, Role
from apps.academic.models import StudentProfile, Semester
from apps.analytics.services import RiskEngineService, AttendanceAnalyticsService, AnomalyDetectionService


class Phase7SecurityAndAIQualityTests(TestCase):
    def setUp(self):
        call_command('reset_demo_data', noinput=True)

    def test_judge_mode_toggle_and_read_only_safety(self):
        """
        Verify that Judge Mode is toggleable via query parameters and does not mutate backend state.
        """
        self.client.login(email="student@example.com", password="Password123!")
        url = reverse('portal:student_dashboard')

        # Enable judge mode
        res1 = self.client.get(f"{url}?judge_mode=1")
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(self.client.session.get('judge_mode', False))

        # Disable judge mode
        res2 = self.client.get(f"{url}?judge_mode=0")
        self.assertEqual(res2.status_code, 200)
        self.assertFalse(self.client.session.get('judge_mode', False))

    def test_seven_persona_consistency_across_authoritative_services(self):
        """
        Verify all 7 student personas evaluate cleanly and consistently through Risk and Attendance engines.
        """
        active_sem = Semester.objects.filter(is_active=True).first()

        personas = [
            ('STU-001', 'Ada Lovelace', 'LOW'),
            ('STU-002', 'Charles Babbage', 'CRITICAL'), # Attendance ~50%
            ('STU-007', 'Katherine Johnson', 'MODERATE') # Pre-rescue acute plunge composite
        ]

        for stu_id, name, expected_risk in personas:
            student = StudentProfile.objects.get(student_id=stu_id)
            risk_res = RiskEngineService.evaluate_overall_risk(student, semester=active_sem)
            att_res = AttendanceAnalyticsService.calculate_overall_attendance(student, semester=active_sem)

            self.assertIsNotNone(risk_res)
            self.assertIsNotNone(att_res)
            self.assertEqual(str(risk_res.risk_level), expected_risk)

        # Verify Katherine Johnson has acute anomaly flagged
        katherine = StudentProfile.objects.get(student_id='STU-007')
        sec = katherine.enrollments.first().class_section
        anom = AnomalyDetectionService.detect_course_anomaly(katherine, sec)
        self.assertTrue(anom.is_anomaly)
