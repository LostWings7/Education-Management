"""
Administrator institutional analytics views for Phase 3.
Provides university-wide macro intelligence, department/program comparative statistics, and risk distributions.
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from apps.core.mixins import AdminRequiredMixin
from apps.academic.models import Department, Program, Semester, StudentProfile, ClassSection, Enrollment
from apps.analytics.schemas.insight import RiskLevel
from apps.analytics.services import (
    PerformanceAnalyticsService,
    AttendanceAnalyticsService,
    RiskEngineService,
    AnomalyDetectionService
)


class AdminInstitutionAnalyticsView(AdminRequiredMixin, TemplateView):
    """
    Macro-level institutional analytics overview for administrators.
    """
    template_name = 'portal/admin/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_semester = Semester.objects.filter(is_active=True).first()

        students = list(StudentProfile.objects.filter(
            academic_status=StudentProfile.AcademicStatus.ACTIVE
        ).select_related('department', 'program', 'user'))

        total_students = len(students)

        # 1. Macro Risk Distribution
        risk_counts = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.CRITICAL: 0
        }

        all_gpas = []
        all_att_pcts = []
        critical_students = []
        anomaly_count = 0

        for s in students:
            risk = RiskEngineService.evaluate_overall_risk(s, active_semester)
            if risk.risk_level in risk_counts:
                risk_counts[risk.risk_level] += 1

            if risk.risk_level == RiskLevel.CRITICAL:
                critical_students.append({'student': s, 'risk': risk})

            gpa_res = PerformanceAnalyticsService.calculate_overall_gpa(s, active_semester)
            if gpa_res['term_average_percentage'] is not None:
                all_gpas.append(gpa_res['term_average_percentage'])

            att_res = AttendanceAnalyticsService.calculate_overall_attendance(s, active_semester)
            if att_res.data_quality != 'INSUFFICIENT_DATA':
                all_att_pcts.append(att_res.attendance_percentage)

            # Check course anomalies
            for enr in s.enrollments.filter(class_section__semester=active_semester):
                ano = AnomalyDetectionService.detect_course_anomaly(s, enr.class_section)
                if ano.is_anomaly:
                    anomaly_count += 1

        institution_avg_gpa = round(sum(all_gpas) / len(all_gpas), 1) if all_gpas else None
        institution_avg_att = round(sum(all_att_pcts) / len(all_att_pcts), 1) if all_att_pcts else None

        # 2. Department-level Breakdown
        departments = Department.objects.filter(is_active=True)
        dept_summary = []
        for d in departments:
            dept_students = [s for s in students if s.department_id == d.pk]
            d_count = len(dept_students)

            d_gpas = []
            d_atts = []
            d_high_risk = 0

            for ds in dept_students:
                r = RiskEngineService.evaluate_overall_risk(ds, active_semester)
                if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    d_high_risk += 1
                g = PerformanceAnalyticsService.calculate_overall_gpa(ds, active_semester)
                if g['term_average_percentage'] is not None:
                    d_gpas.append(g['term_average_percentage'])
                at = AttendanceAnalyticsService.calculate_overall_attendance(ds, active_semester)
                if at.data_quality != 'INSUFFICIENT_DATA':
                    d_atts.append(at.attendance_percentage)

            dept_summary.append({
                'department': d,
                'student_count': d_count,
                'avg_gpa': round(sum(d_gpas) / len(d_gpas), 1) if d_gpas else None,
                'avg_attendance': round(sum(d_atts) / len(d_atts), 1) if d_atts else None,
                'at_risk_count': d_high_risk,
                'at_risk_pct': round((d_high_risk / d_count) * 100.0, 1) if d_count > 0 else 0.0
            })

        context.update({
            'semester': active_semester,
            'total_students': total_students,
            'institution_avg_gpa': institution_avg_gpa,
            'institution_avg_att': institution_avg_att,
            'risk_counts': risk_counts,
            'critical_students': critical_students,
            'anomaly_count': anomaly_count,
            'dept_summary': dept_summary,
        })
        return context
