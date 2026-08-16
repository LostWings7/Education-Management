"""
Management command to safely reset and seed all 7 persona scenarios for Phase 7 Demo & Competition mode.
Strictly protected by settings.DEMO_MODE == True.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    Topic,
    ClassSection,
    Enrollment,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult
)
from apps.interventions.models import (
    Intervention,
    InterventionAction
)
from apps.interventions.services import InterventionLifecycleService


class Command(BaseCommand):
    help = "Resets and seeds the pristine 7-persona dataset for competition demonstration (DEMO_MODE only)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for confirmation before resetting demo data.'
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'DEMO_MODE', False):
            raise CommandError("DEMO_MODE is disabled in settings. Refusing to modify database in production mode.")

        self.stdout.write(self.style.WARNING("Resetting demo dataset for all 7 academic personas..."))

        with transaction.atomic():
            # 1. Academic Structure
            dept, _ = Department.objects.get_or_create(code="MATH", defaults={'name': 'Mathematics & Computer Science', 'is_active': True})
            prog, _ = Program.objects.get_or_create(code="BSCS", defaults={'name': 'B.Sc. Computer Science', 'department': dept, 'duration_years': 4, 'total_semesters': 8, 'is_active': True})

            ay, _ = AcademicYear.objects.get_or_create(name="2025-2026", defaults={'start_date': date(2025, 9, 1), 'end_date': date(2026, 6, 30), 'is_current': True})
            
            # Historical completed semester
            sem_hist, _ = Semester.objects.get_or_create(
                academic_year=ay,
                semester_number=1,
                defaults={'name': 'Fall 2025', 'start_date': date(2025, 9, 1), 'end_date': date(2025, 12, 31), 'is_active': False, 'is_completed': True}
            )

            # Active current semester
            sem_curr, _ = Semester.objects.get_or_create(
                academic_year=ay,
                semester_number=2,
                defaults={'name': 'Spring 2026', 'start_date': date(2026, 2, 1), 'end_date': date(2026, 6, 30), 'is_active': True, 'is_completed': False}
            )

            # Faculty Alan Turing
            teacher_user, _ = User.objects.get_or_create(
                email="teacher@example.com",
                defaults={'role': Role.TEACHER, 'first_name': 'Alan', 'last_name': 'Turing'}
            )
            teacher_user.set_password("Password123!")
            teacher_user.save()
            teacher_profile, _ = TeacherProfile.objects.get_or_create(user=teacher_user, defaults={'employee_id': 'FAC-001', 'department': dept, 'designation': 'Professor'})

            # Administrator Grace Hopper
            admin_user, _ = User.objects.get_or_create(
                email="admin@example.com",
                defaults={'role': Role.ADMINISTRATOR, 'first_name': 'Grace', 'last_name': 'Hopper'}
            )
            admin_user.set_password("Password123!")
            admin_user.save()

            # Courses
            course_diff, _ = Course.objects.get_or_create(code="MATH301", defaults={'department': dept, 'title': 'Differential Equations', 'credits': Decimal('4.0'), 'is_active': True})
            course_algo, _ = Course.objects.get_or_create(code="CS201", defaults={'department': dept, 'title': 'Data Structures & Algorithms', 'credits': Decimal('4.0'), 'is_active': True})

            # Topics
            t1, _ = Topic.objects.get_or_create(course=course_diff, order_index=1, defaults={'title': 'First Order ODEs'})
            t2, _ = Topic.objects.get_or_create(course=course_diff, order_index=2, defaults={'title': 'Laplace Transforms'})
            t3, _ = Topic.objects.get_or_create(course=course_diff, order_index=3, defaults={'title': 'Boundary Value Problems'})

            # Class Sections
            sec_diff, _ = ClassSection.objects.get_or_create(course=course_diff, semester=sem_curr, section_code="A", defaults={'primary_teacher': teacher_profile, 'capacity': 40})
            sec_algo, _ = ClassSection.objects.get_or_create(course=course_algo, semester=sem_curr, section_code="A", defaults={'primary_teacher': teacher_profile, 'capacity': 40})

            # -------------------------------------------------------------
            # Persona 7: Katherine Johnson (Academic Rescue Flow)
            # -------------------------------------------------------------
            katherine_user, _ = User.objects.get_or_create(
                email="katherine@example.com",
                defaults={'role': Role.STUDENT, 'first_name': 'Katherine', 'last_name': 'Johnson'}
            )
            katherine_user.set_password("Password123!")
            katherine_user.save()

            katherine_profile, _ = StudentProfile.objects.get_or_create(
                user=katherine_user,
                defaults={'student_id': 'STU-007', 'department': dept, 'program': prog, 'current_semester': 2}
            )

            enr_k, _ = Enrollment.objects.get_or_create(
                student=katherine_profile,
                class_section=sec_diff,
                defaults={'status': Enrollment.EnrollmentStatus.ENROLLED}
            )

            # High baseline attendance (10 sessions, 9 attended)
            for i in range(10):
                sess, _ = ClassSession.objects.get_or_create(
                    class_section=sec_diff,
                    session_date=date(2026, 2, 1) + timedelta(days=i*3),
                    defaults={'teacher': teacher_profile, 'title': f"Lecture {i+1}"}
                )
                AttendanceRecord.objects.get_or_create(
                    session=sess,
                    student=katherine_profile,
                    defaults={'status': 'PRESENT' if i < 9 else 'ABSENT'}
                )

            # Historical strong baseline assessments (76, 78, 75) + Acute Anomaly Plunge (38)
            a1, _ = Assessment.objects.get_or_create(class_section=sec_diff, title="Quiz 1: First Order ODEs", defaults={'assessment_type': Assessment.AssessmentType.QUIZ, 'max_marks': Decimal('100.0'), 'weightage_percentage': Decimal('10.0')})
            AssessmentResult.objects.get_or_create(assessment=a1, student=katherine_profile, defaults={'marks_obtained': Decimal('76.0')})

            a2, _ = Assessment.objects.get_or_create(class_section=sec_diff, title="Quiz 2: Second Order ODEs", defaults={'assessment_type': Assessment.AssessmentType.QUIZ, 'max_marks': Decimal('100.0'), 'weightage_percentage': Decimal('10.0')})
            AssessmentResult.objects.get_or_create(assessment=a2, student=katherine_profile, defaults={'marks_obtained': Decimal('78.0')})

            a3, _ = Assessment.objects.get_or_create(class_section=sec_diff, title="Midterm Examination", defaults={'assessment_type': Assessment.AssessmentType.MIDTERM, 'max_marks': Decimal('100.0'), 'weightage_percentage': Decimal('30.0')})
            AssessmentResult.objects.get_or_create(assessment=a3, student=katherine_profile, defaults={'marks_obtained': Decimal('75.0')})

            # Acute Plunge Assessment (38.0 / 100.0) -> Z <= -2.0
            a_plunge, _ = Assessment.objects.get_or_create(class_section=sec_diff, title="Quiz 3: Laplace Transforms", defaults={'assessment_type': Assessment.AssessmentType.QUIZ, 'max_marks': Decimal('100.0'), 'weightage_percentage': Decimal('15.0')})
            AssessmentResult.objects.get_or_create(assessment=a_plunge, student=katherine_profile, defaults={'marks_obtained': Decimal('38.0')})

            # -------------------------------------------------------------
            # Persona 1: Ada Lovelace (High Achiever)
            # -------------------------------------------------------------
            ada_user, _ = User.objects.get_or_create(email="student@example.com", defaults={'role': Role.STUDENT, 'first_name': 'Ada', 'last_name': 'Lovelace'})
            ada_user.set_password("Password123!")
            ada_user.save()
            ada_profile, _ = StudentProfile.objects.get_or_create(user=ada_user, defaults={'student_id': 'STU-001', 'department': dept, 'program': prog, 'current_semester': 2})
            Enrollment.objects.get_or_create(student=ada_profile, class_section=sec_diff, defaults={'status': 'ENROLLED'})
            AssessmentResult.objects.get_or_create(assessment=a1, student=ada_profile, defaults={'marks_obtained': Decimal('96.0')})
            AssessmentResult.objects.get_or_create(assessment=a2, student=ada_profile, defaults={'marks_obtained': Decimal('98.0')})

            # -------------------------------------------------------------
            # Persona 2: Charles Babbage (Attendance Deficit)
            # -------------------------------------------------------------
            charles_user, _ = User.objects.get_or_create(email="student2@example.com", defaults={'role': Role.STUDENT, 'first_name': 'Charles', 'last_name': 'Babbage'})
            charles_user.set_password("Password123!")
            charles_user.save()
            charles_profile, _ = StudentProfile.objects.get_or_create(user=charles_user, defaults={'student_id': 'STU-002', 'department': dept, 'program': prog, 'current_semester': 2})
            Enrollment.objects.get_or_create(student=charles_profile, class_section=sec_diff, defaults={'status': 'ENROLLED'})
            # Charles attends only 5 of 10 sessions (50%)
            for i, sess in enumerate(ClassSession.objects.filter(class_section=sec_diff)):
                AttendanceRecord.objects.get_or_create(
                    session=sess,
                    student=charles_profile,
                    defaults={'status': 'PRESENT' if i < 5 else 'ABSENT'}
                )

        self.stdout.write(self.style.SUCCESS("Successfully reset and verified 7-persona demo dataset."))
