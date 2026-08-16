"""
Unit tests for Intervention Permissions, Data Isolation, and Calendar Overdue Logic.
"""

from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
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
from apps.interventions.models import Intervention
from apps.interventions.services import InterventionMonitoringService


class InterventionPermissionsAndScopingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Teacher 1 (Section Instructor)
        t1_u = User.objects.create_user(email='t1.p@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T1-P', department=self.dept)

        # Teacher 2 (Unassigned)
        t2_u = User.objects.create_user(email='t2.p@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T2-P', department=self.dept)

        # Student 1
        s1_u = User.objects.create_user(email='s1.p@example.com', password='Password@123', role=Role.STUDENT)
        self.student1 = StudentProfile.objects.create(user=s1_u, student_id='S1-P', department=self.dept, program=self.prog)

        # Student 2
        s2_u = User.objects.create_user(email='s2.p@example.com', password='Password@123', role=Role.STUDENT)
        self.student2 = StudentProfile.objects.create(user=s2_u, student_id='S2-P', department=self.dept, program=self.prog)

        # Admin
        self.admin = User.objects.create_superuser(email='admin.p@example.com', password='Password@123', role=Role.ADMINISTRATOR)

        # Course & Section
        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)
        Enrollment.objects.create(student=self.student1, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        # Student 1 Plan
        self.plan1 = Intervention.objects.create(
            student=self.student1,
            course=self.course,
            class_section=self.section,
            assigned_to=self.teacher1,
            created_by=t1_u,
            title="Plan 1",
            status=Intervention.Status.ASSIGNED,
            due_date=timezone.now().date() + timezone.timedelta(days=14)
        )

    def test_student_cannot_access_other_student_plan(self):
        """Student 2 receives 404 when attempting to access Student 1's plan."""
        self.client.login(email='s2.p@example.com', password='Password@123')
        res = self.client.get(reverse('portal:student_intervention_detail', kwargs={'pk': self.plan1.pk}))
        self.assertEqual(res.status_code, 404)

    def test_teacher_cannot_access_unassigned_teacher_plan(self):
        """Teacher 2 receives 404 when attempting to access Teacher 1's section plan."""
        self.client.login(email='t2.p@example.com', password='Password@123')
        res = self.client.get(reverse('portal:teacher_intervention_detail', kwargs={'pk': self.plan1.pk}))
        self.assertEqual(res.status_code, 404)

    def test_admin_can_access_all_interventions(self):
        """Admin can access institutional overview and specific intervention detail."""
        self.client.login(email='admin.p@example.com', password='Password@123')
        res_ov = self.client.get(reverse('portal_admin:interventions_overview'))
        self.assertEqual(res_ov.status_code, 200)

        res_det = self.client.get(reverse('portal_admin:intervention_detail', kwargs={'pk': self.plan1.pk}))
        self.assertEqual(res_det.status_code, 200)

    def test_calendar_overdue_and_14_day_severely_overdue(self):
        """
        Verify calendar overdue detection:
        - due_date = today - 1 day -> overdue (True), overdue_14_days (False).
        - due_date = today - 15 days -> overdue (True), overdue_14_days (True).
        """
        today = timezone.now().date()
        self.plan1.due_date = today - timezone.timedelta(days=1)
        self.plan1.save()
        self.assertTrue(self.plan1.is_overdue)
        self.assertFalse(self.plan1.is_overdue_14_days)

        self.plan1.due_date = today - timezone.timedelta(days=15)
        self.plan1.save()
        self.assertTrue(self.plan1.is_overdue)
        self.assertTrue(self.plan1.is_overdue_14_days)

        severely_overdue_qs = InterventionMonitoringService.get_severely_overdue_interventions()
        self.assertIn(self.plan1, severely_overdue_qs)
