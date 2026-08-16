"""
Unit tests for Risk Engine Dynamic Renormalization, What-If Feasibility Solver, and Correlations.
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
    AssessmentResult,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission
)
from apps.analytics.services import (
    RiskEngineService,
    WhatIfSimulationService,
    CorrelationAnalyticsService
)
from apps.analytics.schemas.insight import (
    RiskLevel,
    ConfidenceLevel,
    DataQuality
)


class RiskAndSimulationTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='t.risk@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-RISK', department=self.dept)

        s_u = User.objects.create_user(email='s.risk@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-RISK', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

    def test_dynamic_weight_renormalization_missing_history(self):
        """
        When historical baseline is unavailable (first term student),
        available weights sum to 0.90 (0.25+0.30+0.20+0.15) and are normalized to 1.0.
        """
        # Attendance: 10/10 present -> Att Risk = 0 (w = 0.25)
        for i in range(10):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"Sess {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)

        # Assessments: 3 scores [80, 80, 80] -> Perf Risk = 0 (w = 0.30), Trend Risk = 20 (Stable, w = 0.20)
        for i in range(3):
            a = Assessment.objects.create(class_section=self.section, title=f"Q{i}", assessment_type=Assessment.AssessmentType.QUIZ, date=date(2026, 2, 1 + i), max_marks=Decimal('100.00'), weightage_percentage=Decimal('10.00'))
            AssessmentResult.objects.create(assessment=a, student=self.student, marks_obtained=Decimal('80.00'))

        # Assignments: 2 assigned, 2 submitted -> Assign Risk = 0 (w = 0.15)
        for i in range(2):
            assign = Assignment.objects.create(class_section=self.section, teacher=self.teacher, title=f"A{i}", max_marks=Decimal('50.00'), due_date=timezone.now() + timezone.timedelta(days=10 + i))
            AssignmentSubmission.objects.create(assignment=assign, student=self.student, obtained_marks=Decimal('45.00'))

        # Historical baseline: 0 past terms (NOT_AVAILABLE)
        risk = RiskEngineService.evaluate_course_risk(self.student, self.section)

        # Available weights sum = 0.90 -> confidence = MEDIUM
        self.assertEqual(risk.data_confidence, ConfidenceLevel.MEDIUM)
        # Expected composite: (0.25/0.9 * 0) + (0.30/0.9 * 0) + (0.20/0.9 * 20) + (0.15/0.9 * 0) = 4.0 / 0.9 = 4.44 -> 4.4
        self.assertAlmostEqual(risk.composite_score, 4.4, places=1)
        self.assertEqual(risk.risk_level, RiskLevel.LOW)

    def test_three_consecutive_failing_escalation(self):
        """Three consecutive evaluations strictly below 50% escalate risk level to at least HIGH."""
        # Attendance: 100% -> Att Risk = 0
        sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title="Sess 1")
        AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)

        # 3 consecutive scores: [45, 40, 35] -> failing streak
        for i, score in enumerate([45, 40, 35]):
            a = Assessment.objects.create(class_section=self.section, title=f"Q{i}", assessment_type=Assessment.AssessmentType.QUIZ, date=date(2026, 2, 1 + i), max_marks=Decimal('100.00'), weightage_percentage=Decimal('10.00'))
            AssessmentResult.objects.create(assessment=a, student=self.student, marks_obtained=Decimal(str(score)))

        risk = RiskEngineService.evaluate_course_risk(self.student, self.section)
        self.assertIn(risk.risk_level, [RiskLevel.HIGH, RiskLevel.CRITICAL])
        self.assertTrue(any('consecutive failing' in esc.lower() for esc in risk.escalations_applied))

    def test_what_if_target_grade_solver_feasible_and_impossible(self):
        """Test What-If Target Grade Feasibility Solver formulas."""
        # Course with Midterm (30% weight, scored 70%)
        midterm = Assessment.objects.create(class_section=self.section, title='Midterm', assessment_type=Assessment.AssessmentType.MIDTERM, date=date(2026, 3, 1), max_marks=Decimal('100.00'), weightage_percentage=Decimal('30.00'))
        AssessmentResult.objects.create(assessment=midterm, student=self.student, marks_obtained=Decimal('70.00'))

        # Remaining weight = 70%. Evaluated points = 70 * 30 = 2100.
        # Scenario 1: Target = 80%.
        # Needed points = 80 * 100 - 2100 = 8000 - 2100 = 5900.
        # Required score = 5900 / 70 = 84.29% -> Feasible!
        res_feasible = WhatIfSimulationService.solve_required_score_for_target(self.student, self.section, target_grade_percentage=80.0)
        self.assertTrue(res_feasible.is_feasible)
        self.assertAlmostEqual(res_feasible.required_score, 84.29, places=1)

        # Scenario 2: Target = 95%.
        # Needed points = 9500 - 2100 = 7400.
        # Required score = 7400 / 70 = 105.71% > 100% -> Impossible!
        res_impossible = WhatIfSimulationService.solve_required_score_for_target(self.student, self.section, target_grade_percentage=95.0)
        self.assertFalse(res_impossible.is_feasible)
        self.assertAlmostEqual(res_impossible.required_score, 105.71, places=1)
        self.assertIn('mathematically impossible', res_impossible.explanation.lower())

    def test_correlations_guards(self):
        """Test sample size guard (N < 10) and zero-variance guard."""
        # N = 5 pairs -> insufficient
        pairs_small = [(80.0, 75.0), (85.0, 80.0), (90.0, 88.0), (70.0, 65.0), (60.0, 58.0)]
        res_small = CorrelationAnalyticsService.compute_pearson(pairs_small)
        self.assertEqual(res_small.data_quality, DataQuality.INSUFFICIENT_DATA)
        self.assertIsNone(res_small.pearson_r)

        # N = 10 pairs with constant Y -> zero variance
        pairs_zero_var = [(float(i * 10), 80.0) for i in range(10)]
        res_zero_var = CorrelationAnalyticsService.compute_pearson(pairs_zero_var)
        self.assertEqual(res_zero_var.data_quality, DataQuality.UNDEFINED)
        self.assertIn('zero variance', res_zero_var.relationship_description.lower())

        # N = 10 pairs with positive correlation
        pairs_valid = [(float(50 + i * 5), float(50 + i * 5)) for i in range(10)]
        res_valid = CorrelationAnalyticsService.compute_pearson(pairs_valid)
        self.assertEqual(res_valid.data_quality, DataQuality.VALID)
        self.assertEqual(res_valid.pearson_r, 1.0)
        self.assertIn('does not imply causation', res_valid.disclaimer.lower())
