"""
Unit tests for Target-Aware Impact Evaluation, Checkpoint Recording, and Non-Causal Disclaimers.
"""

from decimal import Decimal
from datetime import date
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
    AttendanceRecord
)
from apps.interventions.models import (
    Intervention,
    InterventionEvaluation
)
from apps.interventions.services import (
    InterventionImpactService,
    InterventionCheckpointService
)


class InterventionTargetImpactAndCheckpointsTest(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(department=self.dept, code='BT-CSE', name='B.Tech CSE')
        self.ay = AcademicYear.objects.create(name='2025-2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 31), is_current=True)
        self.sem = Semester.objects.create(academic_year=self.ay, name='Spring 2026', term_type=Semester.TermType.SPRING, semester_number=2, start_date=date(2026, 1, 10), end_date=date(2026, 5, 30), is_active=True)

        t_u = User.objects.create_user(email='teacher.imp@example.com', password='Password@123', role=Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=t_u, employee_id='T-IMP', department=self.dept)

        s_u = User.objects.create_user(email='student.imp@example.com', password='Password@123', role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=s_u, student_id='S-IMP', department=self.dept, program=self.prog)

        self.course = Course.objects.create(department=self.dept, code='CS201', title='Data Structures', credits=4)
        self.course.programs.add(self.prog)
        self.section = ClassSection.objects.create(course=self.course, semester=self.sem, section_code='A', primary_teacher=self.teacher)
        self.enrollment = Enrollment.objects.create(student=self.student, class_section=self.section, status=Enrollment.EnrollmentStatus.ENROLLED)

        # Baseline plan targeting attendance
        self.intervention_att = Intervention.objects.create(
            student=self.student,
            course=self.course,
            class_section=self.section,
            assigned_to=self.teacher,
            created_by=t_u,
            title="Attendance Recovery",
            category=Intervention.InterventionCategory.ATTENDANCE_RECOVERY,
            status=Intervention.Status.IN_PROGRESS,
            priority=Intervention.Priority.HIGH,
            primary_target_metric=Intervention.TargetMetric.ATTENDANCE,
            due_date=timezone.now().date() + timezone.timedelta(days=14),
            objective="Recover attendance to 75%",
            baseline_metrics={"attendance_percentage": 50.0, "risk_score": 60.0}
        )

    def test_target_aware_effectiveness_effective(self):
        """When primary target attendance moves from 50% to 76%, classification is EFFECTIVE."""
        baseline = {"attendance_percentage": 50.0, "risk_score": 60.0}
        current = {"attendance_percentage": 76.0, "risk_score": 30.0}
        deltas = {"delta_attendance": 26.0, "delta_risk": 30.0}

        classification, summary, quality = InterventionImpactService.evaluate_target_effectiveness(
            intervention=self.intervention_att,
            baseline=baseline,
            current=current,
            deltas=deltas
        )
        self.assertEqual(classification, InterventionEvaluation.EffectivenessClassification.EFFECTIVE)
        self.assertEqual(quality, 'VALID')
        self.assertIn('statistical association does not establish sole causality', summary.lower())

    def test_target_aware_effectiveness_ineffective_when_target_deteriorates(self):
        """If primary target attendance drops further to 40%, classification is INEFFECTIVE."""
        baseline = {"attendance_percentage": 50.0, "risk_score": 60.0}
        current = {"attendance_percentage": 40.0, "risk_score": 75.0}
        deltas = {"delta_attendance": -10.0, "delta_risk": -15.0}

        classification, summary, quality = InterventionImpactService.evaluate_target_effectiveness(
            intervention=self.intervention_att,
            baseline=baseline,
            current=current,
            deltas=deltas
        )
        self.assertEqual(classification, InterventionEvaluation.EffectivenessClassification.INEFFECTIVE)
        self.assertIn('ineffective', summary.lower())

    def test_target_aware_effectiveness_insufficient_data(self):
        """When target metric is missing from evaluation data, returns INSUFFICIENT_DATA."""
        baseline = {"attendance_percentage": 50.0}
        current = {"weighted_score": 80.0} # Attendance not present
        deltas = {}

        classification, summary, quality = InterventionImpactService.evaluate_target_effectiveness(
            intervention=self.intervention_att,
            baseline=baseline,
            current=current,
            deltas=deltas
        )
        self.assertEqual(classification, InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA)

    def test_intermediate_checkpoint_recording(self):
        """Intermediate checkpoint is recorded without changing final outcome status."""
        # Create session records
        sess = ClassSession.objects.create(class_section=self.section, teacher=self.teacher, title="Session 1")
        AttendanceRecord.objects.create(session=sess, student=self.student, status=AttendanceRecord.AttendanceStatus.PRESENT)

        checkpoint = InterventionCheckpointService.record_checkpoint(
            intervention=self.intervention_att,
            evaluator_user=self.teacher.user,
            notes="Student attended all sessions this week."
        )
        self.assertEqual(checkpoint.checkpoint_number, 1)
        self.assertEqual(checkpoint.evaluation_type, InterventionEvaluation.EvaluationType.CHECKPOINT)
        self.assertEqual(checkpoint.evaluator, self.teacher.user)
        self.assertEqual(self.intervention_att.evaluations.count(), 1)
