"""
Unit tests for Role-Based Access Control and data isolation in Academic Operations.
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
    Course,
    ClassSection,
    AcademicYear,
    Semester
)
from apps.academic.services import EnrollmentService


class AcademicPermissionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Teacher 1 (assigned)
        t1_u = User.objects.create_user(email='t1@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T-01', department=self.dept)

        # Teacher 2 (unassigned)
        t2_u = User.objects.create_user(email='t2@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T-02', department=self.dept)

        # Student
        s_u = User.objects.create_user(email='s1@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-01', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)

    def test_student_cannot_access_teacher_gradebook(self):
        """Student role is denied access to teacher gradebook."""
        self.client.login(email='s1@example.com', password='Password@123')
        response = self.client.get(reverse('portal:teacher_gradebook'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_take_attendance(self):
        """Student role is denied access to take attendance view."""
        self.client.login(email='s1@example.com', password='Password@123')
        response = self.client.get(reverse('portal:teacher_take_attendance', kwargs={'section_id': self.section.pk}))
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_access_unassigned_section_take_attendance(self):
        """Teacher 2 cannot take attendance for a section assigned exclusively to Teacher 1 (returns 404)."""
        self.client.login(email='t2@example.com', password='Password@123')
        response = self.client.get(reverse('portal:teacher_take_attendance', kwargs={'section_id': self.section.pk}))
        self.assertEqual(response.status_code, 404)

    def test_teacher_cannot_access_student_grades_portal(self):
        """Teacher role is denied access to student personal grades view."""
        self.client.login(email='t1@example.com', password='Password@123')
        response = self.client.get(reverse('portal:student_grades'))
        self.assertEqual(response.status_code, 403)
