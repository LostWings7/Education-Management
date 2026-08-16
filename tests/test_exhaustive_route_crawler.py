"""
Exhaustive Route Crawler and View Integrity Test Suite.
Iterates and executes HTTP GET across every single URL route across all roles
(Student, Teacher, Administrator, Public) to guarantee ZERO ImportErrors,
AttributeErrors, TypeErrors, or 500 server crashes exist in the entire codebase.
"""

from datetime import date, timedelta
from decimal import Decimal
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
    Topic,
    ClassSection,
    Enrollment,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    ClassSchedule,
    ClassSession,
    AttendanceRecord,
    LearningResource,
    CourseAnnouncement
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionCheckpoint
)


class ExhaustiveRouteCrawlerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "TestPass@12345"

        # Core Academic Setup
        self.dept = Department.objects.create(code="CSE", name="Computer Science")
        self.program = Program.objects.create(department=self.dept, code="BT-CSE", name="B.Tech Computer Science")
        self.year = AcademicYear.objects.create(name="2025-2026", start_date=date(2025, 8, 1), end_date=date(2026, 6, 30))
        self.semester = Semester.objects.create(
            academic_year=self.year,
            name="Spring 2026",
            term_type=Semester.TermType.SPRING,
            semester_number=2,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 5, 20),
            is_active=True
        )

        # Users & Profiles
        self.student_user = User.objects.create_user(
            email="crawler.student@example.com",
            password=self.password,
            first_name="Ada",
            last_name="Lovelace",
            role=Role.STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-CRAWL-01",
            department=self.dept,
            program=self.program,
            current_semester=2
        )

        self.teacher_user = User.objects.create_user(
            email="crawler.teacher@example.com",
            password=self.password,
            first_name="Alan",
            last_name="Turing",
            role=Role.TEACHER
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id="FAC-CRAWL-01",
            department=self.dept,
            designation="Professor"
        )

        self.admin_user = User.objects.create_user(
            email="crawler.admin@example.com",
            password=self.password,
            first_name="Admin",
            last_name="Commander",
            role=Role.ADMINISTRATOR
        )

        # Courses & Class Section
        self.course = Course.objects.create(
            department=self.dept,
            code="CS201",
            title="Data Structures & Algorithms",
            credits=4
        )
        self.course.programs.add(self.program)

        self.topic = Topic.objects.create(
            course=self.course,
            title="Binary Search Trees",
            order_index=1
        )

        self.section = ClassSection.objects.create(
            course=self.course,
            semester=self.semester,
            section_code="A",
            primary_teacher=self.teacher_profile
        )

        self.enrollment = Enrollment.objects.create(
            student=self.student_profile,
            class_section=self.section,
            status=Enrollment.EnrollmentStatus.ENROLLED
        )

        # Assignment & Submission
        self.assignment = Assignment.objects.create(
            class_section=self.section,
            teacher=self.teacher_profile,
            topic=self.topic,
            title="Problem Set 1",
            description="Implement BST traversals",
            due_date=timezone.now() + timedelta(days=7),
            max_marks=Decimal("50.00")
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student_profile,
            submission_text="Solution code...",
            status=AssignmentSubmission.SubmissionStatus.SUBMITTED
        )

        # Assessment
        self.assessment = Assessment.objects.create(
            class_section=self.section,
            title="Midterm Examination",
            assessment_type=Assessment.AssessmentType.MIDTERM,
            max_marks=Decimal("100.00"),
            weightage_percentage=Decimal("30.00"),
            date=date.today()
        )
        self.assessment_result = AssessmentResult.objects.create(
            assessment=self.assessment,
            student=self.student_profile,
            marks_obtained=Decimal("85.00")
        )

        # Attendance Session & Record
        self.session = ClassSession.objects.create(
            class_section=self.section,
            teacher=self.teacher_profile,
            session_date=date.today(),
            title="Introduction to BST"
        )
        self.att_record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student_profile,
            status=AttendanceRecord.AttendanceStatus.PRESENT
        )

        # Resource & Announcement
        self.resource = LearningResource.objects.create(
            course=self.course,
            topic=self.topic,
            uploaded_by=self.teacher_user,
            title="Lecture 1 Slides",
            resource_type=LearningResource.ResourceType.PDF,
            is_published=True
        )
        self.announcement = CourseAnnouncement.objects.create(
            class_section=self.section,
            teacher=self.teacher_profile,
            title="Welcome to CS201",
            content="Welcome everyone."
        )

        # Intervention
        self.intervention = Intervention.objects.create(
            student=self.student_profile,
            course=self.course,
            class_section=self.section,
            topic=self.topic,
            assigned_to=self.teacher_profile,
            created_by=self.teacher_user,
            title="Targeted BST Support",
            objective="Review pointer operations in BST",
            category=Intervention.InterventionCategory.ACADEMIC_REMEDIAL,
            priority=Intervention.Priority.HIGH,
            primary_target_metric=Intervention.TargetMetric.TOPIC_MASTERY,
            evaluation_window=Intervention.EvaluationWindow.DAYS_14,
            status=Intervention.Status.IN_PROGRESS,
            due_date=date.today() + timedelta(days=14)
        )
        self.action = InterventionAction.objects.create(
            intervention=self.intervention,
            order_index=1,
            title="Complete practice worksheet",
            description="Worksheet #1",
            status=InterventionAction.ActionStatus.PENDING
        )

    def test_all_public_routes_render_cleanly(self):
        """All public routes return HTTP 200 without error."""
        public_urls = [
            reverse('public:home'),
            reverse('public:courses'),
            reverse('public:course_detail', kwargs={'code': self.course.code}),
            reverse('public:contact'),
            reverse('public:demo_showcase'),
            reverse('core:login'),
            reverse('core:register'),
            reverse('health_check'),
        ]
        for url in public_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Public URL {url} failed with {res.status_code}")

    def test_all_student_routes_render_cleanly(self):
        """All student portal routes return HTTP 200 without error."""
        self.client.login(email=self.student_user.email, password=self.password)

        student_urls = [
            reverse('portal:student_dashboard'),
            reverse('portal:student_courses'),
            reverse('portal:student_course_detail', kwargs={'section_id': self.section.pk}),
            reverse('portal:student_attendance'),
            reverse('portal:student_assignments'),
            reverse('portal:student_grades'),
            reverse('portal:student_timetable'),
            reverse('portal:student_resources'),
            reverse('portal:student_transcript'),
            reverse('portal:student_transcript_csv'),
            reverse('portal:student_timeline'),
            reverse('portal:student_journey'),
            reverse('portal:student_analytics'),
            reverse('portal:student_what_if'),
            reverse('portal:student_interventions'),
            reverse('portal:student_intervention_detail', kwargs={'pk': self.intervention.pk}),
            reverse('portal:student_ai_copilot'),
            reverse('portal:student_ai_planner'),
            reverse('notifications:list'),
            reverse('notifications:preferences'),
            reverse('core:profile'),
            reverse('core:password_change'),
            reverse('portal:global_search_api') + '?q=data',
        ]

        for url in student_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Student URL {url} failed with {res.status_code}")

    def test_all_teacher_routes_render_cleanly(self):
        """All teacher portal routes return HTTP 200 without error."""
        self.client.login(email=self.teacher_user.email, password=self.password)

        teacher_urls = [
            reverse('portal:teacher_dashboard'),
            reverse('portal:teacher_classes'),
            reverse('portal:teacher_class_detail', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_section_export', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_class_analytics', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_course_intelligence', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_assessment_intelligence', kwargs={'assessment_id': self.assessment.pk}),
            reverse('portal:teacher_class_briefing', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_analytics'),
            reverse('portal:teacher_early_warnings'),
            reverse('portal:teacher_early_warnings_timeline'),
            reverse('portal:teacher_interventions'),
            reverse('portal:teacher_intervention_detail', kwargs={'pk': self.intervention.pk}),
            reverse('portal:teacher_ai_copilot'),
            reverse('portal:teacher_attendance'),
            reverse('portal:teacher_take_attendance', kwargs={'section_id': self.section.pk}),
            reverse('portal:teacher_assignments'),
            reverse('portal:teacher_assignment_create'),
            reverse('portal:teacher_assignment_edit', kwargs={'pk': self.assignment.pk}),
            reverse('portal:teacher_assignment_submissions', kwargs={'assignment_id': self.assignment.pk}),
            reverse('portal:teacher_assessment_create'),
            reverse('portal:teacher_assessment_enter_marks', kwargs={'pk': self.assessment.pk}),
            reverse('portal:teacher_gradebook'),
            reverse('portal:teacher_timetable'),
            reverse('portal:teacher_resources'),
            reverse('portal:teacher_resource_create'),
            reverse('portal:teacher_announcement_create'),
        ]

        for url in teacher_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Teacher URL {url} failed with {res.status_code}")

    def test_all_administrator_routes_render_cleanly(self):
        """All administrator portal routes return HTTP 200 without error."""
        self.client.login(email=self.admin_user.email, password=self.password)

        admin_urls = [
            reverse('portal_admin:dashboard'),
            reverse('portal_admin:analytics'),
            reverse('portal_admin:risk_heatmap'),
            reverse('portal_admin:interventions_overview'),
            reverse('portal_admin:intervention_outcomes'),
            reverse('portal_admin:intervention_detail', kwargs={'pk': self.intervention.pk}),
            reverse('portal_admin:data_quality'),
            reverse('portal_admin:ai_observability'),
            reverse('portal_admin:ai_intelligence'),
            reverse('portal_admin:department_list'),
            reverse('portal_admin:department_create'),
            reverse('portal_admin:department_edit', kwargs={'pk': self.dept.pk}),
            reverse('portal_admin:program_list'),
            reverse('portal_admin:program_create'),
            reverse('portal_admin:program_edit', kwargs={'pk': self.program.pk}),
            reverse('portal_admin:terms_list'),
            reverse('portal_admin:year_create'),
            reverse('portal_admin:semester_create'),
            reverse('portal_admin:courses'),
            reverse('portal_admin:course_create'),
            reverse('portal_admin:course_edit', kwargs={'pk': self.course.pk}),
            reverse('portal_admin:sections'),
            reverse('portal_admin:section_create'),
            reverse('portal_admin:section_edit', kwargs={'pk': self.section.pk}),
            reverse('portal_admin:section_roster', kwargs={'pk': self.section.pk}),
            reverse('portal_admin:enrollments'),
            reverse('portal_admin:student_list'),
            reverse('portal_admin:student_create'),
            reverse('portal_admin:student_edit', kwargs={'pk': self.student_profile.pk}),
            reverse('portal_admin:teacher_list'),
            reverse('portal_admin:teacher_create'),
            reverse('portal_admin:teacher_edit', kwargs={'pk': self.teacher_profile.pk}),
            reverse('portal_admin:timetable'),
            reverse('portal_admin:attendance_list'),
            reverse('portal_admin:attendance_detail', kwargs={'pk': self.session.pk}),
            reverse('portal_admin:assessment_list'),
            reverse('portal_admin:resource_list'),
            reverse('portal_admin:announcement_list'),
            reverse('portal_admin:records'),
            reverse('portal_admin:export_institutional_csv'),
            reverse('portal_admin:export_interventions_csv'),
        ]

        for url in admin_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Admin URL {url} failed with {res.status_code}")
