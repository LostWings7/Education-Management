"""
Deterministic Notification Dispatcher & Smart Digest Service.
Consumes authoritative deterministic analytics outputs without duplicating business arithmetic.
Enforces deduplication hashing and respect for user preferences.
"""

import hashlib
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.urls import reverse
from apps.core.models import User
from apps.academic.models import (
    StudentProfile,
    TeacherProfile,
    Course,
    ClassSection,
    Assignment,
    AssignmentSubmission
)
from apps.analytics.schemas.insight import (
    AttendanceAnalyticsResult,
    RiskEvaluationResult,
    AnomalyEvent
)
from apps.interventions.models import Intervention
from .models import Notification, NotificationPreference


class NotificationDispatcherService:
    """
    Evaluates triggers deterministically, performs deduplication hashing,
    checks preferences, and persists user notifications.
    """

    @classmethod
    def create_event_hash(cls, recipient_id: int, notification_type: str, entity_key: str, date_bucket: str) -> str:
        """
        Creates a deterministic SHA-256 deduplication key.
        """
        raw = f"{recipient_id}:{notification_type}:{entity_key}:{date_bucket}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def dispatch(
        cls,
        recipient: User,
        notification_type: str,
        priority: str,
        title: str,
        message: str,
        link_url: str = '',
        entity_key: str = '',
        date_bucket: Optional[str] = None
    ) -> Optional[Notification]:
        """
        Main entrypoint to dispatch a notification with deduplication & preference enforcement.
        """
        if not date_bucket:
            date_bucket = timezone.now().strftime("%Y-%m-%d")

        event_hash = cls.create_event_hash(recipient.pk, notification_type, entity_key, date_bucket)

        # 1. Deduplication check
        if Notification.objects.filter(event_hash=event_hash).exists():
            return None

        # 2. User preference check (CRITICAL priority cannot be muted)
        if priority != Notification.Priority.CRITICAL:
            prefs = NotificationPreference.get_for_user(recipient)
            if notification_type == Notification.NotificationType.ATTENDANCE_WARNING and not prefs.enable_attendance_warnings:
                return None
            elif notification_type in [Notification.NotificationType.ASSIGNMENT_DEADLINE, Notification.NotificationType.ASSIGNMENT_OVERDUE] and not prefs.enable_assignment_reminders:
                return None
            elif notification_type in [Notification.NotificationType.INTERVENTION_ASSIGNED, Notification.NotificationType.INTERVENTION_ACTION_DUE, Notification.NotificationType.INTERVENTION_OVERDUE] and not prefs.enable_intervention_updates:
                return None
            elif notification_type == Notification.NotificationType.ANNOUNCEMENT and not prefs.enable_announcements:
                return None

        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            link_url=link_url,
            event_hash=event_hash
        )

    # -------------------------------------------------------------------------
    # Deterministic Academic Consumers
    # -------------------------------------------------------------------------

    @classmethod
    def notify_attendance_deficit(
        cls,
        student: StudentProfile,
        course_code: str,
        att_res: AttendanceAnalyticsResult
    ) -> Optional[Notification]:
        """
        Triggered when attendance falls below institutional threshold or absence buffer is 0.
        """
        if att_res.attendance_percentage < 60.0:
            prio = Notification.Priority.CRITICAL
            msg = f"Your attendance in {course_code} is {att_res.attendance_percentage}%. Immediate academic attendance escalation required."
        elif att_res.attendance_percentage < 75.0:
            prio = Notification.Priority.WARNING
            msg = f"Your attendance in {course_code} is {att_res.attendance_percentage}%. You have {att_res.absence_buffer} absence buffer sessions remaining."
        else:
            return None

        return cls.dispatch(
            recipient=student.user,
            notification_type=Notification.NotificationType.ATTENDANCE_WARNING,
            priority=prio,
            title=f"Attendance Alert: {course_code}",
            message=msg,
            link_url=reverse('portal:student_attendance'),
            entity_key=f"att_{course_code}",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )

    @classmethod
    def notify_risk_escalation(
        cls,
        student: StudentProfile,
        course_code: str,
        risk_res: RiskEvaluationResult
    ) -> Optional[Notification]:
        """
        Triggered when risk engine evaluates HIGH or CRITICAL academic risk.
        """
        if risk_res.risk_level not in ['HIGH', 'CRITICAL']:
            return None

        prio = Notification.Priority.CRITICAL if risk_res.risk_level == 'CRITICAL' else Notification.Priority.WARNING
        return cls.dispatch(
            recipient=student.user,
            notification_type=Notification.NotificationType.RISK_ESCALATION,
            priority=prio,
            title=f"Academic Risk Alert ({risk_res.risk_level}): {course_code}",
            message=f"Course risk score evaluated at {risk_res.composite_score}/100. Review recommended recovery actions.",
            link_url=reverse('portal:student_analytics'),
            entity_key=f"risk_{course_code}_{risk_res.risk_level}",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )

    @classmethod
    def notify_teacher_anomaly(
        cls,
        teacher: TeacherProfile,
        student: StudentProfile,
        course_code: str,
        anom_res: AnomalyEvent
    ) -> Optional[Notification]:
        """
        Notifies instructor of acute performance drop anomaly for an enrolled student.
        """
        if not anom_res.is_anomaly:
            return None

        return cls.dispatch(
            recipient=teacher.user,
            notification_type=Notification.NotificationType.ACUTE_ANOMALY,
            priority=Notification.Priority.CRITICAL if anom_res.severity == 'CRITICAL' else Notification.Priority.WARNING,
            title=f"Acute Anomaly Detected: {student.user.get_full_name()} ({course_code})",
            message=f"Acute score drop of {anom_res.delta} points (Z = {anom_res.z_score}) detected. Review student profile for possible intervention.",
            link_url=reverse('portal:teacher_early_warnings'),
            entity_key=f"anom_{student.student_id}_{course_code}",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )

    @classmethod
    def notify_assignment_deadline(
        cls,
        student: StudentProfile,
        assignment: Assignment,
        is_overdue: bool = False
    ) -> Optional[Notification]:
        """
        Notifies student of approaching assignment deadline or overdue coursework.
        """
        if is_overdue:
            return cls.dispatch(
                recipient=student.user,
                notification_type=Notification.NotificationType.ASSIGNMENT_OVERDUE,
                priority=Notification.Priority.WARNING,
                title=f"Overdue Coursework: {assignment.title}",
                message=f"Assignment in {assignment.class_section.course.code} was due on {assignment.due_date.strftime('%b %d, %Y')}.",
                link_url=reverse('portal:student_assignments'),
                entity_key=f"assign_overdue_{assignment.pk}",
                date_bucket=timezone.now().strftime("%Y-%m-%d")
            )
        else:
            return cls.dispatch(
                recipient=student.user,
                notification_type=Notification.NotificationType.ASSIGNMENT_DEADLINE,
                priority=Notification.Priority.INFO,
                title=f"Upcoming Assignment Deadline: {assignment.title}",
                message=f"Due tomorrow ({assignment.due_date.strftime('%b %d, %H:%M')}) in {assignment.class_section.course.code}.",
                link_url=reverse('portal:student_assignments'),
                entity_key=f"assign_due_{assignment.pk}",
                date_bucket=timezone.now().strftime("%Y-%m-%d")
            )

    @classmethod
    def notify_intervention_event(
        cls,
        intervention: Intervention,
        event_type: str,
        actor: Optional[User] = None
    ) -> List[Notification]:
        """
        Dispatches intervention lifecycle notifications to student and supervisor.
        """
        notifications = []
        student_user = intervention.student.user

        if event_type == 'ASSIGNED':
            n = cls.dispatch(
                recipient=student_user,
                notification_type=Notification.NotificationType.INTERVENTION_ASSIGNED,
                priority=Notification.Priority.WARNING,
                title=f"Support Plan Assigned: {intervention.title}",
                message=f"A targeted support plan has been assigned in {intervention.course.code}. Objective: {intervention.objective}.",
                link_url=reverse('portal:student_intervention_detail', kwargs={'pk': intervention.pk}),
                entity_key=f"intv_assign_{intervention.pk}"
            )
            if n:
                notifications.append(n)

        elif event_type == 'OVERDUE':
            n1 = cls.dispatch(
                recipient=student_user,
                notification_type=Notification.NotificationType.INTERVENTION_OVERDUE,
                priority=Notification.Priority.CRITICAL,
                title=f"Support Plan Overdue: {intervention.title}",
                message=f"Checklist actions in {intervention.course.code} are overdue. Target completion date was {intervention.due_date}.",
                link_url=reverse('portal:student_intervention_detail', kwargs={'pk': intervention.pk}),
                entity_key=f"intv_overdue_stu_{intervention.pk}",
                date_bucket=timezone.now().strftime("%Y-%m-%d")
            )
            if n1:
                notifications.append(n1)

            if intervention.assigned_to:
                n2 = cls.dispatch(
                    recipient=intervention.assigned_to.user,
                    notification_type=Notification.NotificationType.INTERVENTION_OVERDUE,
                    priority=Notification.Priority.WARNING,
                    title=f"Supervised Support Plan Overdue: {intervention.student.user.get_full_name()}",
                    message=f"Intervention plan '{intervention.title}' is overdue for student {intervention.student.student_id}.",
                    link_url=reverse('portal:teacher_intervention_detail', kwargs={'pk': intervention.pk}),
                    entity_key=f"intv_overdue_tea_{intervention.pk}",
                    date_bucket=timezone.now().strftime("%Y-%m-%d")
                )
                if n2:
                    notifications.append(n2)

        return notifications


