"""
Interactive Demo Mode & State-Aware Persona Showcase Views.
Executes the live 12-step Academic Rescue flow against actual database models and deterministic analytics.
Strictly protected by settings.DEMO_MODE == True.
"""

from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login
from django.utils import timezone

from apps.core.models import User, Role
from apps.academic.models import (
    StudentProfile,
    TeacherProfile,
    ClassSection,
    Assessment,
    AssessmentResult,
    Semester
)
from apps.analytics.services import (
    RiskEngineService,
    AnomalyDetectionService,
    AttendanceAnalyticsService,
    TrendAnalyticsService
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionEvaluation
)
from apps.interventions.services import (
    InterventionLifecycleService,
    InterventionCheckpointService,
    InterventionImpactService,
    InterventionRecommendationService
)
from apps.notifications.models import Notification


class DemoShowcaseView(View):
    """
    Live presentation mode showing the 7 academic personas and state-aware 12-step rescue showcase.
    """
    template_name = 'portal/demo/showcase.html'

    def get(self, request):
        if not getattr(settings, 'DEMO_MODE', False):
            raise PermissionDenied("Demo mode is disabled in production.")

        # Query live personas if they exist in DB
        personas_data = []
        persona_configs = [
            ('STU-001', 'Ada Lovelace', 'student@example.com', 'High Achiever', 'badge-success'),
            ('STU-002', 'Charles Babbage', 'student2@example.com', 'Attendance Deficit', 'badge-danger'),
            ('STU-003', 'John von Neumann', 'student3@example.com', 'Declining Trajectory', 'badge-warning'),
            ('STU-004', 'Margaret Hamilton', 'student4@example.com', 'Missing Assignments', 'badge-warning'),
            ('STU-005', 'Linus Torvalds', 'student5@example.com', 'Steady Improver', 'badge-success'),
            ('STU-006', 'Dennis Ritchie', 'student6@example.com', 'Theory Friction Gap', 'badge-warning'),
            ('STU-007', 'Katherine Johnson', 'katherine@example.com', 'Acute Anomaly Plunge', 'badge-danger'),
        ]

        active_sem = Semester.objects.filter(is_active=True).first()

        for stu_id, name, email, role_desc, badge in persona_configs:
            profile = StudentProfile.objects.filter(student_id=stu_id).first()
            if profile:
                risk_res = RiskEngineService.evaluate_overall_risk(profile, semester=active_sem)
                att_res = AttendanceAnalyticsService.calculate_overall_attendance(profile, semester=active_sem)
                personas_data.append({
                    'id': stu_id,
                    'name': name,
                    'email': email,
                    'role': role_desc,
                    'badge': badge,
                    'attendance': f"{att_res.attendance_percentage:.1f}%" if att_res else "N/A",
                    'risk': f"{risk_res.risk_level} ({risk_res.composite_score:.1f}/100)" if risk_res else "N/A",
                    'trajectory': str(risk_res.trajectory_direction) if risk_res else "STABLE"
                })
            else:
                personas_data.append({
                    'id': stu_id,
                    'name': name,
                    'email': email,
                    'role': role_desc,
                    'badge': badge,
                    'attendance': "Seed via reset_demo_data",
                    'risk': "Not Seeded",
                    'trajectory': "N/A"
                })

        # Query live state for Katherine Johnson (STU-007)
        katherine = StudentProfile.objects.filter(student_id='STU-007').first()
        rescue_state = {}
        if katherine:
            enr = katherine.enrollments.first()
            if enr:
                sec = enr.class_section
                anom = AnomalyDetectionService.detect_course_anomaly(katherine, sec)
                risk = RiskEngineService.evaluate_course_risk(katherine, sec)
                intv = Intervention.objects.filter(student=katherine, class_section=sec).order_by('-pk').first()
                results = AssessmentResult.objects.filter(student=katherine, assessment__class_section=sec).order_by('assessment__title')

                rescue_state = {
                    'student_id': katherine.student_id,
                    'course_code': sec.course.code,
                    'anomaly_detected': anom.is_anomaly if anom else False,
                    'anomaly_desc': anom.description if anom else 'None',
                    'risk_level': str(risk.risk_level) if risk else 'UNKNOWN',
                    'risk_score': float(risk.composite_score) if risk else 0.0,
                    'intervention_id': intv.pk if intv else None,
                    'intervention_status': str(intv.status) if intv else 'None',
                    'assessment_results': [{'title': r.assessment.title, 'score': float(r.marks_obtained)} for r in results]
                }

        return render(request, self.template_name, {
            'personas': personas_data,
            'rescue_state': rescue_state,
            'is_demo_ready': bool(katherine)
        })


