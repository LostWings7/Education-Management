"""
Phase 7 Automated Tests: Demo Reset Command & State-Aware 12-Step Academic Rescue Flow.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from apps.core.models import User, Role
from apps.academic.models import StudentProfile, ClassSection, AssessmentResult


class Phase7DemoRescueAndResetTests(TestCase):
    @override_settings(DEMO_MODE=True)
    def test_reset_demo_data_command_success(self):
        """
        Verify that python manage.py reset_demo_data seeds all 7 personas when DEMO_MODE=True.
        """
        call_command('reset_demo_data', noinput=True)

        self.assertEqual(StudentProfile.objects.filter(student_id='STU-001').count(), 1)
        self.assertEqual(StudentProfile.objects.filter(student_id='STU-007').count(), 1)

    @override_settings(DEMO_MODE=False)
    def test_reset_demo_data_command_rejected_in_production(self):
        """
        Verify that reset_demo_data raises CommandError when DEMO_MODE=False.
        """
        with self.assertRaises(CommandError):
            call_command('reset_demo_data', noinput=True)

    @override_settings(DEMO_MODE=True)
    def test_demo_execute_rescue_step_dynamic_recalculation(self):
        """
        Verify that DemoExecuteRescueStepView records real 88% assessment result and recalculates risk.
        """
        call_command('reset_demo_data', noinput=True)

        url = reverse('public:demo_execute_rescue_step')
        response = self.client.post(url, {'action': 'record_recovery_assessment'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['recovery_score'], 88.0)
        self.assertEqual(data['intervention_status'], 'EFFECTIVE')

        # Verify real database record
        katherine = StudentProfile.objects.get(student_id='STU-007')
        recov_res = AssessmentResult.objects.filter(student=katherine, assessment__title__icontains="Recovery").first()
        self.assertIsNotNone(recov_res)
        self.assertEqual(recov_res.marks_obtained, Decimal('88.0'))
