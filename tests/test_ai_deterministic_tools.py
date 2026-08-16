"""
Unit tests for Authorized Deterministic Tools and cross-user authorization barriers.
"""

from datetime import date
from django.test import TestCase
from django.core.exceptions import PermissionDenied
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
    AttendanceRecord
)
from apps.ai_service.services import AuthorizedToolsService


class AIDeterministicToolsTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t1_u = User.objects.create_user(email='teacher.tool@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T-TOOL', department=self.dept)

        t2_u = User.objects.create_user(email='other.teacher@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T-OTHER', department=self.dept)

        s_u = User.objects.create_user(email='student.tool@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-TOOL', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)
        Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        # 4 sessions (3 present, 1 absent)
        for i in range(3):
            sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher1, title=f"S {i}")
            AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)
        sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher1, title="S 3")
        AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.ABSENT)

    def test_student_can_execute_authorized_attendance_tool(self):
        """Student successfully executes get_my_attendance_buffer tool."""
        res = AuthorizedToolsService.execute_tool(
            tool_name='get_my_attendance_buffer',
            arguments={'course_id': self.course.pk, 'target_percentage': 75.0},
            user=self.student.user
        )
        self.assertEqual(res['tool'], 'get_my_attendance_buffer')
        self.assertEqual(res['current_attendance_percentage'], 75.0)

    def test_cross_role_tool_execution_is_rejected(self):
        """Student attempting to call teacher/admin tool receives PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            AuthorizedToolsService.execute_tool(
                tool_name='get_section_summary',
                arguments={'section_id': self.section.pk},
                user=self.student.user
            )

    def test_teacher_cannot_inspect_unassigned_section(self):
        """Teacher 2 receives PermissionDenied when attempting to inspect Teacher 1's section."""
        with self.assertRaises(PermissionDenied):
            AuthorizedToolsService.execute_tool(
                tool_name='get_section_summary',
                arguments={'section_id': self.section.pk},
                user=self.teacher2.user
            )
