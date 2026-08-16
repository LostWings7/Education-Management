"""
Deterministic Recommendation Engine for Phase 4 Closed-Loop Academic Interventions.
Maps Phase 3 InsightObjects and analytical signals to structured, educator-reviewable recommendations.
"""

from datetime import date
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db import transaction

from apps.academic.models import (
    StudentProfile,
    ClassSection,
    Topic,
    LearningResource
)
from apps.analytics.schemas.insight import DataQuality, RiskLevel
from apps.analytics.services import (
    RiskEngineService,
    EarlyWarningService,
    AnomalyDetectionService,
    TopicAnalyticsService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    TrendAnalyticsService
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionAcknowledgement
)
from .prioritization import InterventionPrioritizationService


class InterventionRecommendationService:
    """
    Scans a student's deterministic academic performance in a class section and generates
    structured recommendations (status=RECOMMENDED) pending human educator approval.
    """

    @classmethod
    def generate_recommendations_for_student_section(
        cls,
        student: StudentProfile,
        section: ClassSection,
        creator_user
    ) -> List[Intervention]:
        """
        Evaluate academic signals and create new Intervention(status=RECOMMENDED) records.
        Applies deduplication to prevent repeated recommendations for existing active plans.
        """
        recommendations: List[Intervention] = []

        # Run Phase 3 deterministic diagnostics
        risk_res = RiskEngineService.evaluate_course_risk(student, section)
        anomaly_res = AnomalyDetectionService.detect_course_anomaly(student, section)
        att_res = AttendanceAnalyticsService.calculate_course_attendance(student, section)
        assign_res = AssignmentAnalyticsService.calculate_course_assignments(student, section)
        trend_res = TrendAnalyticsService.calculate_course_trajectory(student, section)
        topics_res = TopicAnalyticsService.calculate_topic_mastery(student, section)

        # Baseline snapshot
        baseline_snapshot = {
            'captured_at': timezone.now().isoformat(),
            'risk_score': risk_res.composite_score if risk_res else 0.0,
            'risk_level': str(risk_res.risk_level) if risk_res else 'LOW',
            'attendance_percentage': att_res.attendance_percentage if att_res else 100.0,
            'absence_buffer': att_res.absence_buffer if att_res else 0,
            'missing_assignment_rate': assign_res.missing_rate if assign_res else 0.0,
            'completion_rate': assign_res.completion_rate if assign_res else 100.0,
            'trajectory_slope': trend_res.slope if trend_res else 0.0,
            'trajectory_direction': str(trend_res.direction) if trend_res else 'STABLE',
            'engine_version': '1.0'
        }

        # 1. Trigger: Acute Performance Drop Anomaly
        if anomaly_res and anomaly_res.is_anomaly and anomaly_res.anomaly_type == 'ACUTE_DROP':
            rec = cls._create_or_skip_recommendation(
                student=student,
                section=section,
                category=Intervention.InterventionCategory.FACULTY_DIAGNOSTIC,
                target_metric=Intervention.TargetMetric.ANOMALY_RECOVERY,
                title=f"Faculty Diagnostic Review: Acute Score Plunge in {section.course.code}",
                objective=f"Diagnose the underlying cause of sudden score drop ({anomaly_res.delta} pts below baseline) and create recovery strategy.",
                trigger_type="ACUTE_PERFORMANCE_DROP",
                severity=anomaly_res.severity,
                is_anomaly=True,
                risk_score=risk_res.composite_score,
                baseline_snapshot=dict(baseline_snapshot, anomaly_delta=anomaly_res.delta, z_score=anomaly_res.z_score),
                creator_user=creator_user,
                action_templates=[
                    ("Schedule 1-on-1 Diagnostic Consultation", "Meet with student during office hours to review recent evaluation paper.", InterventionAction.VerificationType.EDUCATOR_VERIFIED),
                    ("Review Root Concept Gaps", "Analyze prerequisite concepts and syllabus topics causing difficulty.", InterventionAction.VerificationType.STUDENT_CHECK),
                    ("Attempt Practice / Diagnostic Re-assessment", "Complete a diagnostic practice quiz to verify conceptual recovery.", InterventionAction.VerificationType.STUDENT_CHECK)
                ]
            )
            if rec:
                recommendations.append(rec)

        # 2. Trigger: Attendance Deficit (Attendance < 60%)
        if att_res and att_res.data_quality != DataQuality.INSUFFICIENT_DATA and att_res.attendance_percentage < 60.0:
            rec = cls._create_or_skip_recommendation(
                student=student,
                section=section,
                category=Intervention.InterventionCategory.ATTENDANCE_RECOVERY,
                target_metric=Intervention.TargetMetric.ATTENDANCE,
                title=f"Attendance Recovery Plan: {section.course.code}",
                objective=f"Recover course attendance from current {att_res.attendance_percentage}% toward university 75.0% threshold (Required: {att_res.required_sessions} sessions).",
                trigger_type="ATTENDANCE_DEFICIT",
                severity="CRITICAL" if att_res.attendance_percentage < 50.0 else "DANGER",
                is_anomaly=False,
                risk_score=risk_res.composite_score,
                baseline_snapshot=dict(baseline_snapshot, attendance_deficit=round(75.0 - att_res.attendance_percentage, 1)),
                creator_user=creator_user,
                action_templates=[
                    ("Academic Attendance Counseling Session", "Meet with course instructor to discuss schedule conflicts and attendance obligations.", InterventionAction.VerificationType.EDUCATOR_VERIFIED),
                    (f"Attend Next 10 Consecutive Lecture Sessions", "Maintain strict unbroken attendance in upcoming scheduled class periods.", InterventionAction.VerificationType.SYSTEM_AUTOMATIC),
                    ("Weekly Attendance Verification", "Check weekly attendance log in student portal to verify accurate session recording.", InterventionAction.VerificationType.STUDENT_CHECK)
                ]
            )
            if rec:
                recommendations.append(rec)

        # 3. Trigger: Declining Trajectory or Performance Deficit
        if (trend_res and trend_res.direction == 'DECLINING' and trend_res.slope and trend_res.slope <= -5.0) or (risk_res and risk_res.performance_risk is not None and risk_res.performance_risk >= 50.0):
            rec = cls._create_or_skip_recommendation(
                student=student,
                section=section,
                category=Intervention.InterventionCategory.ACADEMIC_REMEDIAL,
                target_metric=Intervention.TargetMetric.ASSESSMENT_PERFORMANCE,
                title=f"Academic Remediation & Performance Support: {section.course.code}",
                objective="Reverse downward performance trajectory and re-establish foundational mastery.",
                trigger_type="DECLINING_TRAJECTORY",
                severity="DANGER" if trend_res and trend_res.slope and trend_res.slope <= -10.0 else "WARNING",
                is_anomaly=False,
                risk_score=risk_res.composite_score,
                baseline_snapshot=baseline_snapshot,
                creator_user=creator_user,
                action_templates=[
                    ("Comprehensive Lecture Material Review", "Revisit lecture slide decks and core reference textbooks for recent topics.", InterventionAction.VerificationType.STUDENT_CHECK),
                    ("Complete Remedial Practice Problem Set", "Work through standard practice questions and review model solutions.", InterventionAction.VerificationType.STUDENT_CHECK),
                    ("Faculty Doubt-Clearing Consultation", "Attend designated tutorial/doubt session to clarify challenging course concepts.", InterventionAction.VerificationType.EDUCATOR_VERIFIED)
                ]
            )
            if rec:
                recommendations.append(rec)

        # 4. Trigger: Missing Assignments (Missing Rate >= 50%)
        if assign_res and assign_res.data_quality != DataQuality.INSUFFICIENT_DATA and assign_res.missing_rate >= 50.0:
            rec = cls._create_or_skip_recommendation(
                student=student,
                section=section,
                category=Intervention.InterventionCategory.ASSIGNMENT_RECOVERY,
                target_metric=Intervention.TargetMetric.ASSIGNMENT_COMPLETION,
                title=f"Coursework & Assignment Catch-Up Plan: {section.course.code}",
                objective=f"Clear overdue assignment backlog (Current missing rate: {assign_res.missing_rate}%).",
                trigger_type="MISSING_ASSIGNMENTS",
                severity="DANGER" if assign_res.missing_rate >= 75.0 else "WARNING",
                is_anomaly=False,
                risk_score=risk_res.composite_score,
                baseline_snapshot=dict(baseline_snapshot, missing_assignments_count=assign_res.missing_count),
                creator_user=creator_user,
                action_templates=[
                    ("Review Assignment Guidelines & Requirements", "Review instructions for all missed/incomplete problem sets.", InterventionAction.VerificationType.STUDENT_CHECK),
                    ("Submit Completed Overdue Assignments", "Submit remaining problem sets to instructor/portal for evaluation.", InterventionAction.VerificationType.EDUCATOR_VERIFIED),
                    ("Establish Structured Weekly Study Schedule", "Allocate fixed weekly study hours to prevent future coursework submission delays.", InterventionAction.VerificationType.STUDENT_CHECK)
                ]
            )
            if rec:
                recommendations.append(rec)

        # 5. Trigger: Weak Syllabus Topic (Topic Score < 60%)
        for t_info in topics_res:
            if t_info.get('status') == 'NEEDS_ATTENTION' and t_info.get('score_percentage') is not None:
                topic_id = t_info.get('topic_id')
                topic_obj = Topic.objects.filter(pk=topic_id).first()
                if topic_obj:
                    # Find published learning resources for this topic
                    resources = list(LearningResource.objects.filter(course=section.course, topic=topic_obj, is_published=True))
                    action_templates = [
                        (f"Study Topic Notes: {topic_obj.title}", f"Review study materials and notes covering {topic_obj.title}.", InterventionAction.VerificationType.STUDENT_CHECK),
                        (f"Complete Practice Exercises: {topic_obj.title}", f"Attempt self-assessment questions for {topic_obj.title}.", InterventionAction.VerificationType.STUDENT_CHECK),
                        (f"Verify Topic Competency with Faculty", f"Discuss problem solutions for {topic_obj.title} with instructor.", InterventionAction.VerificationType.EDUCATOR_VERIFIED)
                    ]
                    rec = cls._create_or_skip_recommendation(
                        student=student,
                        section=section,
                        category=Intervention.InterventionCategory.ACADEMIC_REMEDIAL,
                        target_metric=Intervention.TargetMetric.TOPIC_MASTERY,
                        topic=topic_obj,
                        title=f"Topic Remediation: {topic_obj.title} ({section.course.code})",
                        objective=f"Master foundational concepts in '{topic_obj.title}' (Current score: {t_info.score_percentage}%).",
                        trigger_type="TOPIC_MASTERY_DEFICIT",
                        severity="WARNING",
                        is_anomaly=False,
                        risk_score=risk_res.composite_score,
                        baseline_snapshot=dict(baseline_snapshot, weak_topic=topic_obj.title, topic_score=t_info.score_percentage),
                        creator_user=creator_user,
                        action_templates=action_templates,
                        linked_resources=resources
                    )
                    if rec:
                        recommendations.append(rec)

        return recommendations

    @classmethod
    def _create_or_skip_recommendation(
        cls,
        student: StudentProfile,
        section: ClassSection,
        category: str,
        target_metric: str,
        title: str,
        objective: str,
        trigger_type: str,
        severity: str,
        is_anomaly: bool,
        risk_score: float,
        baseline_snapshot: Dict[str, Any],
        creator_user,
        action_templates: List[tuple],
        topic: Optional[Topic] = None,
        linked_resources: Optional[List[LearningResource]] = None
    ) -> Optional[Intervention]:
        """
        Helper method checking for existing active interventions before creating a new recommendation.
        """
        # Deduplication check: Do not duplicate if student already has an active plan in this section & category
        active_statuses = [
            Intervention.Status.RECOMMENDED,
            Intervention.Status.APPROVED,
            Intervention.Status.ASSIGNED,
            Intervention.Status.IN_PROGRESS,
            Intervention.Status.COMPLETED,
            Intervention.Status.EVALUATING
        ]
        existing = Intervention.objects.filter(
            student=student,
            class_section=section,
            category=category,
            topic=topic,
            status__in=active_statuses
        ).exists()

        if existing:
            return None

        # Priority calculation
        p_score = InterventionPrioritizationService.calculate_priority_score(
            risk_score=risk_score,
            severity=severity,
            is_anomaly=is_anomaly,
            is_deadline_near=False
        )
        priority_choice = InterventionPrioritizationService.classify_priority(p_score)

        # Default due date = 14 days from now
        default_due = timezone.now().date() + timezone.timedelta(days=14)

        with transaction.atomic():
            intervention = Intervention.objects.create(
                student=student,
                course=section.course,
                class_section=section,
                topic=topic,
                assigned_to=section.primary_teacher,
                created_by=creator_user,
                title=title,
                category=category,
                status=Intervention.Status.RECOMMENDED,
                priority=priority_choice,
                primary_target_metric=target_metric,
                evaluation_window=Intervention.EvaluationWindow.DAYS_14,
                objective=objective,
                due_date=default_due,
                trigger_insight_type=trigger_type,
                baseline_metrics=baseline_snapshot
            )

            # Create default actions
            for idx, (act_title, act_desc, ver_type) in enumerate(action_templates, start=1):
                res_link = linked_resources[idx - 1] if linked_resources and (idx - 1) < len(linked_resources) else None
                InterventionAction.objects.create(
                    intervention=intervention,
                    order_index=idx,
                    title=act_title,
                    description=act_desc,
                    verification_type=ver_type,
                    resource=res_link,
                    due_date=default_due,
                    status=InterventionAction.ActionStatus.PENDING
                )

            # Create pending acknowledgment record
            InterventionAcknowledgement.objects.create(
                intervention=intervention,
                status=InterventionAcknowledgement.AckStatus.PENDING
            )

        return intervention
