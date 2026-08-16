"""
Student-facing analytics views for Phase 3.
Provides academic health overview, topic mastery diagnostics, risk radar, and interactive What-If simulations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.contrib import messages
from apps.core.mixins import StudentRequiredMixin
from apps.academic.models import StudentProfile, ClassSection, Enrollment, Semester
from apps.analytics.services import (
    PerformanceAnalyticsService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    TrendAnalyticsService,
    TopicAnalyticsService,
    ClassRelativeAnalyticsService,
    RiskEngineService,
    WhatIfSimulationService,
    EarlyWarningService,
    AnomalyDetectionService
)


class StudentAnalyticsOverviewView(StudentRequiredMixin, TemplateView):
    """
    Primary academic intelligence dashboard for students.
    """
    template_name = 'portal/student/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student: StudentProfile = self.request.user.student_profile
        semester = Semester.objects.filter(is_active=True).first()

        # 1. Overall Intelligence Metrics
        overall_gpa = PerformanceAnalyticsService.calculate_overall_gpa(student, semester)
        overall_att = AttendanceAnalyticsService.calculate_overall_attendance(student, semester)
        overall_assign = AssignmentAnalyticsService.calculate_overall_assignments(student, semester)
        overall_risk = RiskEngineService.evaluate_overall_risk(student, semester)
        overall_trend = TrendAnalyticsService.calculate_overall_trajectory(student, semester)

        # 2. Per-Course Breakdown Cards
        enrollments = Enrollment.objects.filter(
            student=student,
            class_section__semester=semester
        ).select_related('class_section__course', 'class_section__primary_teacher__user')

        courses_analytics = []
        for enr in enrollments:
            sec = enr.class_section
            c_perf = PerformanceAnalyticsService.calculate_course_performance(student, sec)
            c_att = AttendanceAnalyticsService.calculate_course_attendance(student, sec)
            c_trend = TrendAnalyticsService.calculate_course_trajectory(student, sec)
            c_assign = AssignmentAnalyticsService.calculate_course_assignments(student, sec)
            c_risk = RiskEngineService.evaluate_course_risk(student, sec)
            c_topics = TopicAnalyticsService.calculate_topic_mastery(student, sec)
            c_anomaly = AnomalyDetectionService.detect_course_anomaly(student, sec)

            courses_analytics.append({
                'enrollment': enr,
                'section': sec,
                'performance': c_perf,
                'attendance': c_att,
                'trend': c_trend,
                'assignments': c_assign,
                'risk': c_risk,
                'topics': c_topics,
                'anomaly': c_anomaly
            })

        context.update({
            'student': student,
            'semester': semester,
            'overall_gpa': overall_gpa,
            'overall_att': overall_att,
            'overall_assign': overall_assign,
            'overall_risk': overall_risk,
            'overall_trend': overall_trend,
            'courses_analytics': courses_analytics,
        })
        return context


class StudentWhatIfSimulatorView(StudentRequiredMixin, View):
    """
    Interactive What-If simulation studio for students.
    """
    template_name = 'portal/student/what_if.html'

    def get(self, request):
        student: StudentProfile = request.user.student_profile
        semester = Semester.objects.filter(is_active=True).first()
        enrollments = Enrollment.objects.filter(
            student=student,
            class_section__semester=semester
        ).select_related('class_section__course')

        selected_section_id = request.GET.get('section_id')
        selected_section = None
        if selected_section_id:
            selected_section = ClassSection.objects.filter(pk=selected_section_id).first()
        if not selected_section and enrollments.exists():
            selected_section = enrollments.first().class_section

        simulation_result = None
        target_result = None

        if selected_section:
            # Baseline values
            perf = PerformanceAnalyticsService.calculate_course_performance(student, selected_section)
            att = AttendanceAnalyticsService.calculate_course_attendance(student, selected_section)

            # Check if simulation parameters submitted via GET
            hypo_score_str = request.GET.get('hypo_score')
            hypo_weight_str = request.GET.get('hypo_weight', '20.0')
            if hypo_score_str:
                try:
                    hypo_score = float(hypo_score_str)
                    hypo_weight = float(hypo_weight_str)
                    simulation_result = WhatIfSimulationService.simulate_next_assessment(
                        student, selected_section, hypo_score, hypo_weight
                    )
                except ValueError:
                    pass

            target_grade_str = request.GET.get('target_grade')
            if target_grade_str:
                try:
                    target_grade = float(target_grade_str)
                    target_result = WhatIfSimulationService.solve_required_score_for_target(
                        student, selected_section, target_grade
                    )
                except ValueError:
                    pass
        else:
            perf = None
            att = None

        return render(request, self.template_name, {
            'student': student,
            'enrollments': enrollments,
            'selected_section': selected_section,
            'performance': perf,
            'attendance': att,
            'simulation_result': simulation_result,
            'target_result': target_result,
        })
