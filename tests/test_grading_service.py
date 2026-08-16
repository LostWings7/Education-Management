"""
Unit tests for GradingService: authoritative calculation, zero double-counting,
published snapshot behavior, and audit trails.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import User, Role, AuditLog
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    ClassSection,
    Enrollment,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    AcademicYear,
    Semester
)
from apps.academic.services import GradingService, EnrollmentService, AssignmentService


class GradingServiceTest(TestCase):
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

        s_user = User.objects.create_user(email='ada@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_user, student_id='S-01', department=self.dept, program=self.prog)
        self.enrollment = EnrollmentService.enroll_student(self.student, self.section)

    def test_weighted_grade_calculation_and_no_double_counting(self):
        """
        Verify that assignments and evaluative assessments are aggregated cleanly without double counting:
        - Quiz 1: Max 100, Weight 20%, Score 90 (contribution = 18.00)
        - Assignments Category: Weight 30%, Student gets 45/50 on PS1 and 45/50 on PS2 -> 90% (contribution = 27.00)
        - Midterm Exam: Max 100, Weight 50%, Score 80 (contribution = 40.00)
        Total Expected = 18 + 27 + 40 = 85.00% -> Grade 'A'
        """
        # 1. Direct Quiz Assessment
        q1 = Assessment.objects.create(
            class_section=self.section,
            title='Quiz 1',
            assessment_type=Assessment.AssessmentType.QUIZ,
            max_marks=Decimal('100.00'),
            weightage_percentage=Decimal('20.00')
        )
        AssessmentResult.objects.create(
            assessment=q1,
            student=self.student,
            marks_obtained=Decimal('90.00'),
            graded_by=self.teacher
        )

        # 2. Formative Assignments (PS1 & PS2)
        ps1 = AssignmentService.create_assignment(self.section, self.teacher, 'PS 1', 'desc', Decimal('50.00'), timezone.now() + timedelta(days=2))
        sub1 = AssignmentService.submit_assignment(ps1, self.student, 'sol1')
        AssignmentService.grade_submission(sub1, self.teacher, Decimal('45.00'))

        ps2 = AssignmentService.create_assignment(self.section, self.teacher, 'PS 2', 'desc', Decimal('50.00'), timezone.now() + timedelta(days=2))
        sub2 = AssignmentService.submit_assignment(ps2, self.student, 'sol2')
        AssignmentService.grade_submission(sub2, self.teacher, Decimal('45.00'))

        # Aggregate Assignments Assessment (30% weight)
        ass_portfolio = Assessment.objects.create(
            class_section=self.section,
            title='Assignments Category',
            assessment_type=Assessment.AssessmentType.ASSIGNMENTS,
            max_marks=Decimal('100.00'),
            weightage_percentage=Decimal('30.00')
        )

        # 3. Direct Midterm Exam Assessment
        mid = Assessment.objects.create(
            class_section=self.section,
            title='Midterm Exam',
            assessment_type=Assessment.AssessmentType.MIDTERM,
            max_marks=Decimal('100.00'),
            weightage_percentage=Decimal('50.00')
        )
        AssessmentResult.objects.create(
            assessment=mid,
            student=self.student,
            marks_obtained=Decimal('80.00'),
            graded_by=self.teacher
        )

        # Calculate student grade
        result = GradingService.calculate_student_course_grade(self.student, self.section)

        self.assertEqual(result['final_percentage'], Decimal('85.00'))
        self.assertEqual(result['final_grade_letter'], 'A')
        self.assertEqual(result['total_evaluated_weights'], Decimal('100.00'))

    def test_publish_grades_and_snapshot_recalculation_with_audit(self):
        """Publishing grades updates Enrollment read-only snapshot; recalculation logs audit trail."""
        q1 = Assessment.objects.create(
            class_section=self.section,
            title='Final Assessment',
            assessment_type=Assessment.AssessmentType.FINAL,
            max_marks=Decimal('100.00'),
            weightage_percentage=Decimal('100.00')
        )
        res = AssessmentResult.objects.create(
            assessment=q1,
            student=self.student,
            marks_obtained=Decimal('76.00'),
            graded_by=self.teacher
        )

        # Publish
        published_count = GradingService.publish_section_grades(self.section, actor=self.teacher.user)
        self.assertEqual(published_count, 1)

        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.is_grade_published)
        self.assertEqual(self.enrollment.final_percentage, Decimal('76.00'))
        self.assertEqual(self.enrollment.final_grade_letter, 'B+')

        # Correct assessment score to 92.00 (A+)
        res.marks_obtained = Decimal('92.00')
        res.save()

        # Recalculate snapshot through GradingService
        GradingService.recalculate_and_update_enrollment_snapshot(self.enrollment, actor=self.teacher.user)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.final_percentage, Decimal('92.00'))
        self.assertEqual(self.enrollment.final_grade_letter, 'A+')

        # Verify AuditLog entry was created for recalculation
        audit = AuditLog.objects.filter(action='RECALCULATE_ENROLLMENT_GRADE').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details['new_grade'], 'A+')
