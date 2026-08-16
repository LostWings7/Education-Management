"""
End-to-end integration and HTTP status verification tests across
public pages, login views, and role-based portal endpoints.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User, Role
from apps.academic.models import Department, Program, StudentProfile, TeacherProfile


class E2EFlowTests(TestCase):
    """
    Verifies full HTTP rendering cycle and context rendering across all routes.
    """

    def setUp(self):
        self.client = Client()
        self.password = 'TestPass@12345'

        # Seed minimal data
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(
            department=self.dept,
            code='BT-CS',
            name='B.Tech CS',
            degree_level=Program.DegreeLevel.BACHELOR
        )

        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password=self.password
        )

        self.teacher_user = User.objects.create_user(
            email='teacher@test.com',
            password=self.password,
            role=Role.TEACHER
        )
        TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id='FAC-99',
            department=self.dept
        )

        self.student_user = User.objects.create_user(
            email='student@test.com',
            password=self.password,
            role=Role.STUDENT
        )
        StudentProfile.objects.create(
            user=self.student_user,
            student_id='STU-99',
            department=self.dept,
            program=self.prog
        )

    def test_public_pages_render_successfully(self):
        # 1. Home
        res_home = self.client.get(reverse('public:home'))
        self.assertEqual(res_home.status_code, 200)
        self.assertContains(res_home, 'Unified Education Management')

        # 2. Courses Catalog
        res_courses = self.client.get(reverse('public:courses'))
        self.assertEqual(res_courses.status_code, 200)
        self.assertContains(res_courses, 'B.Tech CS')

        # 3. Course Detail
        res_detail = self.client.get(reverse('public:course_detail', kwargs={'code': 'BT-CS'}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'B.Tech CS')

        # 4. Contact
        res_contact = self.client.get(reverse('public:contact'))
        self.assertEqual(res_contact.status_code, 200)
        self.assertContains(res_contact, 'Academic Help')

    def test_auth_pages_render_successfully(self):
        # Login page
        res_login = self.client.get(reverse('core:login'))
        self.assertEqual(res_login.status_code, 200)
        self.assertContains(res_login, 'Sign in to your account')

        # Register page
        res_reg = self.client.get(reverse('core:register'))
        self.assertEqual(res_reg.status_code, 200)
        self.assertContains(res_reg, 'Create Student Account')

    def test_authenticated_portals_render_successfully(self):
        # Admin Portal
        self.client.login(email='admin@test.com', password=self.password)
        res_adm = self.client.get(reverse('portal_admin:dashboard'))
        self.assertEqual(res_adm.status_code, 200)
        self.assertContains(res_adm, 'Institution Administration Dashboard')
        self.client.logout()

        # Teacher Portal
        self.client.login(email='teacher@test.com', password=self.password)
        res_tea = self.client.get(reverse('portal:teacher_dashboard'))
        self.assertEqual(res_tea.status_code, 200)
        self.assertContains(res_tea, 'Faculty Portal')
        self.client.logout()

        # Student Portal
        self.client.login(email='student@test.com', password=self.password)
        res_stu = self.client.get(reverse('portal:student_dashboard'))
        self.assertEqual(res_stu.status_code, 200)
        self.assertContains(res_stu, 'Student Portal')
        self.client.logout()
