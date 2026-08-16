"""
Unit tests for 7-day timetable and ScheduleService conflict detection.
"""

from datetime import date, time
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    TeacherProfile,
    Course,
    ClassSection,
    ClassSchedule,
    AcademicYear,
    Semester
)
from apps.academic.services import ScheduleService


class ScheduleConflictTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        # Faculty
        u1 = User.objects.create_user(email='turing@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher1 = TeacherProfile.objects.create(user=u1, employee_id='T-101', department=self.dept)

        u2 = User.objects.create_user(email='hopper@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher2 = TeacherProfile.objects.create(user=u2, employee_id='T-102', department=self.dept)

        # Courses & Sections
        self.c1 = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.c1.programs.add(self.prog)
        self.sec1 = ClassSection.objects.create(course=self.c1, semester=self.sem, section_code='A', primary_teacher=self.teacher1)

        self.c2 = Course.objects.create(department=self.dept, code='CS301', title='Databases', credits=4)
        self.c2.programs.add(self.prog)
        self.sec2 = ClassSection.objects.create(course=self.c2, semester=self.sem, section_code='A', primary_teacher=self.teacher2)

    def test_sunday_timetable_support(self):
        """Verify timetable supports Sunday (day 7) without error."""
        entry = ScheduleService.create_schedule_entry(
            class_section=self.sec1,
            teacher=self.teacher1,
            day_of_week=7,  # Sunday
            start_time=time(10, 0),
            end_time=time(11, 30),
            room='Lab 301'
        )
        self.assertEqual(entry.day_of_week, 7)
        self.assertEqual(entry.get_day_of_week_display(), 'Sunday')

    def test_teacher_double_booking_conflict(self):
        """Instructor cannot be scheduled in two places at overlapping times on the same day."""
        # Initial slot: Monday 09:00 - 10:30
        ScheduleService.create_schedule_entry(
            class_section=self.sec1,
            teacher=self.teacher1,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(10, 30),
            room='Lab 301'
        )

        # Attempt to schedule teacher1 for sec2 on Monday 10:00 - 11:30 (overlaps 10:00-10:30)
        conflicts = ScheduleService.detect_conflicts(
            teacher=self.teacher1,
            room='Room 402',
            class_section=self.sec2,
            day_of_week=1,
            start_time=time(10, 0),
            end_time=time(11, 30)
        )

        self.assertTrue(any(c['type'] == 'TEACHER_CONFLICT' for c in conflicts))

        with self.assertRaises(ValidationError):
            ScheduleService.create_schedule_entry(
                class_section=self.sec2,
                teacher=self.teacher1,
                day_of_week=1,
                start_time=time(10, 0),
                end_time=time(11, 30),
                room='Room 402'
            )

    def test_room_collision_conflict(self):
        """Same classroom cannot be double booked at overlapping times on the same day."""
        ScheduleService.create_schedule_entry(
            class_section=self.sec1,
            teacher=self.teacher1,
            day_of_week=2,  # Tuesday
            start_time=time(11, 0),
            end_time=time(12, 30),
            room='Room 401'
        )

        # Attempt to book same Room 401 by teacher2 for sec2 on Tuesday 11:30 - 13:00
        conflicts = ScheduleService.detect_conflicts(
            teacher=self.teacher2,
            room='Room 401',
            class_section=self.sec2,
            day_of_week=2,
            start_time=time(11, 30),
            end_time=time(13, 0)
        )

        self.assertTrue(any(c['type'] == 'ROOM_CONFLICT' for c in conflicts))

    def test_non_overlapping_slots_allowed(self):
        """Adjacent or non-overlapping slots on the same day proceed without conflict."""
        ScheduleService.create_schedule_entry(
            class_section=self.sec1,
            teacher=self.teacher1,
            day_of_week=3,  # Wednesday
            start_time=time(9, 0),
            end_time=time(10, 30),
            room='Lab 301'
        )

        # Slot starting right at 10:30
        entry2 = ScheduleService.create_schedule_entry(
            class_section=self.sec2,
            teacher=self.teacher2,
            day_of_week=3,
            start_time=time(10, 30),
            end_time=time(12, 0),
            room='Lab 301'
        )
        self.assertIsNotNone(entry2.pk)
