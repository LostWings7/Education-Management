"""
Unit tests for AttendanceService: session creation, attendance logging, and dynamic metrics calculation.
"""

from datetime import date
from django.test import TestCase
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    ClassSection,
    Enrollment,
    AttendanceRecord,
    AcademicYear,
    Semester
)
from apps.academic.services import AttendanceService, EnrollmentService


class AttendanceServiceTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')

        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_user = User.objects.create_user(email='prof@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_user, employee_id='T-01', department=self.dept)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)

        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)

        # 2 Students
        s1_u = User.objects.create_user(email='s1@example.com', password='Password@123', role=Role.STUDENT)
        self.student1 = StudentProfile.objects.create(user=s1_u, student_id='S-01', department=self.dept, program=self.prog)
        EnrollmentService.enroll_student(self.student1, self.section)

        s2_u = User.objects.create_user(email='s2@example.com', password='Password@123', role=Role.STUDENT)
        self.student2 = StudentProfile.objects.create(user=s2_u, student_id='S-02', department=self.dept, program=self.prog)
        EnrollmentService.enroll_student(self.student2, self.section)

    def test_session_creation_initializes_roster(self):
        """Creating a session initializes AttendanceRecord for all active enrolled students."""
        session = AttendanceService.create_session_with_roster(
            class_section=self.section,
            teacher=self.teacher,
            session_date=date(2026, 2, 1),
            title='Lecture 1'
        )
        self.assertEqual(session.attendance_records.count(), 2)

    def test_dynamic_attendance_percentage_calculation(self):
        """Attendance percentage must be derived dynamically from recorded session records."""
        # Conduct 4 sessions
        for i in range(1, 5):
            sess = AttendanceService.create_session_with_roster(
                class_section=self.section,
                teacher=self.teacher,
                session_date=date(2026, 2, i),
                title=f'Lecture {i}'
            )
            # Student 1: Present in all 4 (100%)
            # Student 2: Present in 2, Absent in 2 (50%)
            AttendanceService.mark_attendance(
                session=sess,
                attendance_dict={
                    self.student1.pk: AttendanceRecord.AttendanceStatus.PRESENT,
                    self.student2.pk: AttendanceRecord.AttendanceStatus.PRESENT if (i <= 2) else AttendanceRecord.AttendanceStatus.ABSENT
                }
            )

        calc1 = AttendanceService.calculate_student_attendance(self.student1, class_section=self.section)
        self.assertEqual(calc1['total_sessions'], 4)
        self.assertEqual(calc1['attended_sessions'], 4)
        self.assertEqual(calc1['attendance_percentage'], 100.0)
        self.assertEqual(calc1['status'], 'EXCELLENT')

        calc2 = AttendanceService.calculate_student_attendance(self.student2, class_section=self.section)
        self.assertEqual(calc2['total_sessions'], 4)
        self.assertEqual(calc2['attended_sessions'], 2)
        self.assertEqual(calc2['absent_count'], 2)
        self.assertEqual(calc2['attendance_percentage'], 50.0)
        self.assertEqual(calc2['status'], 'CRITICAL')
        self.assertTrue(calc2['is_below_minimum'])
