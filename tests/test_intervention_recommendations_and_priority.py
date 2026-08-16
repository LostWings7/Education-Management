"""
Unit tests for Phase 4 Recommendation Generation, Prioritization Formulas, and Deduplication.
"""

from decimal import Decimal
from datetime import date
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
    Topic,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assessment,
    AssessmentResult,
    LearningResource
)
from apps.interventions.models import Intervention
from apps.interventions.services import (
    InterventionRecommendationService,
    InterventionPrioritizationService
)


class InterventionRecommendationsAndPriorityTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='teacher.rec@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-REC', department=self.dept)

        s_u = User.objects.create_user(email='student.rec@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-REC', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.topic = Topic.objects.create(course=self.course, title='Binary Trees', order_index=1)

        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)
        self.enrollment = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        # Published learning resource for Binary Trees
        self.resource = LearningResource.objects.create(
            course=self.course,
            topic=self.topic,
            title="Binary Trees Lecture Slides",
            resource_type=LearningResource.ResourceType.PDF,
            is_published=True
        )

    def test_prioritization_formula(self):
        """
        Verify multi-factor priority score calculation:
        P_score = 0.35 * R + 0.30 * S + 0.20 * A + 0.15 * D
        Scenario: Risk = 60.0, Severity = CRITICAL (100.0), Anomaly = True (100.0), Deadline Near = False (20.0).
        P_score = (0.35 * 60) + (0.30 * 100) + (0.20 * 100) + (0.15 * 20)
                = 21.0 + 30.0 + 20.0 + 3.0 = 74.0 -> HIGH.
        """
        score = InterventionPrioritizationService.calculate_priority_score(
            risk_score=60.0,
            severity='CRITICAL',
            is_anomaly=True,
            is_deadline_near=False
        )
        self.assertEqual(score, 74.0)
        self.assertEqual(InterventionPrioritizationService.classify_priority(score), Intervention.Priority.HIGH)

    def test_acute_anomaly_generates_faculty_diagnostic_recommendation(self):
        """
        Persona 7 scenario: Baseline scores [75, 78, 76] then acute plunge to 38.
        Recommendation engine generates FACULTY_DIAGNOSTIC recommendation.
        """
        scores = [75.0, 78.0, 76.0, 38.0]
        for i, sc in enumerate(scores):
            a = Assessment.objects.create(
                class_section=self.section,
                title=f"Eval {i}",
                assessment_type=Assessment.AssessmentType.QUIZ,
                date=date(2026, 2, 1 + i),
                max_marks=Decimal('100.00'),
                weightage_percentage=Decimal('10.00')
            )
            AssessmentResult.objects.create(assessment=a, student=self.student, marks_obtained=Decimal(str(sc)))

        recs = InterventionRecommendationService.generate_recommendations_for_student_section(
            student=self.student,
            section=self.section,
            creator_user=self.teacher.user
        )
        self.assertTrue(len(recs) >= 1)
        diag_rec = next((r for r in recs if r.category == Intervention.InterventionCategory.FACULTY_DIAGNOSTIC), None)
        self.assertIsNotNone(diag_rec)
        self.assertEqual(diag_rec.status, Intervention.Status.RECOMMENDED)
        self.assertEqual(diag_rec.primary_target_metric, Intervention.TargetMetric.ANOMALY_RECOVERY)
        self.assertIn('acute score plunge', diag_rec.title.lower())

    def test_attendance_deficit_generates_attendance_recovery_plan(self):
        """
        Attendance < 60% generates ATTENDANCE_RECOVERY recommendation with attendance target.
        """
        # 5 present, 5 absent -> 50.0%
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"P {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"A {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.ABSENT)

        recs = InterventionRecommendationService.generate_recommendations_for_student_section(
            student=self.student,
            section=self.section,
            creator_user=self.teacher.user
        )
        att_rec = next((r for r in recs if r.category == Intervention.InterventionCategory.ATTENDANCE_RECOVERY), None)
        self.assertIsNotNone(att_rec)
        self.assertEqual(att_rec.primary_target_metric, Intervention.TargetMetric.ATTENDANCE)

    def test_deduplication_guard_prevents_duplicate_active_recommendations(self):
        """
        Running the recommendation scan multiple times does not duplicate existing recommendations.
        """
        # 5 present, 5 absent
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"P {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"A {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.ABSENT)

        recs1 = InterventionRecommendationService.generate_recommendations_for_student_section(
            student=self.student,
            section=self.section,
            creator_user=self.teacher.user
        )
        count_first = len(recs1)
        self.assertTrue(count_first > 0)

        # Second scan should yield 0 new recommendations because they already exist
        recs2 = InterventionRecommendationService.generate_recommendations_for_student_section(
            student=self.student,
            section=self.section,
            creator_user=self.teacher.user
        )
        self.assertEqual(len(recs2), 0)
