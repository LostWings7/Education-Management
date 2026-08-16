"""
Unit tests for Study Plan Semantic and Feasibility Validation.
"""

from datetime import date
from django.test import TestCase
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
    Enrollment,
    Assignment
)
from apps.ai_service.schemas.responses import (
    StudyPlanSchema,
    StudyPlanDaySchema,
    StudyPlanTaskSchema
)
from apps.ai_service.services import StudyPlanValidator


class AIStudyPlanValidationTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='teacher.plan@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-PLAN', department=self.dept)

        s_u = User.objects.create_user(email='student.plan@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-PLAN', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)
        Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        from django.utils import timezone
        from datetime import timedelta
        self.assignment = Assignment.objects.create(
            class_section=self.section,
            teacher=self.teacher,
            title="Valid Problem Set 1",
            due_date=timezone.now() + timedelta(days=10),
            max_marks=100.0
        )

    def test_fabricated_course_and_assignment_ids_are_rejected(self):
        """Fabricated course codes and non-existent assignment IDs are purged by validator."""
        fake_task = StudyPlanTaskSchema(
            course_code="PHYS999", # Student not enrolled
            task_type="TOPIC_STUDY",
            title="Fake Quantum Topic",
            duration_minutes=45,
            description="Fake task",
            assignment_id=99999 # Fake assignment
        )
        valid_task = StudyPlanTaskSchema(
            course_code="CS201",
            task_type="ASSIGNMENT_PREP",
            title="Work on Assignment 1",
            duration_minutes=60,
            description="Real assignment",
            assignment_id=self.assignment.pk
        )

        plan = StudyPlanSchema(
            plan_title="Test Plan",
            target_week="Mar 02 - Mar 06",
            days=[
                StudyPlanDaySchema(
                    day_name="Monday",
                    date_str="2026-03-02",
                    focus_summary="Test Day",
                    tasks=[fake_task, valid_task]
                )
            ]
        )

        sanitized, is_valid = StudyPlanValidator.validate_plan(plan, self.student)
        self.assertFalse(is_valid)
        self.assertEqual(sanitized.validation_status, "VALIDATED_AND_REMEDIATED")
        # Fake task must be purged
        self.assertEqual(len(sanitized.days[0].tasks), 1)
        self.assertEqual(sanitized.days[0].tasks[0].course_code, "CS201")

    def test_daily_workload_cap_enforcement(self):
        """Total daily study time is capped at max daily hours (e.g. 270 minutes)."""
        heavy_tasks = [
            StudyPlanTaskSchema(course_code="CS201", task_type="TOPIC_STUDY", title=f"Study {i}", duration_minutes=90, description="Task")
            for i in range(5) # 5 * 90 = 450 minutes > 270 minutes limit
        ]

        plan = StudyPlanSchema(
            plan_title="Overload Plan",
            target_week="Mar 02 - Mar 06",
            days=[StudyPlanDaySchema(day_name="Monday", date_str="2026-03-02", focus_summary="Overload", tasks=heavy_tasks)]
        )

        sanitized, is_valid = StudyPlanValidator.validate_plan(plan, self.student)
        self.assertFalse(is_valid)
        self.assertTrue(sanitized.days[0].total_study_minutes <= 270)

    def test_student_ai_study_planner_view_endpoint(self):
        """Student study planner view renders successfully with 200 and generates context."""
        from django.urls import reverse
        self.client.login(email='student.plan@example.com', password='Password@123')
        res = self.client.get(reverse('portal:student_ai_planner'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'AI Study Planner')

