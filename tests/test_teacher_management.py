"""
Unit tests for Teacher Portal Management workflows (Assignments, Assessments, Scores, Resources, Announcements).
"""

from decimal import Decimal
from datetime import date, timedelta
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
    Assignment,
    Assessment,
    AssessmentResult,
    LearningResource,
    CourseAnnouncement
)
from apps.academic.services import EnrollmentService


class TeacherManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Faculty 1 (Assigned)
        t1_u = User.objects.create_user(email='t1.mgmt@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=t1_u, employee_id='T1-M', department=self.dept)

        # Faculty 2 (Unassigned)
        t2_u = User.objects.create_user(email='t2.mgmt@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=t2_u, employee_id='T2-M', department=self.dept)

        # Student
        s_u = User.objects.create_user(email='s1.mgmt@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S1-M', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher1)
        EnrollmentService.enroll_student(self.student, self.section)

    def test_teacher_assignment_lifecycle(self):
        """Teacher can create, edit, and delete assignment for assigned section."""
        self.client.login(email='t1.mgmt@example.com', password='Password@123')

        # Create Assignment
        res_create = self.client.post(reverse('portal:teacher_assignment_create'), {
            'class_section': self.section.pk,
            'title': 'Problem Set 1',
            'description': 'Solve graph traversal questions',
            'issue_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'due_date': (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),
            'max_marks': '50.00',
            'is_published': True
        })
        self.assertEqual(res_create.status_code, 302)
        assign = Assignment.objects.get(title='Problem Set 1')
        self.assertEqual(assign.class_section, self.section)

        # Edit Assignment
        res_edit = self.client.post(reverse('portal:teacher_assignment_edit', kwargs={'pk': assign.pk}), {
            'class_section': self.section.pk,
            'title': 'Problem Set 1 (Updated)',
            'description': 'Updated questions',
            'issue_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'due_date': (timezone.now() + timedelta(days=8)).strftime('%Y-%m-%dT%H:%M'),
            'max_marks': '60.00',
            'is_published': True
        })
        self.assertEqual(res_edit.status_code, 302)
        assign.refresh_from_db()
        self.assertEqual(assign.title, 'Problem Set 1 (Updated)')

        # Delete Assignment
        res_del = self.client.post(reverse('portal:teacher_assignment_delete', kwargs={'pk': assign.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Assignment.objects.filter(pk=assign.pk).exists())

    def test_teacher_assessment_and_enter_marks(self):
        """Teacher can create assessment and enter marks for students."""
        self.client.login(email='t1.mgmt@example.com', password='Password@123')

        # Create Assessment
        res_create = self.client.post(reverse('portal:teacher_assessment_create'), {
            'class_section': self.section.pk,
            'title': 'Midterm Examination',
            'assessment_type': Assessment.AssessmentType.MIDTERM,
            'date': '2026-03-15',
            'max_marks': '100.00',
            'weightage_percentage': '30.00',
            'is_published': True
        })
        self.assertEqual(res_create.status_code, 302)
        assessment = Assessment.objects.get(title='Midterm Examination')

        # Enter Marks
        res_marks = self.client.post(reverse('portal:teacher_assessment_enter_marks', kwargs={'pk': assessment.pk}), {
            f'marks_{self.student.pk}': '88.5'
        })
        self.assertEqual(res_marks.status_code, 302)

        result = AssessmentResult.objects.get(assessment=assessment, student=self.student)
        self.assertEqual(result.marks_obtained, Decimal('88.5'))

    def test_teacher_resource_and_announcement(self):
        """Teacher can upload course learning resources and post section announcements."""
        self.client.login(email='t1.mgmt@example.com', password='Password@123')

        # Upload Resource
        res_r = self.client.post(reverse('portal:teacher_resource_create'), {
            'course': self.course.pk,
            'title': 'Lecture 1 Slides',
            'resource_type': LearningResource.ResourceType.PRESENTATION,
            'external_url': 'https://example.com/slides.pdf',
            'is_published': True
        })
        self.assertEqual(res_r.status_code, 302)
        self.assertTrue(LearningResource.objects.filter(title='Lecture 1 Slides').exists())

        # Post Announcement
        res_a = self.client.post(reverse('portal:teacher_announcement_create'), {
            'class_section': self.section.pk,
            'title': 'Quiz 1 Schedule Announcement',
            'content': 'Quiz 1 will take place this Thursday at 10 AM.',
            'is_pinned': True
        })
        self.assertEqual(res_a.status_code, 302)
        self.assertTrue(CourseAnnouncement.objects.filter(title='Quiz 1 Schedule Announcement').exists())

    def test_unassigned_teacher_cannot_manage_another_teachers_section(self):
        """Teacher 2 cannot edit or delete Teacher 1's assignment."""
        self.client.login(email='t1.mgmt@example.com', password='Password@123')
        assign = Assignment.objects.create(
            class_section=self.section,
            teacher=self.teacher1,
            title='Teacher 1 Assignment',
            description='Test',
            issue_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=5),
            max_marks=Decimal('50.00'),
            is_published=True
        )

        # Login as teacher 2
        self.client.login(email='t2.mgmt@example.com', password='Password@123')
        res = self.client.get(reverse('portal:teacher_assignment_edit', kwargs={'pk': assign.pk}))
        self.assertEqual(res.status_code, 404)
