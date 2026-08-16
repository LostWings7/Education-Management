"""
Academic Lifecycle Timeline Service.
Chronologically compiles authentic historical events across enrollment, coursework,
risk detection, intervention milestones, and grade publications.
Never fabricates events.
"""

from typing import Dict, Any, List
from datetime import datetime
from apps.academic.models import (
    StudentProfile,
    Enrollment,
    AssignmentSubmission,
    AssessmentResult,
    ClassSession,
    AttendanceRecord
)
from apps.interventions.models import (
    Intervention,
    InterventionCheckpoint
)


class AcademicTimelineService:
    """
    Constructs an evidence-backed chronological student journey.
    """

    @classmethod
    def get_student_timeline(cls, student: StudentProfile) -> List[Dict[str, Any]]:
        """
        Compiles all authentic lifecycle events for the student sorted newest first.
        """
        events: List[Dict[str, Any]] = []

        # 1. Enrollments
        enrs = Enrollment.objects.filter(student=student).select_related('class_section__course', 'class_section__semester')
        for enr in enrs:
            events.append({
                'timestamp': enr.created_at,
                'event_type': 'ENROLLMENT',
                'badge_class': 'badge-info',
                'title': f"Enrolled in {enr.class_section.course.code}",
                'description': f"Active enrollment confirmed in {enr.class_section.course.title} (Sec {enr.class_section.section_code}) for {enr.class_section.semester.name}.",
                'course_code': enr.class_section.course.code,
                'is_actionable': False
            })

            if enr.is_grade_published and enr.published_at:
                events.append({
                    'timestamp': enr.published_at,
                    'event_type': 'GRADE_PUBLISHED',
                    'badge_class': 'badge-success',
                    'title': f"Final Grade Published: {enr.class_section.course.code}",
                    'description': f"Official final grade published: {enr.final_grade_letter} ({enr.final_percentage}%).",
                    'course_code': enr.class_section.course.code,
                    'is_actionable': False
                })

        # 2. Assignment Submissions
        subs = AssignmentSubmission.objects.filter(student=student).select_related('assignment__class_section__course')
        for s in subs:
            events.append({
                'timestamp': s.submission_date,
                'event_type': 'SUBMISSION',
                'badge_class': 'badge-neutral',
                'title': f"Coursework Submitted: {s.assignment.title}",
                'description': f"Submitted for {s.assignment.class_section.course.code}. Status: {s.get_status_display()}.",
                'course_code': s.assignment.class_section.course.code,
                'is_actionable': False
            })

        # 3. Assessment Results
        results = AssessmentResult.objects.filter(student=student).select_related('assessment__class_section__course')
        for r in results:
            events.append({
                'timestamp': r.created_at,
                'event_type': 'ASSESSMENT_SCORED',
                'badge_class': 'badge-info',
                'title': f"Assessment Scored: {r.assessment.title}",
                'description': f"Scored {r.marks_obtained}/{r.assessment.max_marks} ({r.percentage:.1f}%) in {r.assessment.class_section.course.code}.",
                'course_code': r.assessment.class_section.course.code,
                'is_actionable': False
            })

        # 4. Interventions & Checkpoints
        intvs = Intervention.objects.filter(student=student).select_related('course', 'assigned_to__user')
        for iv in intvs:
            events.append({
                'timestamp': iv.created_at,
                'event_type': 'INTERVENTION_ASSIGNED',
                'badge_class': 'badge-warning',
                'title': f"Support Plan Assigned: {iv.title}",
                'description': f"Targeted support plan in {iv.course.code} assigned by faculty. Objective: {iv.objective}.",
                'course_code': iv.course.code,
                'link_url': f"/portal/student/interventions/{iv.pk}/",
                'is_actionable': True
            })

            for cp in iv.evaluations.all():
                events.append({
                    'timestamp': cp.created_at,
                    'event_type': 'CHECKPOINT_RECORDED',
                    'badge_class': 'badge-neutral',
                    'title': f"Support Evaluation #{cp.checkpoint_number}: {iv.course.code}",
                    'description': f"Progress: {cp.progress_percentage}%. {cp.evaluation_notes}",
                    'course_code': iv.course.code,
                    'link_url': f"/portal/student/interventions/{iv.pk}/",
                    'is_actionable': False
                })

            if iv.status in ['EFFECTIVE', 'COMPLETED', 'CLOSED']:
                events.append({
                    'timestamp': iv.updated_at,
                    'event_type': 'INTERVENTION_RESOLVED',
                    'badge_class': 'badge-success',
                    'title': f"Support Outcome Resolved: {iv.title}",
                    'description': f"Support plan successfully evaluated with status: {iv.get_status_display()}.",
                    'course_code': iv.course.code,
                    'link_url': f"/portal/student/interventions/{iv.pk}/",
                    'is_actionable': False
                })

        # Sort newest first
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return events
