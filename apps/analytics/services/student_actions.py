"""
Deterministic Student Action Prioritization Service for Phase 7 Academic Command Center.
Normalizes all metrics to a common 0.0 - 100.0 scale and ranks actionable tasks deterministically.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.urls import reverse

from apps.academic.models import (
    StudentProfile,
    ClassSection,
    Assignment,
    AssignmentSubmission,
    Assessment,
    Semester
)
from apps.interventions.models import Intervention, InterventionAction
from .risk_engine import RiskEngineService
from .attendance import AttendanceAnalyticsService
from .topic_analysis import TopicAnalyticsService
from .trends import TrendAnalyticsService


class StudentActionPriorityService:
    """
    Deterministic prioritization engine for student daily action queues.
    Formula:
      PriorityScore = 0.45 * Urgency + 0.35 * Risk + 0.20 * Impact
    All sub-scores are strictly normalized to 0.0 - 100.0 before weight application.
    """

    WEIGHT_URGENCY = 0.45
    WEIGHT_RISK = 0.35
    WEIGHT_IMPACT = 0.20

    # Priority Classification Thresholds
    THRESHOLD_URGENT = 70.0
    THRESHOLD_HIGH = 50.0
    THRESHOLD_RECOMMENDED = 30.0

    @classmethod
    def get_prioritized_actions(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate ranked actionable queue for a student across all active courses.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        actions: List[Dict[str, Any]] = []
        now = timezone.now()
        today = now.date()

        # Fetch active enrollments
        enrollments = student.enrollments.filter(
            class_section__semester=semester,
            status='ENROLLED'
        ).select_related('class_section__course', 'class_section__primary_teacher__user')

        for enr in enrollments:
            section = enr.class_section
            course = section.course

            # Pre-fetch course analytical context
            risk_res = RiskEngineService.evaluate_course_risk(student, section)
            course_risk_score = float(risk_res.composite_score) if risk_res else 0.0

            att_res = AttendanceAnalyticsService.calculate_course_attendance(student, section)
            att_pct = att_res.attendance_percentage if att_res else 100.0

            # -------------------------------------------------------------
            # 1. Active Intervention Action Items
            # -------------------------------------------------------------
            active_intvs = Intervention.objects.filter(
                student=student,
                class_section=section,
                status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]
            )
            for iv in active_intvs:
                pending_actions = iv.actions.filter(status=InterventionAction.ActionStatus.PENDING)
                for act in pending_actions:
                    # Urgency: Due date proximity (within 3 days = 100, 7 days = 70, none = 50)
                    if act.due_date:
                        days_left = (act.due_date - today).days
                        urgency = max(0.0, min(100.0, 100.0 - (days_left * 12.0)))
                    else:
                        urgency = 50.0

                    risk_subscore = course_risk_score
                    impact_subscore = 90.0 # Support plans have highest recovery leverage

                    score = (
                        cls.WEIGHT_URGENCY * urgency +
                        cls.WEIGHT_RISK * risk_subscore +
                        cls.WEIGHT_IMPACT * impact_subscore
                    )

                    actions.append({
                        'id': f"intv_{act.pk}",
                        'category': 'INTERVENTION_ACTION',
                        'badge_label': 'Support Plan Task',
                        'badge_class': 'badge-danger',
                        'course_code': course.code,
                        'title': act.title,
                        'description': f"Intervention step in {course.code}: {act.description or 'Complete assigned recovery task.'}",
                        'due_date': act.due_date,
                        'priority_score': round(score, 1),
                        'urgency_score': round(urgency, 1),
                        'risk_subscore': round(risk_subscore, 1),
                        'impact_subscore': round(impact_subscore, 1),
                        'priority_level': cls._classify_priority(score),
                        'action_url': reverse('portal:student_course_detail', kwargs={'section_id': section.pk}),
                        'action_label': 'Complete Action'
                    })

            # -------------------------------------------------------------
            # 2. Upcoming / Overdue Coursework Assignments
            # -------------------------------------------------------------
            assignments = Assignment.objects.filter(class_section=section)
            for assign in assignments:
                sub = student.assignment_submissions.filter(assignment=assign).first()
                if not sub or sub.status != 'SUBMITTED':
                    # Urgency based on due date
                    delta = assign.due_date - now
                    hours_left = delta.total_seconds() / 3600.0

                    if hours_left < 0:
                        urgency = 100.0 # Overdue
                        urgency_label = "OVERDUE"
                    elif hours_left <= 24:
                        urgency = 95.0
                        urgency_label = "Due Today"
                    elif hours_left <= 48:
                        urgency = 80.0
                        urgency_label = "Due Tomorrow"
                    elif hours_left <= 120: # 5 days
                        urgency = 60.0
                        urgency_label = f"Due in {int(hours_left/24)} days"
                    else:
                        urgency = 30.0
                        urgency_label = f"Due {assign.due_date.strftime('%b %d')}"

                    risk_subscore = course_risk_score
                    # Impact proportional to assignment max marks / weight
                    impact_subscore = min(100.0, float(assign.max_marks) * 0.8)

                    score = (
                        cls.WEIGHT_URGENCY * urgency +
                        cls.WEIGHT_RISK * risk_subscore +
                        cls.WEIGHT_IMPACT * impact_subscore
                    )

                    actions.append({
                        'id': f"assign_{assign.pk}",
                        'category': 'ASSIGNMENT',
                        'badge_label': 'Assignment',
                        'badge_class': 'badge-warning',
                        'course_code': course.code,
                        'title': assign.title,
                        'description': f"{course.code} Coursework — {urgency_label} (Max {assign.max_marks} marks)",
                        'due_date': assign.due_date.date(),
                        'priority_score': round(score, 1),
                        'urgency_score': round(urgency, 1),
                        'risk_subscore': round(risk_subscore, 1),
                        'impact_subscore': round(impact_subscore, 1),
                        'priority_level': cls._classify_priority(score),
                        'action_url': reverse('portal:student_assignments'),
                        'action_label': 'Submit Coursework'
                    })

            # -------------------------------------------------------------
            # 3. Attendance Deficit Mitigation
            # -------------------------------------------------------------
            if att_pct < 75.0:
                # Urgency proportional to deficit
                urgency = min(100.0, (75.0 - att_pct) * 4.0)
                risk_subscore = 100.0 if att_pct < 60.0 else 75.0
                impact_subscore = 85.0 # Attendance recovery has strong regulatory impact

                score = (
                    cls.WEIGHT_URGENCY * urgency +
                    cls.WEIGHT_RISK * risk_subscore +
                    cls.WEIGHT_IMPACT * impact_subscore
                )

                req_sessions = att_res.required_sessions if att_res else 1
                actions.append({
                    'id': f"att_{section.pk}",
                    'category': 'ATTENDANCE_RECOVERY',
                    'badge_label': 'Attendance Deficit',
                    'badge_class': 'badge-danger',
                    'course_code': course.code,
                    'title': f"Attend Upcoming {course.code} Lectures",
                    'description': f"Current attendance is {att_pct:.1f}%. Attend next {req_sessions} consecutive session(s) to restore $\\ge 75\\%$.",
                    'due_date': today + timedelta(days=1),
                    'priority_score': round(score, 1),
                    'urgency_score': round(urgency, 1),
                    'risk_subscore': round(risk_subscore, 1),
                    'impact_subscore': round(impact_subscore, 1),
                    'priority_level': cls._classify_priority(score),
                    'action_url': reverse('portal:student_attendance'),
                    'action_label': 'View Timetable'
                })

            # -------------------------------------------------------------
            # 4. Weak Syllabus Topic Remediation (<60% Mastery)
            # -------------------------------------------------------------
            topics_mastery = TopicAnalyticsService.calculate_topic_mastery(student, section)
            for t in topics_mastery:
                score_pct = t.get('score_percentage')
                if score_pct is not None and score_pct < 60.0:
                    urgency = 50.0
                    risk_subscore = course_risk_score
                    impact_subscore = 75.0

                    score = (
                        cls.WEIGHT_URGENCY * urgency +
                        cls.WEIGHT_RISK * risk_subscore +
                        cls.WEIGHT_IMPACT * impact_subscore
                    )

                    actions.append({
                        'id': f"topic_{t['topic_id']}",
                        'category': 'TOPIC_REMEDIATION',
                        'badge_label': 'Topic Mastery Gap',
                        'badge_class': 'badge-info',
                        'course_code': course.code,
                        'title': f"Review Topic: {t['topic_title']}",
                        'description': f"Observed mastery is {score_pct:.1f}%. Review lecture slides & practice problems.",
                        'due_date': today + timedelta(days=3),
                        'priority_score': round(score, 1),
                        'urgency_score': round(urgency, 1),
                        'risk_subscore': round(risk_subscore, 1),
                        'impact_subscore': round(impact_subscore, 1),
                        'priority_level': cls._classify_priority(score),
                        'action_url': reverse('portal:student_resources'),
                        'action_label': 'Study Resources'
                    })

        # Sort descending by priority_score
        actions.sort(key=lambda x: x['priority_score'], reverse=True)
        return actions[:limit]

    @classmethod
    def _classify_priority(cls, score: float) -> str:
        if score >= cls.THRESHOLD_URGENT:
            return 'URGENT'
        elif score >= cls.THRESHOLD_HIGH:
            return 'HIGH'
        elif score >= cls.THRESHOLD_RECOMMENDED:
            return 'RECOMMENDED'
        return 'NORMAL'
