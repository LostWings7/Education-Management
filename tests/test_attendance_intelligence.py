"""
Unit tests for Deterministic Attendance Intelligence Service & Absence Buffer formulas.
"""

from datetime import date
from django.test import TestCase
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
    ClassSession,
    AttendanceRecord
)
from apps.analytics.services import AttendanceAnalyticsService
from apps.analytics.schemas.insight import DataQuality


class AttendanceIntelligenceTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='t.att@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-ATT', department=self.dept)

        s_u = User.objects.create_user(email='s.att@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-ATT', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS101', title='Intro to CS', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

    def _create_sessions_and_records(self, present_count, absent_count, late_count=0):
        for i in range(present_count):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"Session P{i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)
        for i in range(absent_count):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"Session A{i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.ABSENT)
        for i in range(late_count):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"Session L{i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.LATE)

    def test_absence_buffer_formula_standard(self):
        """
        Test absence buffer calculation: b = floor(P + R - T(N+R)/100).
        Scenario: 16 conducted sessions (14 present, 2 absent). Total term sessions = 20 (R = 4).
        P = 14, N = 16, R = 4, T = 75%.
        b = floor(14 + 4 - 0.75 * 20) = floor(18 - 15) = 3 classes.
        """
        self._create_sessions_and_records(present_count=14, absent_count=2)
        res = AttendanceAnalyticsService.calculate_course_attendance(
            self.student, self.section, target_threshold=75.0, estimated_total_term_sessions=20
        )
        self.assertEqual(res.attendance_percentage, 87.5)
        self.assertEqual(res.absence_buffer, 3)
        self.assertEqual(res.remaining_sessions, 4)
        self.assertFalse(res.is_below_threshold)
        self.assertTrue(res.is_recovery_possible)

    def test_absence_buffer_boundary_zero_buffer(self):
        """
        Scenario: Exactly at margin where missing 1 class drops below 75%.
        N = 16 (12 present, 4 absent). Total = 20 (R = 4).
        P = 12, N = 16, R = 4, T = 75%.
        b = floor(12 + 4 - 0.75 * 20) = floor(16 - 15) = 1 class.
        If student misses 1 class, finishes at 15/20 = 75.0% (clamped buffer = 1).
        """
        self._create_sessions_and_records(present_count=12, absent_count=4)
        res = AttendanceAnalyticsService.calculate_course_attendance(
            self.student, self.section, target_threshold=75.0, estimated_total_term_sessions=20
        )
        self.assertEqual(res.attendance_percentage, 75.0)
        self.assertEqual(res.absence_buffer, 1)

    def test_absence_buffer_depleted_and_recovery_required(self):
        """
        Scenario: Below threshold (8 present, 8 absent). N = 16, R = 4, Total = 20.
        P = 8, T = 75%.
        b = floor(8 + 4 - 0.75 * 20) = floor(12 - 15) = -3 -> clamped to 0.
        Required sessions to reach 75%: ceil((75*16 - 100*8) / 25) = ceil((1200 - 800) / 25) = 16 sessions.
        Since 16 > R (4), is_recovery_possible = False.
        """
        self._create_sessions_and_records(present_count=8, absent_count=8)
        res = AttendanceAnalyticsService.calculate_course_attendance(
            self.student, self.section, target_threshold=75.0, estimated_total_term_sessions=20
        )
        self.assertEqual(res.attendance_percentage, 50.0)
        self.assertEqual(res.absence_buffer, 0)
        self.assertTrue(res.is_below_threshold)
        self.assertEqual(res.required_sessions, 16)
        self.assertFalse(res.is_recovery_possible)

    def test_late_credits_half_point(self):
        """Late attendance credits 0.5 points."""
        self._create_sessions_and_records(present_count=10, absent_count=0, late_count=2)
        # N = 12, P = 10 + 0.5 * 2 = 11.0. % = 11 / 12 * 100 = 91.67%
        res = AttendanceAnalyticsService.calculate_course_attendance(
            self.student, self.section, target_threshold=75.0, estimated_total_term_sessions=20
        )
        self.assertAlmostEqual(res.attendance_percentage, 91.67, places=1)
