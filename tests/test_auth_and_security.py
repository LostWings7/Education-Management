"""
Unit and integration tests for Authentication, Student Registration security,
and Profile management.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User, Role


class AuthAndSecurityTests(TestCase):
    """
    Tests ensuring authentication flows and role assignment restrictions.
    """

    def setUp(self):
        self.client = Client()
        self.student_email = 'student.auth@example.com'
        self.student_password = 'Password123!'
        self.student = User.objects.create_user(
            email=self.student_email,
            password=self.student_password,
            first_name='Alice',
            last_name='Smith',
            role=Role.STUDENT
        )

    def test_login_successful_with_email(self):
        response = self.client.post(reverse('core:login'), {
            'email': self.student_email,
            'password': self.student_password,
        })
        # Should redirect to portal dispatcher
        self.assertRedirects(response, reverse('portal:dispatcher'), target_status_code=302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.student.pk)

    def test_login_fails_with_incorrect_password(self):
        response = self.client.post(reverse('core:login'), {
            'email': self.student_email,
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email address or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_public_registration_creates_student_role_only(self):
        reg_data = {
            'email': 'newstudent@example.com',
            'first_name': 'Bob',
            'last_name': 'Taylor',
            'phone_number': '+1-555-9999',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        }
        response = self.client.post(reverse('core:register'), reg_data)
        self.assertRedirects(response, reverse('portal:dispatcher'), target_status_code=302)

        # Verify user was created with STUDENT role
        new_user = User.objects.get(email='newstudent@example.com')
        self.assertEqual(new_user.role, Role.STUDENT)
        self.assertTrue(new_user.is_student)
        self.assertFalse(new_user.is_teacher)
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

    def test_registration_ignores_forged_role_parameter(self):
        """
        Ensure sending role=ADMINISTRATOR in post data does NOT grant administrator role.
        """
        reg_data = {
            'email': 'attacker@example.com',
            'first_name': 'Attacker',
            'last_name': 'User',
            'phone_number': '+1-555-0000',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'role': Role.ADMINISTRATOR,  # Attempted privilege escalation!
            'is_staff': True,
            'is_superuser': True,
        }
        response = self.client.post(reverse('core:register'), reg_data)
        self.assertRedirects(response, reverse('portal:dispatcher'), target_status_code=302)

        user = User.objects.get(email='attacker@example.com')
        # Role must still be STUDENT!
        self.assertEqual(user.role, Role.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_logout_view(self):
        self.client.login(email=self.student_email, password=self.student_password)
        response = self.client.post(reverse('core:logout'))
        self.assertRedirects(response, reverse('core:login'))
        self.assertNotIn('_auth_user_id', self.client.session)
