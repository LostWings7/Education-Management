"""
Unit tests for Phase 4 Intervention Lifecycle State Machine, Acknowledgment, and Audit Trails.
"""

from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import User, Role, AuditLog
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    ClassSection,
    Enrollment
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionAcknowledgement,
    InterventionEscalation
)
from apps.interventions.services import (
    InterventionLifecycleService,
    InterventionActionService
)


class InterventionLifecycleTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='teacher.lc@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-LC', department=self.dept)

        s_u = User.objects.create_user(email='student.lc@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-LC', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)
        self.enrollment = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        # Base recommendation
        self.intervention = Intervention.objects.create(
            student=self.student,
            course=self.course,
            class_section=self.section,
            assigned_to=self.teacher,
            created_by=t_u,
            title="Attendance Support Plan",
            category=Intervention.InterventionCategory.ATTENDANCE_RECOVERY,
            status=Intervention.Status.RECOMMENDED,
            priority=Intervention.Priority.HIGH,
            primary_target_metric=Intervention.TargetMetric.ATTENDANCE,
            due_date=timezone.now().date() + timezone.timedelta(days=14),
            objective="Recover attendance to 75%",
            baseline_metrics={"attendance_percentage": 52.0, "risk_score": 60.0}
        )

    def test_approve_recommendation_transitions_to_assigned(self):
        """Educator approval transitions RECOMMENDED to ASSIGNED and records AuditLog."""
        approved = InterventionLifecycleService.approve_recommendation(
            intervention=self.intervention,
            user=self.teacher.user,
            educator_notes="Approved with prioritized action steps."
        )
        self.assertEqual(approved.status, Intervention.Status.ASSIGNED)
        self.assertIsNotNone(approved.approved_at)

        # AuditLog entry
        log = AuditLog.objects.filter(action="APPROVE_INTERVENTION_RECOMMENDATION").last()
        self.assertIsNotNone(log)
        self.assertEqual(log.details.get("intervention_id"), self.intervention.pk)

    def test_dismiss_recommendation_transitions_to_dismissed(self):
        """Educator dismissal transitions RECOMMENDED to DISMISSED with recorded reason."""
        dismissed = InterventionLifecycleService.dismiss_recommendation(
            intervention=self.intervention,
            user=self.teacher.user,
            reason="Student already attended medical makeup session."
        )
        self.assertEqual(dismissed.status, Intervention.Status.DISMISSED)
        self.assertIsNotNone(dismissed.dismissed_at)
        self.assertEqual(dismissed.dismissal_reason, "Student already attended medical makeup session.")

    def test_student_acknowledgment_accepts_and_starts_plan(self):
        """Student acceptance transitions ASSIGNED to IN_PROGRESS."""
        self.intervention.status = Intervention.Status.ASSIGNED
        self.intervention.save()

        ack = InterventionLifecycleService.acknowledge_by_student(
            intervention=self.intervention,
            student_user=self.student.user,
            ack_status=InterventionAcknowledgement.AckStatus.ACCEPTED,
            student_notes="I accept this plan."
        )
        self.intervention.refresh_from_db()
        self.assertEqual(ack.status, InterventionAcknowledgement.AckStatus.ACCEPTED)
        self.assertEqual(self.intervention.status, Intervention.Status.IN_PROGRESS)
        self.assertIsNotNone(self.intervention.started_at)

    def test_invalid_state_transition_raises_validation_error(self):
        """Cannot jump directly from RECOMMENDED to COMPLETED or CLOSED."""
        with self.assertRaises(ValidationError):
            InterventionLifecycleService.validate_transition(
                current_status=Intervention.Status.RECOMMENDED,
                target_status=Intervention.Status.COMPLETED
            )

        with self.assertRaises(ValidationError):
            InterventionLifecycleService.validate_transition(
                current_status=Intervention.Status.RECOMMENDED,
                target_status=Intervention.Status.CLOSED
            )

    def test_all_actions_completed_transitions_to_completed(self):
        """When all action steps are completed, intervention transitions to COMPLETED."""
        self.intervention.status = Intervention.Status.IN_PROGRESS
        self.intervention.save()

        act1 = InterventionAction.objects.create(
            intervention=self.intervention,
            order_index=1,
            title="Step 1",
            status=InterventionAction.ActionStatus.PENDING,
            verification_type=InterventionAction.VerificationType.STUDENT_CHECK
        )
        act2 = InterventionAction.objects.create(
            intervention=self.intervention,
            order_index=2,
            title="Step 2",
            status=InterventionAction.ActionStatus.PENDING,
            verification_type=InterventionAction.VerificationType.STUDENT_CHECK
        )

        InterventionActionService.update_action_status(act1, self.student.user, InterventionAction.ActionStatus.COMPLETED)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.Status.IN_PROGRESS)

        InterventionActionService.update_action_status(act2, self.student.user, InterventionAction.ActionStatus.COMPLETED)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.Status.COMPLETED)
        self.assertIsNotNone(self.intervention.completed_at)

    def test_educator_verification_required_guard(self):
        """Student cannot mark an EDUCATOR_VERIFIED action as COMPLETED."""
        act = InterventionAction.objects.create(
            intervention=self.intervention,
            order_index=1,
            title="Faculty Verification Step",
            status=InterventionAction.ActionStatus.PENDING,
            verification_type=InterventionAction.VerificationType.EDUCATOR_VERIFIED
        )

        with self.assertRaises(ValidationError):
            InterventionActionService.update_action_status(
                action=act,
                user=self.student.user,
                new_status=InterventionAction.ActionStatus.COMPLETED
            )

        # Faculty can verify and complete it
        updated = InterventionActionService.update_action_status(
            action=act,
            user=self.teacher.user,
            new_status=InterventionAction.ActionStatus.COMPLETED
        )
        self.assertEqual(updated.status, InterventionAction.ActionStatus.COMPLETED)
