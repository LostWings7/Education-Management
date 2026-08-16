"""
Unit tests for Course-Program Many-to-Many hierarchy, Topics, and Academic Periods.
"""

from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.academic.models import (
    Department,
    Program,
    Course,
    Topic,
    AcademicYear,
    Semester
)


class AcademicHierarchyModelTest(TestCase):
    def setUp(self):
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science')
        self.dept_ai = Department.objects.create(code='AI', name='Artificial Intelligence')

        self.prog_cse = Program.objects.create(
            department=self.dept_cse,
            code='BT-CSE',
            name='B.Tech CSE'
        )
        self.prog_ai = Program.objects.create(
            department=self.dept_ai,
            code='BT-AI',
            name='B.Tech AI'
        )
        self.prog_csbs = Program.objects.create(
            department=self.dept_cse,
            code='BT-CSBS',
            name='B.Tech CSBS'
        )

        self.ay = AcademicYear.objects.create(
            name='2025-2026',
            start_date=date(2025, 8, 1),
            end_date=date(2026, 5, 31),
            is_current=True
        )

    def test_course_many_to_many_program_relationship(self):
        """Verify a Course can be included in multiple degree programs across departments."""
        course = Course.objects.create(
            department=self.dept_cse,
            code='CS301',
            title='Data Structures & Algorithms',
            credits=4
        )
        course.programs.add(self.prog_cse, self.prog_ai, self.prog_csbs)

        self.assertEqual(course.programs.count(), 3)
        self.assertTrue(course.is_eligible_for_program(self.prog_cse))
        self.assertTrue(course.is_eligible_for_program(self.prog_ai))
        self.assertTrue(course.is_eligible_for_program(self.prog_csbs))

        # Check reverse query
        self.assertIn(course, self.prog_cse.courses.all())
        self.assertIn(course, self.prog_ai.courses.all())

    def test_course_eligibility_check(self):
        """Test eligibility check returns False for non-associated programs."""
        course = Course.objects.create(
            department=self.dept_ai,
            code='AI401',
            title='Deep Learning',
            credits=4
        )
        course.programs.add(self.prog_ai)

        self.assertTrue(course.is_eligible_for_program(self.prog_ai))
        self.assertFalse(course.is_eligible_for_program(self.prog_cse))
        self.assertFalse(course.is_eligible_for_program(None))

    def test_topic_ordering_and_unique_constraint(self):
        """Verify topics can be created and maintain unique order sequence per course."""
        course = Course.objects.create(
            department=self.dept_cse,
            code='CS201',
            title='Data Structures',
            credits=4
        )

        t1 = Topic.objects.create(course=course, order_index=1, title='Arrays')
        t2 = Topic.objects.create(course=course, order_index=2, title='Trees')

        self.assertEqual(course.topics.count(), 2)
        self.assertEqual(list(course.topics.all()), [t1, t2])

        # Attempting duplicate order_index should raise error
        with self.assertRaises(Exception):
            Topic.objects.create(course=course, order_index=1, title='Duplicate Order Topic')

    def test_academic_year_date_validation(self):
        """Academic year must enforce start_date < end_date."""
        with self.assertRaises(ValidationError):
            ay_invalid = AcademicYear(
                name='2027-2028',
                start_date=date(2028, 5, 1),
                end_date=date(2027, 5, 1)
            )
            ay_invalid.clean()

    def test_semester_active_and_completed_flags(self):
        """Verify semester active/completed separation."""
        sem_fall = Semester.objects.create(
            academic_year=self.ay,
            name='Fall 2025',
            term_type=Semester.TermType.FALL,
            semester_number=1,
            start_date=date(2025, 8, 1),
            end_date=date(2025, 12, 15),
            is_active=False,
            is_completed=True
        )

        sem_spring = Semester.objects.create(
            academic_year=self.ay,
            name='Spring 2026',
            term_type=Semester.TermType.SPRING,
            semester_number=2,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 5, 30),
            is_active=True,
            is_completed=False
        )

        self.assertTrue(sem_fall.is_completed)
        self.assertFalse(sem_fall.is_active)
        self.assertTrue(sem_spring.is_active)
        self.assertFalse(sem_spring.is_completed)
