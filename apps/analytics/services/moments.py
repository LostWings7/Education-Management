"""
Academic Moments & Dignified Milestones Service for Phase 7.
Identifies meaningful academic milestones based on institutional thresholds without trivial gamification.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.conf import settings
from apps.academic.models import StudentProfile, Semester
from apps.interventions.models import Intervention
from .attendance import AttendanceAnalyticsService
from .topic_analysis import TopicAnalyticsService
from .trends import TrendAnalyticsService


class AcademicMomentsService:
    """
    Evaluates dignified, positive academic accomplishments for students.
    """

    # Configurable Institutional Thresholds
    DISTINCTION_GPA_THRESHOLD = getattr(settings, 'ACADEMIC_DISTINCTION_GPA', 3.80)
    ATTENDANCE_STANDARD_THRESHOLD = getattr(settings, 'ACADEMIC_ATTENDANCE_STANDARD', 75.0)
    TOPIC_MASTERY_THRESHOLD = getattr(settings, 'ACADEMIC_TOPIC_MASTERY_THRESHOLD', 85.0)

    @classmethod
    def get_student_moments(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify active positive milestones for a student.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        moments: List[Dict[str, Any]] = []

        # 1. Academic Distinction Standing
        from apps.portal.reporting import TranscriptService
        transcript = TranscriptService.get_student_transcript(student)
        cgpa = transcript.get('cumulative_gpa')
        if cgpa is not None and cgpa >= cls.DISTINCTION_GPA_THRESHOLD:
            moments.append({
                'id': f"moment_distinction_{student.pk}",
                'moment_type': 'DISTINCTION_ACHIEVED',
                'badge_class': 'badge-success',
                'title': 'Academic Distinction Standing',
                'description': f"Maintaining a Cumulative GPA of {cgpa:.2f} (Threshold: {cls.DISTINCTION_GPA_THRESHOLD:.2f}).",
                'icon': 'award'
            })

        # 2. Positive Attendance Standard Maintenance
        enrollments = student.enrollments.filter(class_section__semester=semester, status='ENROLLED')
        for enr in enrollments:
            section = enr.class_section
            att_res = AttendanceAnalyticsService.calculate_course_attendance(student, section)
            if att_res and att_res.attendance_percentage >= cls.ATTENDANCE_STANDARD_THRESHOLD and att_res.total_conducted >= 5:
                moments.append({
                    'id': f"moment_att_{section.pk}",
                    'moment_type': 'ATTENDANCE_STANDARD_MAINTAINED',
                    'badge_class': 'badge-info',
                    'title': f"Exemplary Attendance ({section.course.code})",
                    'description': f"Achieving {att_res.attendance_percentage:.1f}% attendance with a positive buffer of {att_res.absence_buffer} session(s).",
                    'icon': 'calendar-check'
                })

            # 3. Topic Syllabus Mastery
            topics_mastery = TopicAnalyticsService.calculate_topic_mastery(student, section)
            for t in topics_mastery:
                score_pct = t.get('score_percentage')
                if score_pct is not None and score_pct >= cls.TOPIC_MASTERY_THRESHOLD:
                    moments.append({
                        'id': f"moment_top_{t['topic_id']}",
                        'moment_type': 'TOPIC_MASTERY_ACHIEVED',
                        'badge_class': 'badge-primary',
                        'title': f"Topic Mastery: {t['topic_title']}",
                        'description': f"Demonstrated high topic comprehension ({score_pct:.1f}%) in {section.course.code}.",
                        'icon': 'check-circle'
                    })

        # 4. Resolved Support Plans
        resolved_intvs = Intervention.objects.filter(
            student=student,
            status=Intervention.Status.EFFECTIVE
        )
        for iv in resolved_intvs:
            moments.append({
                'id': f"moment_intv_{iv.pk}",
                'moment_type': 'INTERVENTION_RESOLVED',
                'badge_class': 'badge-success',
                'title': f"Support Plan Completed: {iv.course.code}",
                'description': f"Successfully achieved recovery targets for '{iv.title}'.",
                'icon': 'shield-check'
            })

        return moments
