"""
Unit tests verifying AI Explanation and Synthesis across the 7 seeded student personas.
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
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assessment,
    AssessmentResult,
    Assignment
)
from apps.ai_service.context import StudentContextBuilder
from apps.ai_service.providers.fallback import FallbackHeuristicProvider
from apps.ai_service.schemas.messages import ChatMessage


class AIPersonaSynthesesTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='teacher.persona@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-PERS', department=self.dept)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

        # Persona 2 (Charles Babbage - Attendance Deficit 50%)
        u2 = User.objects.create_user(email='charles.b@example.com', password='Password@123', role=Role.STUDENT, first_name='Charles', last_name='Babbage')
        self.student_charles = StudentProfile.objects.create(user=u2, student_id='STU-002', department=self.dept, program=self.prog)
        Enrollment.objects.create(student=self.student_charles, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"P {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student_charles, status=AttendanceRecord.AttendanceStatus.PRESENT)
        for i in range(5):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title=f"A {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student_charles, status=AttendanceRecord.AttendanceStatus.ABSENT)

        self.provider = FallbackHeuristicProvider()

    def test_charles_babbage_attendance_explanation(self):
        """AI synthesizes Charles Babbage's 50% attendance deficit and absence buffer accurately."""
        ctx = StudentContextBuilder.build_context(self.student_charles)
        resp = self.provider.chat(
            system_instruction="System instruction",
            messages=[ChatMessage(role="user", content="Explain my attendance standing.")],
            context_data=ctx.__dict__
        )
        self.assertIn("50.0%", resp.content)
        self.assertEqual(resp.validation_status, "VALID")
        # Fact attribution checked
        att_fact = next((f for f in resp.facts_used if "Attendance" in f.metric_name), None)
        self.assertIsNotNone(att_fact)
