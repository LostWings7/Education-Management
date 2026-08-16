"""
Unit tests for Custom Administrator Portal Academic CRUD & Management Workflows.
"""

from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User, Role, AuditLog
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    Topic,
    ClassSection,
    Enrollment,
    ClassSchedule
)


class AdminCRUDTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Admin user
        self.admin_user = User.objects.create_superuser(email='admin.crud@example.com', password='Password@123', role=Role.ADMINISTRATOR)
        self.client.login(email='admin.crud@example.com', password='Password@123')

        # Baseline Dept & Program
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Teacher
        t_u = User.objects.create_user(email='t.crud@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-CRUD', department=self.dept)

    def test_admin_create_department(self):
        """Administrator can create a new academic department."""
        response = self.client.post(reverse('portal_admin:department_create'), {
            'code': 'ECE',
            'name': 'Electronics Engineering',
            'description': 'Hardware and circuits',
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.filter(code='ECE').exists())

    def test_admin_toggle_department_status(self):
        """Administrator can archive/deactivate a department."""
        dept = Department.objects.create(code='BIO', name='Biotechnology', is_active=True)
        response = self.client.post(reverse('portal_admin:department_toggle_status', kwargs={'pk': dept.pk}))
        self.assertEqual(response.status_code, 302)
        dept.refresh_from_db()
        self.assertFalse(dept.is_active)

    def test_admin_create_program(self):
        """Administrator can create a new degree program."""
        response = self.client.post(reverse('portal_admin:program_create'), {
            'department': self.dept.pk,
            'code': 'MT-CSE',
            'name': 'M.Tech CSE',
            'degree_level': Program.DegreeLevel.MASTER,
            'duration_years': 2,
            'total_semesters': 4,
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Program.objects.filter(code='MT-CSE').exists())

    def test_admin_create_student_validates_department_and_program(self):
        """Admin student creation validates that program belongs to selected department."""
        other_dept = Department.objects.create(code='MATH', name='Mathematics')
        other_prog = Program.objects.create(department=other_dept, code='BS-MATH', name='B.Sc Mathematics')

        # Invalid post: CSE dept with MATH program
        response = self.client.post(reverse('portal_admin:student_create'), {
            'email': 'badstudent@example.com',
            'first_name': 'Bad',
            'last_name': 'Student',
            'password': 'Password@123',
            'student_id': 'BAD-001',
            'department': self.dept.pk,
            'program': other_prog.pk,
            'current_semester': 1,
            'academic_year': 2026,
            'academic_status': StudentProfile.AcademicStatus.ACTIVE
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='badstudent@example.com').exists())

        # Valid post: CSE dept with CSE program
        response_valid = self.client.post(reverse('portal_admin:student_create'), {
            'email': 'goodstudent@example.com',
            'first_name': 'Good',
            'last_name': 'Student',
            'password': 'Password@123',
            'student_id': 'GOOD-001',
            'department': self.dept.pk,
            'program': self.prog.pk,
            'current_semester': 1,
            'academic_year': 2026,
            'academic_status': StudentProfile.AcademicStatus.ACTIVE
        })
        self.assertEqual(response_valid.status_code, 302)
        self.assertTrue(StudentProfile.objects.filter(student_id='GOOD-001').exists())

    def test_admin_create_course_with_m2m_programs_and_topic(self):
        """Administrator can create a course with M2M program offerings and syllabus topics."""
        prog2 = Program.objects.create(department=self.dept, code='BT-AI', name='B.Tech AI')
        response = self.client.post(reverse('portal_admin:course_create'), {
            'department': self.dept.pk,
            'programs': [self.prog.pk, prog2.pk],
            'code': 'CS305',
            'title': 'Operating Systems',
            'credits': 4,
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(code='CS305')
        self.assertEqual(course.programs.count(), 2)

        # Add topic
        res_topic = self.client.post(reverse('portal_admin:topic_create', kwargs={'course_id': course.pk}), {
            'order_index': 1,
            'title': 'Process Scheduling',
            'description': 'CPU scheduling algorithms'
        })
        self.assertEqual(res_topic.status_code, 302)
        self.assertEqual(course.topics.count(), 1)

    def test_admin_enrollment_workflow(self):
        """Admin can enroll student, view roster, and drop enrollment safely."""
        s_u = User.objects.create_user(email='s.enr@example.com', password='Password@123', role=Role.STUDENT)
        student = StudentProfile.objects.create(user=s_u, student_id='S-ENR', department=self.dept, program=self.prog)

        course = Course.objects.create(department=self.dept, code='CS202', title='Algorithms', credits=4)
        course.programs.add(self.prog)
        sec = ClassSection.objects.create(course=course, semester=self.sem, section_code='A', primary_teacher=self.teacher, capacity=30)

        # Enroll
        res_enr = self.client.post(reverse('portal_admin:enrollment_create'), {
            'student': student.pk,
            'class_section': sec.pk
        })
        self.assertEqual(res_enr.status_code, 302)
        self.assertEqual(Enrollment.objects.filter(student=student, class_section=sec, status=Enrollment.EnrollmentStatus.ENROLLED).count(), 1)

        # View Roster
        res_roster = self.client.get(reverse('portal_admin:section_roster', kwargs={'pk': sec.pk}))
        self.assertEqual(res_roster.status_code, 200)
        self.assertContains(res_roster, 'S-ENR')

        # Drop student
        enr = Enrollment.objects.get(student=student, class_section=sec)
        res_drop = self.client.post(reverse('portal_admin:enrollment_drop', kwargs={'pk': enr.pk}))
        self.assertEqual(res_drop.status_code, 302)
        enr.refresh_from_db()
        self.assertEqual(enr.status, Enrollment.EnrollmentStatus.DROPPED)
