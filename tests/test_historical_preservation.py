"""
Unit tests for Historical Multi-Semester Academic Data Preservation & Demo Personas.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.management import call_command
from apps.core.models import User
from apps.academic.models import (
    Semester,
    StudentProfile,
    Enrollment,
    AssessmentResult,
    ClassSession,
    AttendanceRecord,
    AssignmentSubmission
)
from apps.academic.services import EnrollmentService, AttendanceService


class HistoricalPreservationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Run full seed data
        call_command('seed_demo_data')

    def test_multi_semester_query_isolation(self):
        """Historical completed term (Fall 2025) and active term (Spring 2026) remain distinct and queryable."""
        sem_fall = Semester.objects.filter(name='Fall 2025').first()
        sem_spring = Semester.objects.filter(name='Spring 2026').first()

        self.assertIsNotNone(sem_fall)
        self.assertIsNotNone(sem_spring)
        self.assertTrue(sem_fall.is_completed)
        self.assertTrue(sem_spring.is_active)

        # Query student 1 enrollments in past vs active
        sp = StudentProfile.objects.get(user__email='student@example.com')
        active_enrs = EnrollmentService.get_student_enrollments(sp, semester=sem_spring)
        hist_enrs = EnrollmentService.get_student_enrollments(sp, semester=sem_fall)

        self.assertGreaterEqual(active_enrs.count(), 2)
        self.assertGreaterEqual(hist_enrs.count(), 2)

        # Check that historical enrollment has preserved published snapshot
        for he in hist_enrs:
            self.assertEqual(he.status, Enrollment.EnrollmentStatus.COMPLETED)
            self.assertTrue(he.is_grade_published)
            self.assertIsNotNone(he.final_percentage)

    def test_persona_7_sudden_performance_anomaly(self):
        """Verify Persona 7 (student7@example.com) has genuine baseline scores followed by sudden sharp drop to 38."""
        sp7 = StudentProfile.objects.get(user__email='student7@example.com')
        results = AssessmentResult.objects.filter(student=sp7, assessment__class_section__course__code='CS201').order_by('assessment__date')

        scores = [float(r.marks_obtained) for r in results]
        # Baseline ~75, 78, 76 then sudden plunge to 38
        self.assertIn(38.0, scores)
        self.assertEqual(scores[-1], 38.0)
        self.assertGreaterEqual(scores[0], 70.0)

    def test_persona_2_chronic_attendance_deficit(self):
        """Verify Persona 2 (student2@example.com) attendance percentage is dynamically low (~50%)."""
        sp2 = StudentProfile.objects.get(user__email='student2@example.com')
        metrics = AttendanceService.calculate_student_attendance(sp2)

        self.assertLessEqual(metrics['attendance_percentage'], 60.0)
        self.assertEqual(metrics['status'], 'CRITICAL')
        self.assertTrue(metrics['is_below_minimum'])
        self.assertGreaterEqual(metrics['absent_count'], 5)

    def test_granular_records_exist(self):
        """Verify genuine underlying records exist across sessions, attendance records, submissions, results."""
        self.assertGreaterEqual(ClassSession.objects.count(), 20)
        self.assertGreaterEqual(AttendanceRecord.objects.count(), 100)
        self.assertGreaterEqual(AssignmentSubmission.objects.count(), 15)
        self.assertGreaterEqual(AssessmentResult.objects.count(), 20)
