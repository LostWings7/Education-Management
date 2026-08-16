"""
Django management command for periodic notification evaluation and digest generation.
Safe to execute repeatedly (idempotent deduplication hashing).
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import User, Role
from apps.academic.models import (
    StudentProfile,
    TeacherProfile,
    Assignment,
    Enrollment
)
from apps.interventions.models import Intervention
from apps.notifications.services import NotificationDispatcherService, DigestService


class Command(BaseCommand):
    help = 'Evaluates deterministic triggers, checks upcoming deadlines, and generates daily digests.'

    def handle(self, *args, **options):
        self.stdout.write("Starting periodic notification processing...")
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        count = 0

        # 1. Upcoming Assignment Deadlines (due within next 24 hours)
        upcoming_assignments = Assignment.objects.filter(
            due_date__gte=now,
            due_date__lte=tomorrow
        ).select_related('class_section__course')

        for assign in upcoming_assignments:
            enrs = Enrollment.objects.filter(class_section=assign.class_section, status='ENROLLED').select_related('student__user')
            for enr in enrs:
                sub = enr.student.assignment_submissions.filter(assignment=assign).first()
                if not sub or sub.status != 'SUBMITTED':
                    n = NotificationDispatcherService.notify_assignment_deadline(enr.student, assign, is_overdue=False)
                    if n:
                        count += 1

        # 2. Overdue Assignments
        overdue_assignments = Assignment.objects.filter(
            due_date__lt=now,
            due_date__gte=now - timedelta(days=7) # Look back 7 days
        ).select_related('class_section__course')

        for assign in overdue_assignments:
            enrs = Enrollment.objects.filter(class_section=assign.class_section, status='ENROLLED').select_related('student__user')
            for enr in enrs:
                sub = enr.student.assignment_submissions.filter(assignment=assign).first()
                if not sub or sub.status != 'SUBMITTED':
                    n = NotificationDispatcherService.notify_assignment_deadline(enr.student, assign, is_overdue=True)
                    if n:
                        count += 1

        # 3. Overdue Interventions
        overdue_intvs = list(Intervention.objects.filter(
            status__in=['APPROVED', 'ASSIGNED', 'IN_PROGRESS'],
            due_date__lt=now.date()
        ).select_related('student__user', 'assigned_to__user', 'course'))

        for iv in overdue_intvs:
            created_list = NotificationDispatcherService.notify_intervention_event(iv, event_type='OVERDUE')
            count += len(created_list)

        # 4. Daily Digests for Students
        students = StudentProfile.objects.select_related('user').all()
        for s in students:
            n = DigestService.generate_student_digest(s)
            if n:
                count += 1

        # 5. Daily Digests for Teachers
        teachers = TeacherProfile.objects.select_related('user').all()
        for t in teachers:
            n = DigestService.generate_teacher_digest(t)
            if n:
                count += 1

        # 6. Daily Digests for Admins
        admins = User.objects.filter(role=Role.ADMINISTRATOR)
        for a in admins:
            n = DigestService.generate_admin_digest(a)
            if n:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Notification processing completed successfully. Dispatched {count} new notification(s)."))