class DigestService:
    """
    Compiles periodic smart digests from deterministic facts.
    """

    @classmethod
    def generate_student_digest(cls, student: StudentProfile) -> Notification:
        """
        Generates daily academic summary digest for student.
        """
        pending_assignments = Assignment.objects.filter(
            class_section__enrollments__student=student,
            class_section__enrollments__status='ENROLLED'
        ).exclude(
            submissions__student=student,
            submissions__status='SUBMITTED'
        ).count()

        active_intvs = Intervention.objects.filter(
            student=student,
            status__in=['APPROVED', 'ASSIGNED', 'IN_PROGRESS']
        ).count()

        title = "Your Daily Academic Digest"
        msg = f"Good morning {student.user.get_short_name()}. You have {pending_assignments} pending assignment(s) and {active_intvs} active academic recovery action(s) today."

        return NotificationDispatcherService.dispatch(
            recipient=student.user,
            notification_type=Notification.NotificationType.DIGEST_SUMMARY,
            priority=Notification.Priority.INFO,
            title=title,
            message=msg,
            link_url=reverse('portal:student_dashboard'),
            entity_key="student_daily_digest",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )

    @classmethod
    def generate_teacher_digest(cls, teacher: TeacherProfile) -> Notification:
        """
        Generates daily teaching summary digest for teacher.
        """
        sec_ids = ClassSection.objects.filter(primary_teacher=teacher, semester__is_active=True).values_list('id', flat=True)
        pending_grading = AssignmentSubmission.objects.filter(
            assignment__class_section_id__in=sec_ids,
            status=AssignmentSubmission.SubmissionStatus.SUBMITTED
        ).count()

        active_intvs = Intervention.objects.filter(
            class_section_id__in=sec_ids,
            status__in=['RECOMMENDED', 'ASSIGNED', 'IN_PROGRESS']
        ).count()

        title = "Your Daily Teaching Digest"
        msg = f"Good morning Professor {teacher.user.last_name or teacher.user.email}. You have {pending_grading} submission(s) awaiting grading and {active_intvs} active student support plan(s)."

        return NotificationDispatcherService.dispatch(
            recipient=teacher.user,
            notification_type=Notification.NotificationType.DIGEST_SUMMARY,
            priority=Notification.Priority.INFO,
            title=title,
            message=msg,
            link_url=reverse('portal:teacher_dashboard'),
            entity_key="teacher_daily_digest",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )

    @classmethod
    def generate_admin_digest(cls, admin_user: User) -> Notification:
        """
        Generates daily institutional digest for administrator.
        """
        total_intvs = Intervention.objects.filter(status__in=['RECOMMENDED', 'IN_PROGRESS']).count()
        overdue_intvs = sum(1 for iv in Intervention.objects.filter(status__in=['ASSIGNED', 'IN_PROGRESS']) if iv.is_overdue)

        title = "Daily University Academic Intelligence Digest"
        msg = f"Institutional Overview: {total_intvs} total interventions currently active across departments ({overdue_intvs} overdue)."

        return NotificationDispatcherService.dispatch(
            recipient=admin_user,
            notification_type=Notification.NotificationType.DIGEST_SUMMARY,
            priority=Notification.Priority.INFO,
            title=title,
            message=msg,
            link_url=reverse('portal_admin:dashboard'),
            entity_key="admin_daily_digest",
            date_bucket=timezone.now().strftime("%Y-%m-%d")
        )
