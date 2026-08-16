"""
Phase 7 Automated Tests: Student Academic Command Center, Action Priority Normalization & Longitudinal Projections.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
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
    Topic,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult
)
from apps.analytics.services import (
    StudentActionPriorityService,
    LongitudinalJourneyService,
    AcademicMomentsService
)


class Phase7StudentCommandCenterTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Computer Science", code="CS")
        self.prog = Program.objects.create(name="B.Sc. CS", code="BSCS", department=self.dept)

        self.student_user = User.objects.create_user(
            email="student@example.com",
            password="Password123!",
            role=Role.STUDENT,
            first_name="Ada",
            last_name="Lovelace"
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-001",
            department=self.dept,
            program=self.prog,
            current_semester=3
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            password="Password123!",
            role=Role.TEACHER,
            first_name="Alan",
            last_name="Turing"
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, employee_id="FAC-001", department=self.dept)

        self.ay = AcademicYear.objects.create(name="2025-2026", start_date=date(2025, 9, 1), end_date=date(2026, 6, 30))

        # Completed Semester 1
        self.sem1 = Semester.objects.create(
            academic_year=self.ay,
            semester_number=1,
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 31),
            is_active=False,
            is_completed=True
        )

        # Active Semester 2
        self.sem2 = Semester.objects.create(
            academic_year=self.ay,
            semester_number=2,
            name="Spring 2026",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 6, 30),
            is_active=True,
            is_completed=False
        )

        self.course = Course.objects.create(department=self.dept, code="CS101", title="Intro to CS", credits=Decimal('4.0'))
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem2, section_code="A", primary_teacher=self.teacher)
        self.enr = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_student_action_priority_normalization_and_formula(self):
        """
        Verify that StudentActionPriorityService strictly normalizes sub-scores to 0-100 and applies:
        Score = 0.45 * Urgency + 0.35 * Risk + 0.20 * Impact.
        """
        # Create an assignment due tomorrow (high urgency)
        now = timezone.now()
        assign = Assignment.objects.create(
            class_section=self.section,
            teacher=self.teacher,
            title="Problem Set 1",
            max_marks=Decimal('100.0'),
            due_date=now + timedelta(hours=20)
        )

        actions = StudentActionPriorityService.get_prioritized_actions(self.student, semester=self.sem2)
        self.assertTrue(len(actions) > 0)
        top_action = actions[0]

        self.assertEqual(top_action['category'], 'ASSIGNMENT')
        self.assertGreaterEqual(top_action['priority_score'], 0.0)
        self.assertLessEqual(top_action['priority_score'], 100.0)
        self.assertIn(top_action['priority_level'], ['URGENT', 'HIGH', 'RECOMMENDED', 'NORMAL'])

        # Verify formula precision
        expected_score = round(
            0.45 * top_action['urgency_score'] +
            0.35 * top_action['risk_subscore'] +
            0.20 * top_action['impact_subscore'],
            1
        )
        self.assertEqual(top_action['priority_score'], expected_score)

    def test_longitudinal_projection_minimum_observation_guard(self):
        """
        Verify that longitudinal projection requires >= 3 completed terms, otherwise returning INSUFFICIENT_DATA.
        """
        # Only 1 completed semester exists in setUp
        journey = LongitudinalJourneyService.get_student_journey(self.student)
        self.assertEqual(journey['where_you_are_headed']['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(journey['where_you_are_headed']['projected_next_gpa'])

        # Add 2 more completed semesters with grades
        sem3 = Semester.objects.create(academic_year=self.ay, semester_number=3, name="Summer 2026", start_date=date(2026, 7, 1), end_date=date(2026, 8, 31), is_completed=True)
        sem4 = Semester.objects.create(academic_year=self.ay, semester_number=4, name="Fall 2026", start_date=date(2026, 9, 1), end_date=date(2026, 12, 31), is_completed=True)

        sec3 = ClassSection.objects.create(course=self.course, semester=self.sem1, section_code="A", primary_teacher=self.teacher)
        sec4 = ClassSection.objects.create(course=self.course, semester=sem3, section_code="A", primary_teacher=self.teacher)
        sec5 = ClassSection.objects.create(course=self.course, semester=sem4, section_code="A", primary_teacher=self.teacher)

        Enrollment.objects.create(student=self.student, class_section=sec3, final_grade_letter='A', final_percentage=Decimal('92.0'), is_grade_published=True)
        Enrollment.objects.create(student=self.student, class_section=sec4, final_grade_letter='A', final_percentage=Decimal('94.0'), is_grade_published=True)
        Enrollment.objects.create(student=self.student, class_section=sec5, final_grade_letter='A', final_percentage=Decimal('96.0'), is_grade_published=True)

        journey_projected = LongitudinalJourneyService.get_student_journey(self.student)
        self.assertEqual(journey_projected['where_you_are_headed']['status'], 'VALID')
        self.assertIsNotNone(journey_projected['where_you_are_headed']['projected_next_gpa'])
        self.assertIn('[PROJECTION]', journey_projected['where_you_are_headed']['disclaimer'])

    def test_academic_milestones_neutral_naming_and_thresholds(self):
        """
        Verify that milestones use neutral names (e.g. DISTINCTION_ACHIEVED) and respect centralized thresholds.
        """
        # Publish high GPA
        self.enr.final_grade_letter = 'A'
        self.enr.final_percentage = Decimal('95.0')
        self.enr.is_grade_published = True
        self.enr.save()

        moments = AcademicMomentsService.get_student_moments(self.student, semester=self.sem2)
        moment_types = [m['moment_type'] for m in moments]
        self.assertIn('DISTINCTION_ACHIEVED', moment_types)
