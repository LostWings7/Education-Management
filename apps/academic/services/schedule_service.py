"""
Timetable and schedule management service with 7-day conflict detection.
"""

from typing import Dict, Any, List, Optional
from datetime import time
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.academic.models import (
    ClassSchedule,
    ClassSection,
    TeacherProfile,
    StudentProfile,
    Semester,
    Enrollment
)


class ScheduleService:
    """
    Service managing lecture schedules, 7-day weekly timetable representations,
    and automated collision / conflict detection across rooms, teachers, and batches.
    """

    @classmethod
    def detect_conflicts(
        cls,
        teacher: TeacherProfile,
        room: str,
        class_section: ClassSection,
        day_of_week: int,
        start_time: time,
        end_time: time,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for scheduling collisions across teacher, room, and section in the same semester.
        Supports days 1 (Monday) through 7 (Sunday).
        """
        conflicts = []

        if day_of_week < 1 or day_of_week > 7:
            raise ValidationError({'day_of_week': _('Day of week must be an integer between 1 (Monday) and 7 (Sunday).')})

        if start_time >= end_time:
            raise ValidationError({'end_time': _('End time must be strictly after start time.')})

        semester = class_section.semester

        # Base query for overlapping time in the same semester and day
        base_qs = ClassSchedule.objects.filter(
            class_section__semester=semester,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).select_related('class_section__course', 'teacher__user')

        if exclude_schedule_id:
            base_qs = base_qs.exclude(pk=exclude_schedule_id)

        # 1. Check Teacher Conflict
        teacher_conflict = base_qs.filter(teacher=teacher).first()
        if teacher_conflict:
            day_name = dict(ClassSchedule.DayOfWeek.choices).get(day_of_week, f'Day {day_of_week}')
            conflicts.append({
                'type': 'TEACHER_CONFLICT',
                'message': (
                    f"Instructor '{teacher.user.get_full_name() or teacher.employee_id}' is already "
                    f"scheduled for '{teacher_conflict.class_section.course.code}' on {day_name} "
                    f"from {teacher_conflict.start_time.strftime('%H:%M')} to {teacher_conflict.end_time.strftime('%H:%M')}."
                ),
                'conflicting_schedule_id': teacher_conflict.pk
            })

        # 2. Check Room Conflict
        if room:
            room_conflict = base_qs.filter(room__iexact=room.strip()).first()
            if room_conflict:
                day_name = dict(ClassSchedule.DayOfWeek.choices).get(day_of_week, f'Day {day_of_week}')
                conflicts.append({
                    'type': 'ROOM_CONFLICT',
                    'message': (
                        f"Room / Lab '{room}' is already booked by '{room_conflict.class_section.course.code}' "
                        f"on {day_name} from {room_conflict.start_time.strftime('%H:%M')} to {room_conflict.end_time.strftime('%H:%M')}."
                    ),
                    'conflicting_schedule_id': room_conflict.pk
                })

        # 3. Check Class Section Conflict
        section_conflict = base_qs.filter(class_section=class_section).first()
        if section_conflict:
            day_name = dict(ClassSchedule.DayOfWeek.choices).get(day_of_week, f'Day {day_of_week}')
            conflicts.append({
                'type': 'SECTION_CONFLICT',
                'message': (
                    f"Class section '{class_section}' already has a lecture scheduled "
                    f"on {day_name} from {section_conflict.start_time.strftime('%H:%M')} to {section_conflict.end_time.strftime('%H:%M')}."
                ),
                'conflicting_schedule_id': section_conflict.pk
            })

        return conflicts

    @classmethod
    @transaction.atomic
    def create_schedule_entry(
        cls,
        class_section: ClassSection,
        teacher: TeacherProfile,
        day_of_week: int,
        start_time: time,
        end_time: time,
        room: str
    ) -> ClassSchedule:
        """
        Create a new schedule entry after enforcing conflict validations.
        """
        conflicts = cls.detect_conflicts(
            teacher=teacher,
            room=room,
            class_section=class_section,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time
        )
        if conflicts:
            error_messages = [c['message'] for c in conflicts]
            raise ValidationError({'schedule': error_messages})

        entry = ClassSchedule.objects.create(
            class_section=class_section,
            teacher=teacher,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            room=room.strip()
        )
        return entry

    @classmethod
    def get_student_weekly_timetable(cls, student: StudentProfile, semester: Optional[Semester] = None):
        """
        Return the 7-day schedule grid for all courses the student is actively enrolled in.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        enrolled_sections = Enrollment.objects.filter(
            student=student,
            status=Enrollment.EnrollmentStatus.ENROLLED
        )
        if semester:
            enrolled_sections = enrolled_sections.filter(class_section__semester=semester)

        section_ids = enrolled_sections.values_list('class_section_id', flat=True)

        return ClassSchedule.objects.filter(
            class_section_id__in=section_ids
        ).select_related(
            'class_section__course',
            'class_section__semester',
            'teacher__user'
        ).order_by('day_of_week', 'start_time')

    @classmethod
    def get_teacher_weekly_timetable(cls, teacher: TeacherProfile, semester: Optional[Semester] = None):
        """
        Return the 7-day teaching schedule grid for a faculty member.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        qs = ClassSchedule.objects.filter(teacher=teacher).select_related(
            'class_section__course',
            'class_section__semester'
        )
        if semester:
            qs = qs.filter(class_section__semester=semester)

        return qs.order_by('day_of_week', 'start_time')
