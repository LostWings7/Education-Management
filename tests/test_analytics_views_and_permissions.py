"""
Unit tests for Analytics Views, Data Isolation, and RBAC Security.
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
    Enrollment
)


class AnalyticsViewsAndPermissionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Faculty 1 (Assigned)
        t1_u = User.objects.create_user(email='t1.an@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T1-AN', department=self.dept)

        # Faculty 2 (Unassigned)
        t2_u = User.objects.create_user(email='t2.an@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T2-AN', department=self.dept)

        # Student 1
        s1_u = User.objects.create_user(email='s1.an@example.com', password='Password@123', role=Role.STUDENT)
        self.student1 = StudentProfile.objects.create(user=s1_u, student_id='S1-AN', department=self.dept, program=self.prog)

        # Student 2
        s2_u = User.objects.create_user(email='s2.an@example.com', password='Password@123', role=Role.STUDENT)
        self.student2 = StudentProfile.objects.create(user=s2_u, student_id='S2-AN', department=self.dept, program=self.prog)

        # Admin
        self.admin = User.objects.create_superuser(email='admin.an@example.com', password='Password@123', role=Role.ADMINISTRATOR)

        # Course & Section
        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)
        Enrollment.objects.create(student=self.student1, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_student_can_view_own_analytics_and_what_if(self):
        """Student can view personal analytics and simulation studio."""
        self.client.login(email='s1.an@example.com', password='Password@123')
        res = self.client.get(reverse('portal:student_analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Academic Intelligence & Analytics')

        res_whatif = self.client.get(reverse('portal:student_what_if'))
        self.assertEqual(res_whatif.status_code, 200)
        self.assertContains(res_whatif, 'What-If Simulation Studio')

    def test_student_cannot_access_teacher_or_admin_analytics(self):
        """Student receives 403 when trying to access faculty or admin intelligence."""
        self.client.login(email='s1.an@example.com', password='Password@123')
        res_t = self.client.get(reverse('portal:teacher_analytics'))
        self.assertEqual(res_t.status_code, 403)

        res_adm = self.client.get(reverse('portal_admin:analytics'))
        self.assertEqual(res_adm.status_code, 403)

    def test_teacher_can_view_assigned_class_analytics_and_early_warnings(self):
        """Teacher can view assigned section analytics and early alerts."""
        self.client.login(email='t1.an@example.com', password='Password@123')
        res = self.client.get(reverse('portal:teacher_analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Class Intelligence & Topic Diagnostics')

        res_ew = self.client.get(reverse('portal:teacher_early_warnings'))
        self.assertEqual(res_ew.status_code, 200)
        self.assertContains(res_ew, 'Early Warning Alert Center')

    def test_unassigned_teacher_cannot_access_other_teacher_section(self):
        """Teacher 2 receives 404 when directly requesting Teacher 1's section analytics."""
        self.client.login(email='t2.an@example.com', password='Password@123')
        res = self.client.get(reverse('portal:teacher_class_analytics', kwargs={'section_id': self.section.pk}))
        self.assertEqual(res.status_code, 404)

    def test_admin_can_view_institutional_analytics(self):
        """Administrator can access institutional intelligence dashboard."""
        self.client.login(email='admin.an@example.com', password='Password@123')
        res = self.client.get(reverse('portal_admin:analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'University Academic Intelligence & Risk Distribution')
