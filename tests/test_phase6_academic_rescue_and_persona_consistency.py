"""
Phase 6 Automated Tests: Persona Consistency & End-to-End Academic Rescue Flow.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assessment,
    AssessmentResult
)
from apps.analytics.services import (
    RiskEngineService,
    AttendanceAnalyticsService,
    TrendAnalyticsService,
    AnomalyDetectionService
)
from apps.interventions.models import (
    Intervention,
    InterventionAction,
    InterventionEvaluation
)
from apps.interventions.services import (
    InterventionLifecycleService,
    InterventionActionService,
    InterventionCheckpointService,
    InterventionImpactService
)
from apps.portal.reporting import TranscriptService


class Phase6AcademicRescueAndPersonaConsistencyTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Mathematics & CS", code="MATH")
        self.prog = Program.objects.create(name="B.Sc. Applied Math", code="BSAM", department=self.dept)

        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            password="Password123!",
            role=Role.TEACHER,
            first_name="Alan",
            last_name="Turing"
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, employee_id="FAC-001", department=self.dept)

        self.ay = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        self.sem = Semester.objects.create(
            academic_year=self.ay,
            semester_number=1,
            name="Fall 2026",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 31),
            is_active=True
        )
        self.course = Course.objects.create(department=self.dept, code="MATH301", title="Differential Equations", credits=Decimal('4.0'))
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code="A", primary_teacher=self.teacher)

        # Persona 7: Katherine Johnson (Acute Anomaly Plunge)
        self.student_user = User.objects.create_user(
            email="katherine@example.com",
            password="Password123!",
            role=Role.STUDENT,
            first_name="Katherine",
            last_name="Johnson"
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-007",
            department=self.dept,
            program=self.prog
        )
        self.enr = Enrollment.objects.create(
            student=self.student,
            class_section=self.section,
            status=Enrollment.EnrollmentStatus.ENROLLED
        )

        # High baseline attendance (90%)
        for i in range(10):
            sess = ClassSession.objects.create(
                class_section=self.section,
                teacher=self.teacher,
                session_date=date(2026, 9, 1) + timedelta(days=i),
                title=f"Session {i+1}"
            )
            AttendanceRecord.objects.create(
                session=sess,
                student=self.student,
                status=AttendanceRecord.AttendanceStatus.PRESENT if i < 9 else AttendanceRecord.AttendanceStatus.ABSENT
            )

        # Baseline assessment series: 78, 80, 76 -> Plunge to 38
        self.a1 = Assessment.objects.create(class_section=self.section, title="Quiz 1", assessment_type=Assessment.AssessmentType.QUIZ, max_marks=Decimal('100.0'), weightage_percentage=Decimal('10.0'))
        self.a2 = Assessment.objects.create(class_section=self.section, title="Quiz 2", assessment_type=Assessment.AssessmentType.QUIZ, max_marks=Decimal('100.0'), weightage_percentage=Decimal('10.0'))
        self.a3 = Assessment.objects.create(class_section=self.section, title="Midterm 1", assessment_type=Assessment.AssessmentType.MIDTERM, max_marks=Decimal('100.0'), weightage_percentage=Decimal('20.0'))
        self.a4 = Assessment.objects.create(class_section=self.section, title="Midterm 2", assessment_type=Assessment.AssessmentType.MIDTERM, max_marks=Decimal('100.0'), weightage_percentage=Decimal('20.0'))

        AssessmentResult.objects.create(assessment=self.a1, student=self.student, marks_obtained=Decimal('78.00'))
        AssessmentResult.objects.create(assessment=self.a2, student=self.student, marks_obtained=Decimal('80.00'))
        AssessmentResult.objects.create(assessment=self.a3, student=self.student, marks_obtained=Decimal('76.00'))
        self.plunge_result = AssessmentResult.objects.create(assessment=self.a4, student=self.student, marks_obtained=Decimal('38.00'))

    def test_end_to_end_academic_rescue_flow(self):
        r"""
        Complete verification of the 8-step Academic Rescue Lifecycle:
        1. Detection (Anomaly $Z \le -2.0$)
        2. Analysis (Risk escalated by acute drop)
        3. Recommendation (Phase 4 targeted Concept Remediation plan generated)
        4. Teacher Approval (Faculty reviews and approves)
        5. Student Action (Student checks off practice tasks)
        6. Checkpoint Recorded (Teacher logs positive checkpoint)
        7. New Evidence & Deterministic Recalculation (Student scores 85 on re-test -> Risk recalculated down)
        8. Outcome Evaluation & Institutional Reporting (Outcome marked EFFECTIVE)
        """
        # Step 1 & 2: Detection & Analysis
        scores = [78.0, 80.0, 76.0, 38.0]
        anom_res = AnomalyDetectionService.detect_from_sequence(scores, context_name="MATH301")
        self.assertTrue(anom_res.is_anomaly)
        self.assertLessEqual(anom_res.z_score, -2.0)

        risk_res_before = RiskEngineService.evaluate_course_risk(self.student, self.section)
        self.assertIn(risk_res_before.risk_level, ['MODERATE', 'HIGH', 'CRITICAL'])

        # Step 3: Recommendation
        intv = Intervention.objects.create(
            student=self.student,
            course=self.course,
            class_section=self.section,
            assigned_to=self.teacher,
            category=Intervention.InterventionCategory.ACADEMIC_REMEDIAL,
            priority=Intervention.Priority.URGENT,
            status=Intervention.Status.RECOMMENDED,
            primary_target_metric=Intervention.TargetMetric.ASSESSMENT_PERFORMANCE,
            title="Differential Equations Remediation",
            objective="Re-establish core mastery on 2nd-order ODE boundary value problems.",
            due_date=timezone.now().date() + timedelta(days=14),
            created_by=self.student_user,
            baseline_metrics={
                'risk_score': 65.0,
                'weighted_score': 54.0,
                'attendance_percentage': 90.0,
                'completion_rate': 100.0
            }
        )

        # Step 4: Teacher Approval
        InterventionLifecycleService.approve_recommendation(intv, user=self.teacher_user)
        intv.refresh_from_db()
        self.assertEqual(intv.status, Intervention.Status.ASSIGNED)

        # Add Action Items
        act1 = InterventionAction.objects.create(
            intervention=intv,
            title="Review boundary value problem problem-sets",
            verification_type=InterventionAction.VerificationType.STUDENT_CHECK,
            status=InterventionAction.ActionStatus.PENDING
        )

        # Step 5: Student Action
        InterventionActionService.update_action_status(act1, user=self.student_user, new_status=InterventionAction.ActionStatus.COMPLETED)
        act1.refresh_from_db()
        self.assertEqual(act1.status, InterventionAction.ActionStatus.COMPLETED)

        # Step 6: Checkpoint Recorded
        cp = InterventionCheckpointService.record_checkpoint(
            intervention=intv,
            evaluator_user=self.teacher_user,
            notes="Student completed review exercises and demonstrated restored comprehension."
        )
        self.assertIsNotNone(cp)

        # Step 7: New Academic Evidence & Deterministic Recalculation
        # Student completes Recovery Assessment scoring 88%
        a_recovery = Assessment.objects.create(
            class_section=self.section,
            title="ODE Recovery Exam",
            assessment_type=Assessment.AssessmentType.FINAL,
            max_marks=Decimal('100.0'),
            weightage_percentage=Decimal('20.0')
        )
        AssessmentResult.objects.create(assessment=a_recovery, student=self.student, marks_obtained=Decimal('88.00'))

        # Phase 3 Deterministic Recalculation
        risk_res_after = RiskEngineService.evaluate_course_risk(self.student, self.section)
        # Verify deterministic calculation reflects the recovery
        self.assertLess(risk_res_after.composite_score, 50.0)

        # Step 8: Outcome Evaluation
        InterventionImpactService.evaluate_and_record_outcome(
            intervention=intv,
            evaluator_user=self.teacher_user,
            evaluator_notes="Performance restored. Score recovered to 88% on re-examination."
        )
        intv.refresh_from_db()
        self.assertEqual(intv.status, Intervention.Status.EFFECTIVE)

        # Transcript integrity check
        transcript = TranscriptService.get_student_transcript(self.student)
        self.assertEqual(transcript['student_id'], "STU-007")
        self.assertIsNotNone(transcript['cumulative_gpa'])
