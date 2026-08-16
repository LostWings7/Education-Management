"""
Unit and integration tests for Role-Based Access Control (RBAC),
view decorators/mixins, and portal dispatcher routing.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User, Role


class RBACAndRoutingTests(TestCase):
    """
    Tests ensuring access controls across Student, Teacher, and Admin portals.
    """

    def setUp(self):
        self.client = Client()
        self.password = 'SharedPassword123!'

        self.student = User.objects.create_user(
            email='student.rbac@example.com',
            password=self.password,
            role=Role.STUDENT
        )

        self.teacher = User.objects.create_user(
            email='teacher.rbac@example.com',
            password=self.password,
            role=Role.TEACHER
        )

        self.admin_user = User.objects.create_superuser(
            email='admin.rbac@example.com',
            password=self.password,
            role=Role.ADMINISTRATOR
        )

    def test_unauthenticated_access_redirects_to_login(self):
        routes = [
            reverse('portal:dispatcher'),
            reverse('portal:student_dashboard'),
            reverse('portal:teacher_dashboard'),
            reverse('portal_admin:dashboard'),
            reverse('core:profile'),
        ]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302, f"Failed for route: {route}")
            self.assertIn('/accounts/login/', response.url)

    def test_student_can_access_student_dashboard(self):
        self.client.login(email=self.student.email, password=self.password)
        response = self.client.get(reverse('portal:student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student Portal')

    def test_student_blocked_from_teacher_and_admin_portals(self):
        self.client.login(email=self.student.email, password=self.password)

        # Accessing teacher dashboard must be forbidden
        response_teacher = self.client.get(reverse('portal:teacher_dashboard'))
        self.assertEqual(response_teacher.status_code, 403)

        # Accessing admin dashboard must be forbidden
        response_admin = self.client.get(reverse('portal_admin:dashboard'))
        self.assertEqual(response_admin.status_code, 403)

    def test_teacher_can_access_teacher_dashboard(self):
        self.client.login(email=self.teacher.email, password=self.password)
        response = self.client.get(reverse('portal:teacher_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Faculty Portal')

    def test_teacher_blocked_from_admin_portal(self):
        self.client.login(email=self.teacher.email, password=self.password)
        response = self.client.get(reverse('portal_admin:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_dashboard(self):
        self.client.login(email=self.admin_user.email, password=self.password)
        response = self.client.get(reverse('portal_admin:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Institution Administration Dashboard')

    def test_portal_dispatcher_routing_by_role(self):
        # 1. Student dispatch
        self.client.login(email=self.student.email, password=self.password)
        res_stu = self.client.get(reverse('portal:dispatcher'))
        self.assertRedirects(res_stu, reverse('portal:student_dashboard'))

        # 2. Teacher dispatch
        self.client.login(email=self.teacher.email, password=self.password)
        res_tea = self.client.get(reverse('portal:dispatcher'))
        self.assertRedirects(res_tea, reverse('portal:teacher_dashboard'))

        # 3. Admin dispatch
        self.client.login(email=self.admin_user.email, password=self.password)
        res_adm = self.client.get(reverse('portal:dispatcher'))
        self.assertRedirects(res_adm, reverse('portal_admin:dashboard'))
