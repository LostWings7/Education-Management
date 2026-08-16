"""
Phase 6 Automated Tests: Notification Center, Deduplication & Digests.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
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
    Assignment,
    AssignmentSubmission
)
from apps.analytics.schemas.insight import (
    AttendanceAnalyticsResult,
    RiskEvaluationResult,
    AnomalyEvent
)
from apps.interventions.models import Intervention
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import NotificationDispatcherService, DigestService


class Phase6NotificationTests(TestCase):
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
            program=self.prog
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            password="Password123!",
            role=Role.TEACHER,
            first_name="Alan",
            last_name="Turing"
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id="FAC-001",
            department=self.dept
        )

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            role=Role.ADMINISTRATOR,
            first_name="Admin",
            last_name="User"
        )

        self.ay = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        self.sem = Semester.objects.create(
            academic_year=self.ay,
            semester_number=1,
            name="Fall 2026",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 31),
            is_active=True
        )
        self.course = Course.objects.create(department=self.dept, code="CS101", title="Intro to CS", credits=Decimal('3.0'))
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code="A", primary_teacher=self.teacher)
        self.enr = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

    def test_notification_dispatch_and_deduplication(self):
        """Verify notifications are created with deterministic SHA-256 deduplication."""
        # 1. First dispatch
        n1 = NotificationDispatcherService.dispatch(
            recipient=self.student_user,
            notification_type=Notification.NotificationType.SYSTEM_ALERT,
            priority=Notification.Priority.INFO,
            title="Welcome to EduPortal",
            message="Your account is active.",
            entity_key="welcome_msg"
        )
        self.assertIsNotNone(n1)
        self.assertEqual(Notification.objects.filter(recipient=self.student_user).count(), 1)

        # 2. Duplicate dispatch attempt on the same day -> Must return None and not create duplicate
        n2 = NotificationDispatcherService.dispatch(
            recipient=self.student_user,
            notification_type=Notification.NotificationType.SYSTEM_ALERT,
            priority=Notification.Priority.INFO,
            title="Welcome to EduPortal",
            message="Your account is active.",
            entity_key="welcome_msg"
        )
        self.assertIsNone(n2)
        self.assertEqual(Notification.objects.filter(recipient=self.student_user).count(), 1)

    def test_preference_filtering_preserves_critical(self):
        """Verify non-critical notifications respect preferences, but critical alerts cannot be disabled."""
        prefs = NotificationPreference.get_for_user(self.student_user)
        prefs.enable_attendance_warnings = False
        prefs.save()

        # Non-critical attendance warning (WARNING) -> blocked by preference
        att_warn = AttendanceAnalyticsResult(
            attendance_percentage=70.0,
            total_conducted=10,
            present_count=7,
            absent_count=3,
            late_count=0,
            excused_count=0,
            remaining_sessions=10,
            target_threshold=75.0,
            absence_buffer=1,
            required_sessions=3,
            is_below_threshold=True,
            is_recovery_possible=True
        )
        res_warn = NotificationDispatcherService.notify_attendance_deficit(self.student, "CS101", att_warn)
        self.assertIsNone(res_warn)

        # Critical attendance deficit (<60%) -> Mandatory bypass
        att_crit = AttendanceAnalyticsResult(
            attendance_percentage=50.0,
            total_conducted=10,
            present_count=5,
            absent_count=5,
            late_count=0,
            excused_count=0,
            remaining_sessions=10,
            target_threshold=75.0,
            absence_buffer=0,
            required_sessions=8,
            is_below_threshold=True,
            is_recovery_possible=True
        )
        res_crit = NotificationDispatcherService.notify_attendance_deficit(self.student, "CS101", att_crit)
        self.assertIsNotNone(res_crit)
        self.assertEqual(res_crit.priority, Notification.Priority.CRITICAL)

    def test_process_notifications_management_command(self):
        """Verify the periodic process_notifications command runs cleanly and is idempotent."""
        # Create an upcoming assignment
        assign = Assignment.objects.create(
            class_section=self.section,
            teacher=self.teacher,
            title="Problem Set 1",
            due_date=timezone.now() + timedelta(hours=12),
            max_marks=Decimal('100.0')
        )

        call_command('process_notifications')
        notifs_count_1 = Notification.objects.count()
        self.assertGreater(notifs_count_1, 0)

        # Run a second time -> Deduplication guarantees 0 extra notifications
        call_command('process_notifications')
        notifs_count_2 = Notification.objects.count()
        self.assertEqual(notifs_count_1, notifs_count_2)

    def test_smart_digests(self):
        """Verify daily digests generate structured summaries for each role."""
        stu_digest = DigestService.generate_student_digest(self.student)
        tea_digest = DigestService.generate_teacher_digest(self.teacher)
        adm_digest = DigestService.generate_admin_digest(self.admin_user)

        self.assertIsNotNone(stu_digest)
        self.assertIsNotNone(tea_digest)
        self.assertIsNotNone(adm_digest)
        self.assertIn("Daily Academic Digest", stu_digest.title)
        self.assertIn("Daily Teaching Digest", tea_digest.title)
        self.assertIn("Daily University Academic", adm_digest.title)