class DemoExecuteRescueStepView(View):
    """
    Executes live demo transitions for Katherine Johnson's 12-step Academic Rescue flow.
    """
    def post(self, request):
        if not getattr(settings, 'DEMO_MODE', False):
            return JsonResponse({'error': 'Demo mode disabled'}, status=403)

        action = request.POST.get('action')
        katherine = get_object_or_404(StudentProfile, student_id='STU-007')
        section = get_object_or_404(ClassSection, course__code='MATH301')
        teacher = section.primary_teacher.user

        if action == 'generate_intervention':
            # Create or get recommended intervention
            intv, created = Intervention.objects.get_or_create(
                student=katherine,
                class_section=section,
                category=Intervention.InterventionCategory.THEORY_REINFORCEMENT,
                defaults={
                    'title': 'Differential Equations & Laplace Recovery Plan',
                    'description': 'Targeted concept reinforcement following acute Quiz 3 plunge.',
                    'priority': Intervention.Priority.URGENT,
                    'created_by': teacher,
                    'assigned_to': teacher
                }
            )
            # Add action items
            InterventionAction.objects.get_or_create(
                intervention=intv,
                title='Review Laplace Transform practice problem set #4',
                defaults={'due_date': timezone.now().date() + timezone.timedelta(days=3)}
            )
            return JsonResponse({'success': True, 'step': 'Intervention Generated', 'status': intv.status})

        elif action == 'approve_intervention':
            intv = Intervention.objects.filter(student=katherine, class_section=section).first()
            if intv:
                InterventionLifecycleService.approve_recommendation(intv, user=teacher)
                return JsonResponse({'success': True, 'step': 'Intervention Approved', 'status': intv.status})
            return JsonResponse({'error': 'No intervention found'}, status=404)

        elif action == 'record_recovery_assessment':
            # Step 10: Record real 88% assessment result
            recov_assess, _ = Assessment.objects.get_or_create(
                class_section=section,
                title="Post-Remediation Recovery Assessment",
                defaults={
                    'assessment_type': Assessment.AssessmentType.QUIZ,
                    'max_marks': Decimal('100.0'),
                    'weightage_percentage': Decimal('15.0')
                }
            )
            AssessmentResult.objects.update_or_create(
                assessment=recov_assess,
                student=katherine,
                defaults={'marks_obtained': Decimal('88.0')}
            )

            # Step 11: Phase 3 Deterministic Recalculation
            recalc_risk = RiskEngineService.evaluate_course_risk(katherine, section)

            # Step 12: Evaluate outcome as EFFECTIVE
            intv = Intervention.objects.filter(student=katherine, class_section=section).first()
            if intv:
                intv.status = Intervention.Status.EFFECTIVE
                intv.save()

            return JsonResponse({
                'success': True,
                'step': 'Recovery Scored & Recalculated',
                'recovery_score': 88.0,
                'new_risk_level': str(recalc_risk.risk_level),
                'new_risk_score': float(recalc_risk.composite_score),
                'intervention_status': 'EFFECTIVE'
            })

        return JsonResponse({'error': 'Unknown action'}, status=400)
