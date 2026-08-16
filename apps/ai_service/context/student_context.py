"""
Pre-prompt Scoped Context Builder for Students.
Enforces strict student-level data isolation before context construction.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from apps.academic.models import (
    StudentProfile,
    Semester,
    Enrollment,
    Assignment,
    LearningResource,
    Assessment
)
from apps.analytics.services import (
    RiskEngineService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    PerformanceAnalyticsService,
    TrendAnalyticsService,
    TopicAnalyticsService,
    AnomalyDetectionService
)
from apps.interventions.models import Intervention
from apps.ai_service.schemas.context import StudentAIContext
from apps.ai_service.schemas.responses import FactAttribution
from .base import BaseContextBuilder


class StudentContextBuilder(BaseContextBuilder):
    """
    Constructs authorized, pre-scoped academic context for the student.
    """

    @classmethod
    def build_context(cls, student: StudentProfile, semester: Optional[Semester] = None) -> StudentAIContext:
        """
        Builds full structured context and Fact Registry for the student.
        """
        if not semester:
            semester = Semester.objects.filter(is_active=True).first()

        enrollments = list(Enrollment.objects.select_related(
            'class_section__course',
            'class_section__primary_teacher__user',
            'class_section__semester'
        ).filter(
            student=student,
            class_section__semester=semester,
            status=Enrollment.EnrollmentStatus.ENROLLED
        ))

        fact_registry: List[FactAttribution] = []
        enrolled_courses = []
        topic_diagnostics = []
        all_pending_assignments = []
        all_learning_resources = []
        anomalies_list = []
        risk_summary = {}
        trajectory_summary = {}

        total_attendance_pcts = []
        total_buffers = []

        # Iterate through student's enrolled courses
        for enr in enrollments:
            sec = enr.class_section
            course = sec.course

            enrolled_courses.append({
                'course_id': course.pk,
                'course_code': course.code,
                'course_title': course.title,
                'section_code': sec.section_code,
                'teacher_name': sec.primary_teacher.user.get_full_name() if sec.primary_teacher else "Faculty Instructor",
                'current_grade': enr.final_grade_letter or "In Progress",
                'current_score': float(enr.final_percentage) if enr.final_percentage is not None else None
            })

            # Attendance Analytics
            att_res = AttendanceAnalyticsService.calculate_course_attendance(student, sec)
            if att_res:
                total_attendance_pcts.append(att_res.attendance_percentage)
                total_buffers.append(att_res.absence_buffer)
                fact_registry.append(cls.create_fact_attribution(
                    fact_id=f"FACT-ATT-{course.code}",
                    classification="FACT",
                    metric_name=f"{course.code} Attendance",
                    value=f"{att_res.attendance_percentage}%",
                    source_service="AttendanceAnalyticsService",
                    course_code=course.code
                ))
                fact_registry.append(cls.create_fact_attribution(
                    fact_id=f"CALC-BUF-{course.code}",
                    classification="CALCULATION",
                    metric_name=f"{course.code} Absence Buffer",
                    value=att_res.absence_buffer,
                    source_service="AttendanceAnalyticsService",
                    course_code=course.code
                ))

            # Risk Engine Analytics
            risk_res = RiskEngineService.evaluate_course_risk(student, sec)
            if risk_res and not risk_summary:
                risk_summary = {
                    'composite_score': risk_res.composite_score,
                    'risk_level': risk_res.risk_level,
                    'contributing_factors': [f.get('factor', str(f)) if isinstance(f, dict) else str(f) for f in risk_res.contributing_factors],
                    'attendance_risk': risk_res.attendance_risk,
                    'performance_risk': risk_res.performance_risk,
                    'coursework_risk': risk_res.assignment_risk,
                    'trend_risk': risk_res.trend_risk
                }
                fact_registry.append(cls.create_fact_attribution(
                    fact_id="CALC-RISK-COMPOSITE",
                    classification="CALCULATION",
                    metric_name="Composite Risk Score",
                    value=f"{risk_res.composite_score}/100 ({risk_res.risk_level})",
                    source_service="RiskEngineService",
                    course_code=course.code
                ))

            # Trajectory Analytics
            trend_res = TrendAnalyticsService.calculate_course_trajectory(student, sec)
            if trend_res and not trajectory_summary:
                trajectory_summary = {
                    'direction': trend_res.direction,
                    'slope': trend_res.slope,
                    'is_improving': trend_res.direction == 'IMPROVING',
                    'is_declining': trend_res.direction == 'DECLINING'
                }
                fact_registry.append(cls.create_fact_attribution(
                    fact_id="CALC-TREND-SLOPE",
                    classification="CALCULATION",
                    metric_name="Trajectory Slope",
                    value=f"{trend_res.slope} pts/step ({trend_res.direction})",
                    source_service="TrendAnalyticsService",
                    course_code=course.code
                ))

            # Anomaly Analytics
            anom_res = AnomalyDetectionService.detect_course_anomaly(student, sec)
            if anom_res and anom_res.is_anomaly:
                anomalies_list.append({
                    'course_code': course.code,
                    'anomaly_type': anom_res.anomaly_type,
                    'severity': anom_res.severity,
                    'description': anom_res.summary,
                    'score_drop': anom_res.delta,
                    'z_score': anom_res.z_score
                })
                fact_registry.append(cls.create_fact_attribution(
                    fact_id=f"CALC-ANOM-{course.code}",
                    classification="CALCULATION",
                    metric_name=f"{course.code} Acute Drop Anomaly",
                    value=f"Drop of {anom_res.delta} pts (Z = {anom_res.z_score})",
                    source_service="AnomalyDetectionService",
                    course_code=course.code
                ))

            # Topic Diagnostics
            top_list = TopicAnalyticsService.calculate_topic_mastery(student, sec)
            for t in top_list:
                topic_diagnostics.append({
                    'course_code': course.code,
                    'topic_id': t.get('topic_id'),
                    'title': t.get('title'),
                    'score_percentage': t.get('score_percentage'),
                    'status': t.get('status'),
                    'status_label': t.get('status_label')
                })

            # Pending Assignments
            assign_res = AssignmentAnalyticsService.calculate_course_assignments(student, sec)
            assignments = Assignment.objects.filter(class_section=sec).order_by('due_date')
            for a in assignments:
                sub = student.submissions.filter(assignment=a).first()
                if not sub or sub.status != 'SUBMITTED':
                    all_pending_assignments.append({
                        'id': a.pk,
                        'course_code': course.code,
                        'title': a.title,
                        'due_date': str(a.due_date),
                        'max_marks': float(a.max_marks),
                        'is_overdue': a.is_overdue
                    })

            # Learning Resources
            res_qs = LearningResource.objects.filter(course=course, is_published=True)
            for r in res_qs:
                all_learning_resources.append({
                    'id': r.pk,
                    'course_code': course.code,
                    'topic_id': r.topic_id,
                    'title': r.title,
                    'resource_type': r.get_resource_type_display(),
                    'external_url': r.external_url,
                    'has_file': bool(r.file)
                })

        # Phase 4 Interventions
        active_intvs = list(Intervention.objects.filter(
            student=student,
            status__in=['RECOMMENDED', 'APPROVED', 'ASSIGNED', 'IN_PROGRESS']
        ).select_related('course', 'assigned_to__user').prefetch_related('actions'))

        interventions_payload = []
        for iv in active_intvs:
            act_payload = []
            for act in iv.actions.all():
                act_payload.append({
                    'action_id': act.pk,
                    'order_index': act.order_index,
                    'title': act.title,
                    'description': act.description,
                    'status': act.status,
                    'verification_type': act.verification_type
                })
            interventions_payload.append({
                'id': iv.pk,
                'title': iv.title,
                'course_code': iv.course.code,
                'category': iv.get_category_display(),
                'priority': iv.get_priority_display(),
                'primary_target_metric': iv.get_primary_target_metric_display(),
                'objective': iv.objective,
                'due_date': str(iv.due_date),
                'status': iv.status,
                'supervisor_name': iv.assigned_to.user.get_full_name() if iv.assigned_to else "Advisor",
                'actions': act_payload
            })
            fact_registry.append(cls.create_fact_attribution(
                fact_id=f"ACTION-INTV-{iv.pk}",
                classification="ACTION",
                metric_name=f"Support Plan: {iv.title}",
                value=f"Status: {iv.status}, Priority: {iv.priority}",
                source_service="InterventionService",
                course_code=iv.course.code
            ))

        avg_att = round(sum(total_attendance_pcts) / len(total_attendance_pcts), 1) if total_attendance_pcts else 100.0
        min_buf = min(total_buffers) if total_buffers else 0

        attendance_summary = {
            'overall_percentage': avg_att,
            'absence_buffer': min_buf
        }

        coursework_summary = {
            'pending_assignments_count': len(all_pending_assignments),
            'pending_assignments': all_pending_assignments[:10]
        }

        return StudentAIContext(
            student_id=student.student_id,
            student_name=student.user.get_full_name() or student.user.email,
            program_name=student.program.name if student.program else "Academic Program",
            department_name=student.department.name if student.department else "Department",
            semester_name=semester.name if semester else "Current Semester",
            enrolled_courses=enrolled_courses,
            attendance_summary=attendance_summary,
            coursework_summary=coursework_summary,
            risk_summary=risk_summary,
            trajectory_summary=trajectory_summary,
            anomalies=anomalies_list,
            topic_diagnostics=topic_diagnostics,
            active_interventions=interventions_payload,
            learning_resources=all_learning_resources,
            fact_registry=fact_registry
        )
