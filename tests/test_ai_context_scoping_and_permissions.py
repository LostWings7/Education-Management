"""
Unit tests for AI Context Scoping, Data Minimization, and Permission Boundaries.
"""

from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
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
from apps.ai_service.context import StudentContextBuilder, TeacherContextBuilder, AdminContextBuilder


class AIContextScopingAndPermissionsTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Faculty 1
        t1_u = User.objects.create_user(email='t1.ai@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T1-AI', department=self.dept)

        # Faculty 2
        t2_u = User.objects.create_user(email='t2.ai@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T2-AI', department=self.dept)

        # Student 1
        s1_u = User.objects.create_user(email='s1.ai@example.com', password='Password@123', role=Role.STUDENT, first_name='Student', last_name='One')
        self.student1 = StudentProfile.objects.create(user=s1_u, student_id='S1-AI', department=self.dept, program=self.prog)

        # Student 2
        s2_u = User.objects.create_user(email='s2.ai@example.com', password='Password@123', role=Role.STUDENT, first_name='Student', last_name='Two')
        self.student2 = StudentProfile.objects.create(user=s2_u, student_id='S2-AI', department=self.dept, program=self.prog)

        # Course & Section
        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section1 = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)
        Enrollment.objects.create(student=self.student1, class_section=self.section1, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_student_context_strictly_contains_own_data(self):
        """StudentContextBuilder constructs context scoped strictly to the student's enrollments."""
        ctx = StudentContextBuilder.build_context(self.student1)
        self.assertEqual(ctx.student_id, 'S1-AI')
        self.assertEqual(len(ctx.enrolled_courses), 1)
        self.assertEqual(ctx.enrolled_courses[0]['course_code'], 'CS201')

        # Verify Student 2 data is NOT in Student 1's context
        self.assertNotIn('S2-AI', str(ctx.__dict__))

    def test_teacher_context_data_minimization(self):
        """TeacherContextBuilder only includes sections where the teacher is assigned."""
        ctx1 = TeacherContextBuilder.build_context(self.teacher1)
        self.assertEqual(len(ctx1.assigned_sections), 1)
        self.assertEqual(ctx1.assigned_sections[0]['course_code'], 'CS201')

        # Teacher 2 has no assigned sections
        ctx2 = TeacherContextBuilder.build_context(self.teacher2)
        self.assertEqual(len(ctx2.assigned_sections), 0)

    def test_admin_context_aggregates_macrometrics(self):
        """AdminContextBuilder compiles aggregated departmental metrics without raw personal dumps."""
        ctx = AdminContextBuilder.build_context()
        self.assertEqual(ctx.total_enrollments, 1)
        self.assertTrue(len(ctx.department_summary) >= 1)
        self.assertEqual(ctx.department_summary[0]['department_code'], 'CSE')
