"""
Teacher-facing analytics views for Phase 3.
Provides class section diagnostics, risk radar rosters, topic deficiency matrices, and early warning alerts.
"""

from django.shortcuts import render, get_object_or_404
from django.views.generic import View, TemplateView
from apps.core.mixins import TeacherRequiredMixin
from apps.academic.models import TeacherProfile, ClassSection, Enrollment
from apps.analytics.services import (
    ClassRelativeAnalyticsService,
    PerformanceAnalyticsService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    TrendAnalyticsService,
    TopicAnalyticsService,
    RiskEngineService,
    EarlyWarningService,
    AnomalyDetectionService,
    CorrelationAnalyticsService
)


class TeacherClassAnalyticsView(TeacherRequiredMixin, TemplateView):
    """
    In-depth class section analytics dashboard for instructors.
    """
    template_name = 'portal/teacher/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher: TeacherProfile = self.request.user.teacher_profile
        section_id = kwargs.get('section_id')

        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course', 'semester')
        if section_id:
            selected_section = get_object_or_404(ClassSection, pk=section_id, primary_teacher=teacher)
        else:
            selected_section = sections.first()

        if not selected_section:
            context.update({'sections': [], 'selected_section': None})
            return context

        # 1. Section Performance Distribution
        distribution = ClassRelativeAnalyticsService.calculate_section_distribution(selected_section)

        # 2. Student Roster Risk Radar Matrix
        enrollments = Enrollment.objects.filter(
            class_section=selected_section
        ).select_related('student__user', 'student__program').order_by('student__student_id')

        student_matrix = []
        for enr in enrollments:
            s = enr.student
            perf = PerformanceAnalyticsService.calculate_course_performance(s, selected_section)
            att = AttendanceAnalyticsService.calculate_course_attendance(s, selected_section)
            trend = TrendAnalyticsService.calculate_course_trajectory(s, selected_section)
            risk = RiskEngineService.evaluate_course_risk(s, selected_section)
            anomaly = AnomalyDetectionService.detect_course_anomaly(s, selected_section)

            student_matrix.append({
                'enrollment': enr,
                'student': s,
                'performance': perf,
                'attendance': att,
                'trend': trend,
                'risk': risk,
                'anomaly': anomaly
            })

        # 3. Class-wide Topic Diagnostics
        topics = selected_section.course.topics.all().order_by('order_index')
        topic_summary = []
        for t in topics:
            topic_scores = []
            for item in student_matrix:
                student_topics = TopicAnalyticsService.calculate_topic_mastery(item['student'], selected_section)
                matching = next((st for st in student_topics if st['topic_id'] == t.pk), None)
                if matching and matching['score_percentage'] is not None:
                    topic_scores.append(matching['score_percentage'])

            if topic_scores:
                avg_topic = sum(topic_scores) / len(topic_scores)
                status = "STRONG" if avg_topic >= 75.0 else ("DEVELOPING" if avg_topic >= 60.0 else "NEEDS_REVISION")
            else:
                avg_topic = None
                status = "NO_DATA"

            topic_summary.append({
                'topic': t,
                'average_score': round(avg_topic, 1) if avg_topic is not None else None,
                'status': status,
                'evaluated_students_count': len(topic_scores)
            })

        # 4. Statistical Correlation
        correlation = CorrelationAnalyticsService.calculate_attendance_vs_performance(selected_section)

        context.update({
            'sections': sections,
            'selected_section': selected_section,
            'distribution': distribution,
            'student_matrix': student_matrix,
            'topic_summary': topic_summary,
            'correlation': correlation,
        })
        return context


class TeacherEarlyWarningsView(TeacherRequiredMixin, TemplateView):
    """
    Early warning alert center for faculty covering all their assigned sections.
    """
    template_name = 'portal/teacher/early_warnings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher: TeacherProfile = self.request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course', 'semester')

        all_warnings = []
        for sec in sections:
            enrollments = Enrollment.objects.filter(class_section=sec).select_related('student__user')
            for enr in enrollments:
                student_warnings = EarlyWarningService.scan_course_signals(enr.student, sec)
                for w in student_warnings:
                    all_warnings.append({
                        'warning': w,
                        'student': enr.student,
                        'section': sec
                    })

        # Sort by severity (CRITICAL first, then DANGER, WARNING, INFO)
        severity_order = {'CRITICAL': 0, 'DANGER': 1, 'WARNING': 2, 'INFO': 3}
        all_warnings.sort(key=lambda x: severity_order.get(x['warning'].severity, 4))

        context.update({
            'sections': sections,
            'warnings_list': all_warnings,
            'critical_count': sum(1 for w in all_warnings if w['warning'].severity == 'CRITICAL'),
            'danger_count': sum(1 for w in all_warnings if w['warning'].severity == 'DANGER'),
            'warning_count': sum(1 for w in all_warnings if w['warning'].severity == 'WARNING'),
        })
        return context
