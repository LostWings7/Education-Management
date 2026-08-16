"""
Unit tests for Performance, Trajectory OLS Trends, and Anomaly Detection.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
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
    Assessment,
    AssessmentResult
)
from apps.analytics.services import (
    PerformanceAnalyticsService,
    TrendAnalyticsService,
    AnomalyDetectionService
)
from apps.analytics.schemas.insight import TrendDirection, DataQuality


class PerformanceAndTrendsTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='t.perf@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-PERF', department=self.dept)

        s_u = User.objects.create_user(email='s.perf@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-PERF', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

    def test_weighted_course_score_and_consistency(self):
        """Test weighted score normalization and standard deviation consistency."""
        a1 = Assessment.objects.create(class_section=self.section, title='Quiz 1', assessment_type=Assessment.AssessmentType.QUIZ, date=date(2026, 2, 1), max_marks=Decimal('20.00'), weightage_percentage=Decimal('10.00'))
        a2 = Assessment.objects.create(class_section=self.section, title='Midterm', assessment_type=Assessment.AssessmentType.MIDTERM, date=date(2026, 3, 1), max_marks=Decimal('100.00'), weightage_percentage=Decimal('30.00'))

        # Quiz 1: 18/20 = 90.0% (w=10)
        AssessmentResult.objects.create(assessment=a1, student=self.student, marks_obtained=Decimal('18.00'))
        # Midterm: 80/100 = 80.0% (w=30)
        AssessmentResult.objects.create(assessment=a2, student=self.student, marks_obtained=Decimal('80.00'))

        # Evaluated weight = 40%. Weighted sum = (90 * 0.1) + (80 * 0.3) = 9.0 + 24.0 = 33.0 / 0.4 = 82.5%
        res = PerformanceAnalyticsService.calculate_course_performance(self.student, self.section)
        self.assertEqual(res.weighted_score, 82.5)
        self.assertEqual(res.average_score, 85.0)
        self.assertEqual(res.completed_weight, 40.0)
        self.assertEqual(res.evaluations_count, 2)
        self.assertEqual(res.consistency_label, "High Consistency")

    def test_trajectory_ols_trend_classification(self):
        """Test OLS assessment trajectory slope classification."""
        # Insufficient data: 2 observations
        res_insuf = TrendAnalyticsService._compute_trajectory_from_sequence([80.0, 85.0])
        self.assertEqual(res_insuf.direction, TrendDirection.INSUFFICIENT_DATA)

        # Improving sequence: 60 -> 70 -> 80 (slope = +10.0 pts/step)
        res_imp = TrendAnalyticsService._compute_trajectory_from_sequence([60.0, 70.0, 80.0])
        self.assertEqual(res_imp.direction, TrendDirection.IMPROVING)
        self.assertEqual(res_imp.slope, 10.0)

        # Declining sequence: 85 -> 75 -> 65 (slope = -10.0 pts/step)
        res_dec = TrendAnalyticsService._compute_trajectory_from_sequence([85.0, 75.0, 65.0])
        self.assertEqual(res_dec.direction, TrendDirection.DECLINING)
        self.assertEqual(res_dec.slope, -10.0)

        # Stable sequence: 75 -> 76 -> 74 (slope = -0.5 pts/step, std <= 8)
        res_stab = TrendAnalyticsService._compute_trajectory_from_sequence([75.0, 76.0, 74.0])
        self.assertEqual(res_stab.direction, TrendDirection.STABLE)

    def test_anomaly_detection_persona_7_arithmetic(self):
        """
        Verify Persona 7 acute plunge arithmetic:
        Baseline: [75, 78, 76] -> mean = 76.33, std = 1.25.
        Current: 38.0.
        Effective std floor = max(1.25, 3.0) = 3.0.
        Z = (38.0 - 76.33) / 3.0 = -12.78.
        Drop delta = 76.33 - 38.0 = 38.33 points >= 25.0 threshold.
        """
        anomaly = AnomalyDetectionService.detect_from_sequence([75.0, 78.0, 76.0, 38.0], context_name="CS201")
        self.assertTrue(anomaly.is_anomaly)
        self.assertEqual(anomaly.anomaly_type, "ACUTE_DROP")
        self.assertEqual(anomaly.severity, "CRITICAL")
        self.assertEqual(anomaly.baseline_mean, 76.33)
        self.assertEqual(anomaly.delta, 38.33)
        self.assertEqual(anomaly.z_score, -12.78)

    def test_anomaly_normal_variation_not_flagged(self):
        """Normal score fluctuation is not flagged as an anomaly."""
        anomaly = AnomalyDetectionService.detect_from_sequence([80.0, 82.0, 78.0, 81.0], context_name="CS201")
        self.assertFalse(anomaly.is_anomaly)
        self.assertEqual(anomaly.anomaly_type, "NONE")
