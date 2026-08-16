"""
Authorized Deterministic Tool Execution Layer.
Enforces strict user-level authorization before delegating to deterministic academic engines.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.core.exceptions import PermissionDenied
from apps.core.models import User
from apps.academic.models import (
    StudentProfile,
    TeacherProfile,
    ClassSection,
    Enrollment,
    Course,
    Topic,
    LearningResource
)
from apps.analytics.services import (
    WhatIfSimulationService,
    AttendanceAnalyticsService,
    TopicAnalyticsService,
    RiskEngineService,
    PerformanceAnalyticsService
)
from apps.interventions.models import Intervention


class AuthorizedToolsService:
    """
    Executes deterministic service calls on behalf of the AI assistant with role enforcement.
    """

    @classmethod
    def execute_tool(
        cls,
        tool_name: str,
        arguments: Dict[str, Any],
        user: User
    ) -> Dict[str, Any]:
        """
        Main tool dispatcher enforcing user authorization.
        """
        # 1. Student Tools
        if user.is_student:
            student = getattr(user, 'student_profile', None)
            if not student:
                raise PermissionDenied("Student profile not found.")

            if tool_name == 'get_my_attendance_buffer':
                return cls._student_attendance_buffer(student, arguments)
            elif tool_name == 'run_my_what_if':
                return cls._student_what_if(student, arguments)
            elif tool_name == 'get_my_topic_mastery':
                return cls._student_topic_mastery(student, arguments)
            elif tool_name == 'get_my_interventions':
                return cls._student_interventions(student)
            elif tool_name == 'get_my_performance':
                return cls._student_performance(student, arguments)
            else:
                raise PermissionDenied(f"Unknown or unauthorized tool '{tool_name}' for student.")

        # 2. Teacher Tools
        elif user.is_teacher:
            teacher = getattr(user, 'teacher_profile', None)
            if not teacher:
                raise PermissionDenied("Teacher profile not found.")

            if tool_name == 'get_section_summary':
                return cls._teacher_section_summary(teacher, arguments)
            elif tool_name == 'get_enrolled_student_analysis':
                return cls._teacher_student_analysis(teacher, arguments)
            else:
                raise PermissionDenied(f"Unknown or unauthorized tool '{tool_name}' for faculty.")

        # 3. Admin Tools
        elif user.is_administrator or user.is_superuser:
            if tool_name == 'get_department_kpis':
                return cls._admin_department_kpis(arguments)
            elif tool_name == 'get_institutional_overview':
                return cls._admin_institutional_overview()
            else:
                raise PermissionDenied(f"Unknown or unauthorized tool '{tool_name}' for administrator.")

        raise PermissionDenied("User does not have permission to execute AI tools.")

    # -------------------------------------------------------------------------
    # Student Tool Implementations
    # -------------------------------------------------------------------------

    @classmethod
    def _student_attendance_buffer(cls, student: StudentProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        course_id = args.get('course_id')
        target_pct = float(args.get('target_percentage', 75.0))
        enr = Enrollment.objects.filter(student=student, class_section__course_id=course_id, status='ENROLLED').first()
        if not enr:
            # Try by active enrollment
            enr = Enrollment.objects.filter(student=student, status='ENROLLED').first()
        if not enr:
            return {'error': 'No active enrollment found for this course.'}

        res = AttendanceAnalyticsService.calculate_course_attendance(student, enr.class_section, target_threshold=target_pct)
        return {
            'tool': 'get_my_attendance_buffer',
            'course_code': enr.class_section.course.code,
            'current_attendance_percentage': res.attendance_percentage,
            'conducted_sessions': res.total_conducted,
            'attended_credits': res.present_count + (0.5 * res.late_count),
            'remaining_sessions': res.remaining_sessions,
            'target_percentage': target_pct,
            'absence_buffer': res.absence_buffer,
            'status': 'BUFFER_AVAILABLE' if res.absence_buffer > 0 else 'NO_BUFFER'
        }

    @classmethod
    def _student_what_if(cls, student: StudentProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        course_id = args.get('course_id')
        enr = Enrollment.objects.filter(student=student, class_section__course_id=course_id, status='ENROLLED').first()
        if not enr:
            enr = Enrollment.objects.filter(student=student, status='ENROLLED').first()
        if not enr:
            return {'error': 'No active enrollment found.'}

        sec = enr.class_section
        scenarios = WhatIfSimulationService.calculate_target_scenarios(student, sec)
        return {
            'tool': 'run_my_what_if',
            'course_code': sec.course.code,
            'current_score': scenarios.current_weighted_score,
            'scenarios': [
                {
                    'target_grade': s.target_grade,
                    'required_score': s.required_remaining_score,
                    'is_feasible': s.is_feasible,
                    'feasibility_label': s.feasibility_label
                }
                for s in scenarios.scenarios
            ]
        }

    @classmethod
    def _student_topic_mastery(cls, student: StudentProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        course_id = args.get('course_id')
        enr = Enrollment.objects.filter(student=student, class_section__course_id=course_id, status='ENROLLED').first()
        if not enr:
            enr = Enrollment.objects.filter(student=student, status='ENROLLED').first()
        if not enr:
            return {'error': 'No active enrollment found.'}

        sec = enr.class_section
        topics = TopicAnalyticsService.calculate_topic_mastery(student, sec)
        return {
            'tool': 'get_my_topic_mastery',
            'course_code': sec.course.code,
            'topics': topics
        }

    @classmethod
    def _student_interventions(cls, student: StudentProfile) -> Dict[str, Any]:
        intvs = Intervention.objects.filter(student=student, status__in=['APPROVED', 'ASSIGNED', 'IN_PROGRESS']).select_related('course')
        return {
            'tool': 'get_my_interventions',
            'active_interventions': [
                {
                    'id': iv.pk,
                    'title': iv.title,
                    'course_code': iv.course.code,
                    'priority': iv.priority,
                    'objective': iv.objective,
                    'due_date': str(iv.due_date),
                    'progress_percentage': iv.action_progress_percentage
                }
                for iv in intvs
            ]
        }

    @classmethod
    def _student_performance(cls, student: StudentProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        course_id = args.get('course_id')
        enr = Enrollment.objects.filter(student=student, class_section__course_id=course_id, status='ENROLLED').first()
        if not enr:
            enr = Enrollment.objects.filter(student=student, status='ENROLLED').first()
        if not enr:
            return {'error': 'No active enrollment found.'}

        perf = PerformanceAnalyticsService.calculate_course_performance(student, enr.class_section)
        return {
            'tool': 'get_my_performance',
            'course_code': enr.class_section.course.code,
            'current_weighted_score': perf.current_weighted_score,
            'assessment_count': perf.assessment_count,
            'letter_grade': enr.final_grade_letter or 'In Progress'
        }

    # -------------------------------------------------------------------------
    # Teacher Tool Implementations
    # -------------------------------------------------------------------------

    @classmethod
    def _teacher_section_summary(cls, teacher: TeacherProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        section_id = args.get('section_id')
        sec = ClassSection.objects.filter(pk=section_id, primary_teacher=teacher).first()
        if not sec:
            raise PermissionDenied("Teacher is not assigned to this section.")

        enrs = sec.enrollments.filter(status='ENROLLED')
        return {
            'tool': 'get_section_summary',
            'course_code': sec.course.code,
            'section_code': sec.section_code,
            'enrolled_count': enrs.count()
        }

    @classmethod
    def _teacher_student_analysis(cls, teacher: TeacherProfile, args: Dict[str, Any]) -> Dict[str, Any]:
        section_id = args.get('section_id')
        student_id = args.get('student_id')
        sec = ClassSection.objects.filter(pk=section_id, primary_teacher=teacher).first()
        if not sec:
            raise PermissionDenied("Teacher is not assigned to this section.")

        enr = sec.enrollments.filter(student__student_id=student_id, status='ENROLLED').select_related('student__user').first()
        if not enr:
            raise PermissionDenied("Requested student is not enrolled in this section.")

        st = enr.student
        r_res = RiskEngineService.evaluate_course_risk(st, sec)
        att_res = AttendanceAnalyticsService.calculate_course_attendance(st, sec)

        return {
            'tool': 'get_enrolled_student_analysis',
            'student_id': st.student_id,
            'student_name': st.user.get_full_name(),
            'course_code': sec.course.code,
            'risk_level': r_res.risk_level if r_res else 'LOW',
            'risk_score': r_res.composite_score if r_res else 0.0,
            'attendance_percentage': att_res.attendance_percentage if att_res else 100.0
        }

    # -------------------------------------------------------------------------
    # Admin Tool Implementations
    # -------------------------------------------------------------------------

    @classmethod
    def _admin_department_kpis(cls, args: Dict[str, Any]) -> Dict[str, Any]:
        dept_code = args.get('department_code')
        sections = ClassSection.objects.filter(course__department__code=dept_code)
        enrs = Enrollment.objects.filter(class_section__in=sections, status='ENROLLED')
        return {
            'tool': 'get_department_kpis',
            'department_code': dept_code,
            'enrolled_students': enrs.count()
        }

    @classmethod
    def _admin_institutional_overview(cls) -> Dict[str, Any]:
        return {
            'tool': 'get_institutional_overview',
            'total_active_enrollments': Enrollment.objects.filter(status='ENROLLED').count()
        }
