"""
Unit tests for custom User model and UserManager.
"""

from django.test import TestCase
from django.db import IntegrityError
from apps.core.models import User, Role


class UserModelTests(TestCase):
    """
    Tests ensuring User model uses email as unique identifier
    and manages roles accurately.
    """

    def test_create_student_user_with_email_successful(self):
        user = User.objects.create_user(
            email='teststudent@example.com',
            password='SecretPassword123!',
            first_name='John',
            last_name='Doe',
            role=Role.STUDENT
        )
        self.assertEqual(user.email, 'teststudent@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.role, Role.STUDENT)
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_administrator)
        self.assertTrue(user.check_password('SecretPassword123!'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_email_normalized(self):
        email = 'TestUser@Example.COM'
        user = User.objects.create_user(email=email, password='SecretPassword123!')
        self.assertEqual(user.email, 'testuser@example.com')

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='SecretPassword123!')

    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(email='duplicate@example.com', password='Password123!')
        with self.assertRaises(IntegrityError):
            User.objects.create(email='duplicate@example.com', role=Role.STUDENT)

    def test_create_superuser_successful(self):
        admin = User.objects.create_superuser(
            email='superadmin@example.com',
            password='AdminPassword123!',
            first_name='Super',
            last_name='Admin'
        )
        self.assertEqual(admin.email, 'superadmin@example.com')
        self.assertEqual(admin.role, Role.ADMINISTRATOR)
        self.assertTrue(admin.is_administrator)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
