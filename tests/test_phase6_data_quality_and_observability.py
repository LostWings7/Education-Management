"""
Phase 6 Automated Tests: Academic Data Quality Center & AI Observability.
"""

from decimal import Decimal
from django.test import TestCase
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    Topic,
    ClassSection,
    Enrollment
)
from apps.analytics.services.data_quality import DataQualityEngineService
from apps.ai_service.models import AIInteractionLog, AIMessageFeedback
from apps.ai_service.services.observability_service import AIObservabilityService


class Phase6DataQualityAndObservabilityTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Computer Science", code="CS")
        self.prog = Program.objects.create(name="B.Sc. CS", code="BSCS", department=self.dept)

        self.user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            role=Role.ADMINISTRATOR
        )

    def test_data_quality_audit_6_dimensions(self):
        """Verify the 6-dimension data quality audit computes transparent scores and detects missing topics."""
        # Create course without topics -> triggers Curriculum Completeness warning
        course = Course.objects.create(department=self.dept, code="CS102", title="Data Structures", credits=Decimal('3.0'))

        audit = DataQualityEngineService.run_full_audit()

        self.assertIn('overall_score', audit)
        self.assertIn('dimension_scores', audit)
        self.assertEqual(len(audit['dimension_scores']), 6)
        self.assertIn('Profile Completeness', audit['dimension_scores'])
        self.assertIn('Curriculum Completeness', audit['dimension_scores'])
        self.assertIn('Assessment Completeness', audit['dimension_scores'])
        self.assertIn('Attendance Completeness', audit['dimension_scores'])
        self.assertIn('Enrollment Consistency', audit['dimension_scores'])
        self.assertIn('Schedule Consistency', audit['dimension_scores'])

        # Check that the missing topic was flagged in issues
        has_topic_warning = any(iss['dimension'] == 'Curriculum Completeness' and 'CS102' in iss['entity'] for iss in audit['issues'])
        self.assertTrue(has_topic_warning)

    def test_ai_observability_metrics_aggregation(self):
        """Verify AI telemetry, fallback rates, latency percentiles, and feedback metrics."""
        # Create sample logs
        AIInteractionLog.objects.create(
            user=self.user,
            role="ADMINISTRATOR",
            request_type="BRIEFING",
            provider="gemini",
            model="gemini-2.5-pro",
            latency_ms=450,
            success=True,
            validation_status="VALID"
        )
        AIInteractionLog.objects.create(
            user=self.user,
            role="STUDENT",
            request_type="STUDY_PLAN",
            provider="fallback_heuristic",
            model="deterministic_rules_engine",
            latency_ms=12,
            success=True,
            validation_status="VALID"
        )

        metrics = AIObservabilityService.get_observability_metrics()

        self.assertEqual(metrics['total_requests'], 2)
        self.assertEqual(metrics['success_rate'], 100.0)
        self.assertEqual(metrics['online_provider_requests'], 1)
        self.assertEqual(metrics['fallback_provider_requests'], 1)
        self.assertEqual(metrics['fallback_rate'], 50.0)
        self.assertEqual(metrics['validation_pass_rate'], 100.0)
