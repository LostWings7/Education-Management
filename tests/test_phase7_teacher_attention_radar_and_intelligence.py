"""
Phase 7 Automated Tests: Teacher Attention Radar, Curricular Topic Friction & Assessment Intelligence.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
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
    Topic,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assessment,
    AssessmentResult
)


class Phase7TeacherAttentionRadarAndIntelligenceTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Mathematics", code="MATH")
        self.prog = Program.objects.create(name="B.Sc. Math", code="BSM", department=self.dept)

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            password="Password123!",
            role=Role.TEACHER,
            first_name="Alan",
            last_name="Turing"
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, employee_id="FAC-001", department=self.dept)

        self.student_user = User.objects.create_user(
            email="katherine@example.com",
            password="Password123!",
            role=Role.STUDENT,
            first_name="Katherine",
            last_name="Johnson"
        )
        self.student = StudentProfile.objects.create(user=self.student_user, student_id="STU-007", department=self.dept, program=self.prog)

        self.ay = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        self.sem = Semester.objects.create(academic_year=self.ay, semester_number=1, name="Fall 2026", start_date=date(2026, 9, 1), end_date=date(2026, 12, 31), is_active=True)

        self.course = Course.objects.create(department=self.dept, code="MATH301", title="Differential Equations", credits=Decimal('4.0'))
        self.topic = Topic.objects.create(course=self.course, order_index=1, title="Laplace Transforms")
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code="A", primary_teacher=self.teacher)
        self.enr = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_teacher_attention_radar_dashboard_tiering(self):
        """
        Verify that TeacherDashboardView properly assigns students into Attention Radar tiers.
        """
        # Create 10 attendance sessions (student attends 4 = 40% -> Critical)
        for i in range(10):
            sess = ClassSession.objects.create(class_section=self.section, session_date=date(2026, 9, 1) + timedelta(days=i), title=f"Lecture {i+1}", teacher=self.teacher)
            AttendanceRecord.objects.create(session=sess, student=self.student, status='PRESENT' if i < 4 else 'ABSENT')

        self.client.login(email="teacher@example.com", password="Password123!")
        url = reverse('portal:teacher_dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('attention_radar', response.context)
        radar = response.context['attention_radar']
        self.assertEqual(radar['total_monitored'], 1)
        self.assertTrue(len(radar['critical']) > 0)
        self.assertEqual(radar['critical'][0]['student_id'], 'STU-007')

    def test_teacher_course_intelligence_view(self):
        """
        Verify TeacherCourseIntelligenceView computes topic friction levels.
        """
        self.client.login(email="teacher@example.com", password="Password123!")
        url = reverse('portal:teacher_course_intelligence', kwargs={'section_id': self.section.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('topic_analysis', response.context)
        self.assertEqual(len(response.context['topic_analysis']), 1)

    def test_teacher_assessment_intelligence_view(self):
        """
        Verify TeacherAssessmentIntelligenceView computes statistical summaries.
        """
        assess = Assessment.objects.create(class_section=self.section, title="Midterm", max_marks=Decimal('100.0'), weightage_percentage=Decimal('30.0'))
        AssessmentResult.objects.create(assessment=assess, student=self.student, marks_obtained=Decimal('85.0'))

        self.client.login(email="teacher@example.com", password="Password123!")
        url = reverse('portal:teacher_assessment_intelligence', kwargs={'assessment_id': assess.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        self.assertEqual(response.context['stats']['mean'], 85.0)
        self.assertEqual(response.context['stats']['count'], 1)
