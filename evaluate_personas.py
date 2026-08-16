"""
Evaluates all 7 seeded student personas against the Phase 3 Deterministic Analytics Engine.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.academic.models import StudentProfile, Semester
from apps.analytics.services import (
    PerformanceAnalyticsService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    TrendAnalyticsService,
    RiskEngineService,
    AnomalyDetectionService,
    TopicAnalyticsService,
    EarlyWarningService
)

active_semester = Semester.objects.filter(is_active=True).first()
students = StudentProfile.objects.all().order_by('student_id')

print("=" * 80)
print(f"PHASE 3 DETERMINISTIC ANALYTICS PERSONA EVALUATION ({active_semester})")
print("=" * 80)

for s in students:
    user = s.user
    enr = s.enrollments.filter(class_section__semester=active_semester).first()
    sec = enr.class_section if enr else None

    # Overall Metrics
    gpa = PerformanceAnalyticsService.calculate_overall_gpa(s, active_semester)
    att = AttendanceAnalyticsService.calculate_overall_attendance(s, active_semester)
    assign = AssignmentAnalyticsService.calculate_overall_assignments(s, active_semester)
    trend = TrendAnalyticsService.calculate_overall_trajectory(s, active_semester)
    risk = RiskEngineService.evaluate_overall_risk(s, active_semester)

    # Course specific anomaly & early warnings
    anomaly = AnomalyDetectionService.detect_course_anomaly(s, sec) if sec else None
    warnings = EarlyWarningService.scan_course_signals(s, sec) if sec else []

    print(f"\n[{s.student_id}] {user.get_full_name()} ({user.email})")
    print(f"  • Course Grade   : {gpa['term_average_percentage']}% (GPA: {gpa['term_gpa_4']}/4.0)")
    print(f"  • Attendance     : {att.attendance_percentage}% (Buffer: {att.absence_buffer} classes, Required: {att.required_sessions}, Recovery: {att.is_recovery_possible})")
    print(f"  • Assignments    : Completion {assign.completion_rate}%, Missing Rate {assign.missing_rate}%, Discordance: {assign.discordance_flag}")
    print(f"  • Trajectory     : {trend.direction} (Slope: {trend.slope} pts/step, Scores: {trend.scores_sequence})")
    print(f"  • Academic Risk  : {risk.risk_level} (Score: {risk.composite_score}/100, Confidence: {risk.data_confidence})")
    print(f"  • Sub-risks      : Att={risk.attendance_risk}, Perf={risk.performance_risk}, Trend={risk.trend_risk}, Assign={risk.assignment_risk}, Hist={risk.historical_risk}")
    if risk.escalations_applied:
        print(f"  • Escalations    : {risk.escalations_applied}")
    if anomaly and anomaly.is_anomaly:
        print(f"  • ANOMALY        : {anomaly.anomaly_type} (Z = {anomaly.z_score}, Drop = {anomaly.delta} pts)")
    if warnings:
        print(f"  • Early Warnings : {[w.title for w in warnings]}")

print("\n" + "=" * 80)
