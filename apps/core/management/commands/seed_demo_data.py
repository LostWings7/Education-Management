"""
Comprehensive management command to populate foundational Phase 1 & Phase 2 academic demo data.
Includes:
- Academic Years (2024-2025 Past, 2025-2026 Current)
- Semesters (Fall 2025 Completed Historical, Spring 2026 Active Live)
- Departments, Programs, Courses (Many-to-Many), Topics
- Class Sections, 7-Day Timetables (with Sunday slots)
- 7 Student Performance Archetypes with authentic granular historical records:
  1. High Achiever (Ada Lovelace)
  2. Chronic Attendance Deficit (Charles Babbage)
  3. Declining Trajectory (John von Neumann)
  4. Missing Assignments (Margaret Hamilton)
  5. Steady Improver (Linus Torvalds)
  6. Theory Struggle / Lab Ace (Dennis Ritchie)
  7. Sudden Performance Anomaly (Katherine Johnson: 75 -> 78 -> 76 -> 79 -> 38 drop)
"""

from decimal import Decimal
from datetime import date, time, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.core.models import User, Role, AuditLog
from apps.academic.models import (
    AcademicYear,
    Semester,
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    Course,
    Topic,
    ClassSection,
    Enrollment,
    ClassSchedule,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    LearningResource,
    CourseAnnouncement,
)
from apps.academic.services import GradingService


class Command(BaseCommand):
    help = 'Seeds complete multi-term academic core data and 7 student performance personas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Starting Phase 2 Academic Management database seeding...'))

        with transaction.atomic():
            # ================================================================
            # 1. Seed Academic Years & Semesters
            # ================================================================
            year_past, _ = AcademicYear.objects.get_or_create(
                name='2024-2025',
                defaults={
                    'start_date': date(2024, 8, 1),
                    'end_date': date(2025, 5, 31),
                    'is_current': False
                }
            )

            year_current, _ = AcademicYear.objects.get_or_create(
                name='2025-2026',
                defaults={
                    'start_date': date(2025, 8, 1),
                    'end_date': date(2026, 5, 31),
                    'is_current': True
                }
            )

            # Historical completed semester
            sem_fall25, _ = Semester.objects.get_or_create(
                academic_year=year_current,
                term_type=Semester.TermType.FALL,
                semester_number=1,
                defaults={
                    'name': 'Fall 2025',
                    'start_date': date(2025, 8, 1),
                    'end_date': date(2025, 12, 20),
                    'is_active': False,
                    'is_completed': True
                }
            )

            # Active live semester
            sem_spring26, _ = Semester.objects.get_or_create(
                academic_year=year_current,
                term_type=Semester.TermType.SPRING,
                semester_number=2,
                defaults={
                    'name': 'Spring 2026',
                    'start_date': date(2026, 1, 10),
                    'end_date': date(2026, 5, 30),
                    'is_active': True,
                    'is_completed': False
                }
            )
            # Ensure active flag
            sem_spring26.is_active = True
            sem_spring26.save()

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Academic Years (2024-2025, 2025-2026) and Semesters (Fall 2025 [Completed], Spring 2026 [Active])'))

            # ================================================================
            # 2. Seed Academic Departments & Degree Programs
            # ================================================================
            dept_cse, _ = Department.objects.get_or_create(
                code='CSE',
                defaults={'name': 'Computer Science and Engineering', 'is_active': True}
            )
            dept_ai, _ = Department.objects.get_or_create(
                code='AI_DS',
                defaults={'name': 'Artificial Intelligence and Data Science', 'is_active': True}
            )
            dept_ece, _ = Department.objects.get_or_create(
                code='ECE',
                defaults={'name': 'Electronics and Communication Engineering', 'is_active': True}
            )
            dept_math, _ = Department.objects.get_or_create(
                code='MATH',
                defaults={'name': 'Mathematics and Basic Sciences', 'is_active': True}
            )

            prog_cse, _ = Program.objects.get_or_create(
                code='BT-CSE',
                defaults={
                    'department': dept_cse,
                    'name': 'B.Tech in Computer Science & Engineering',
                    'degree_level': Program.DegreeLevel.BACHELOR,
                    'duration_years': 4,
                    'total_semesters': 8
                }
            )
            prog_ai, _ = Program.objects.get_or_create(
                code='BT-AI',
                defaults={
                    'department': dept_ai,
                    'name': 'B.Tech in Artificial Intelligence & Machine Learning',
                    'degree_level': Program.DegreeLevel.BACHELOR,
                    'duration_years': 4,
                    'total_semesters': 8
                }
            )
            prog_csbs, _ = Program.objects.get_or_create(
                code='BT-CSBS',
                defaults={
                    'department': dept_cse,
                    'name': 'B.Tech in Computer Science & Business Systems',
                    'degree_level': Program.DegreeLevel.BACHELOR,
                    'duration_years': 4,
                    'total_semesters': 8
                }
            )

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Departments (CSE, AI_DS, ECE, MATH) and Programs (BT-CSE, BT-AI, BT-CSBS)'))

            # ================================================================
            # 3. Seed Courses, Topics & Many-to-Many Program Affiliations
            # ================================================================
            # Course 1: Data Structures
            c_ds, _ = Course.objects.get_or_create(
                code='CS201',
                defaults={
                    'department': dept_cse,
                    'title': 'Data Structures and Algorithms',
                    'description': 'Linear and non-linear data structures, algorithm complexity analysis, dynamic programming, and graphs.',
                    'credits': 4,
                    'is_active': True
                }
            )
            c_ds.programs.set([prog_cse, prog_ai, prog_csbs])

            Topic.objects.get_or_create(course=c_ds, order_index=1, defaults={'title': 'Arrays, Linked Lists, & Complexity', 'description': 'Asymptotic analysis, memory layouts.'})
            Topic.objects.get_or_create(course=c_ds, order_index=2, defaults={'title': 'Stacks, Queues, & Recursion', 'description': 'LIFO/FIFO structures, recursion trees.'})
            Topic.objects.get_or_create(course=c_ds, order_index=3, defaults={'title': 'Trees & Binary Search Trees', 'description': 'Tree traversals, AVL, Red-Black balancing.'})
            Topic.objects.get_or_create(course=c_ds, order_index=4, defaults={'title': 'Graph Algorithms & Shortest Paths', 'description': 'BFS, DFS, Dijkstra, Bellman-Ford.'})
            Topic.objects.get_or_create(course=c_ds, order_index=5, defaults={'title': 'Dynamic Programming & Greedy Approaches', 'description': 'Memoization, knapsack, greedy heuristics.'})

            # Course 2: Database Systems
            c_db, _ = Course.objects.get_or_create(
                code='CS301',
                defaults={
                    'department': dept_cse,
                    'title': 'Database Management Systems',
                    'description': 'Relational architecture, SQL optimization, normalization, indexing, and ACID transactions.',
                    'credits': 4,
                    'is_active': True
                }
            )
            c_db.programs.set([prog_cse, prog_ai, prog_csbs])

            Topic.objects.get_or_create(course=c_db, order_index=1, defaults={'title': 'Relational Model & Advanced SQL', 'description': 'Schema definitions, joins, aggregations.'})
            Topic.objects.get_or_create(course=c_db, order_index=2, defaults={'title': 'ER Modeling & Relational Algebra', 'description': 'Entity-relationship diagrams to table mappings.'})
            Topic.objects.get_or_create(course=c_db, order_index=3, defaults={'title': 'Database Normalization (1NF - BCNF)', 'description': 'Functional dependencies, lossless decomposition.'})
            Topic.objects.get_or_create(course=c_db, order_index=4, defaults={'title': 'Transactions & Concurrency Control', 'description': 'ACID properties, two-phase locking, serializability.'})

            # Course 3: Machine Learning
            c_ml, _ = Course.objects.get_or_create(
                code='AI301',
                defaults={
                    'department': dept_ai,
                    'title': 'Machine Learning Fundamentals',
                    'description': 'Supervised learning, classification, clustering, model evaluation, and regularizations.',
                    'credits': 4,
                    'is_active': True
                }
            )
            c_ml.programs.set([prog_cse, prog_ai])

            Topic.objects.get_or_create(course=c_ml, order_index=1, defaults={'title': 'Linear Models & Gradient Descent', 'description': 'Cost functions, optimization algorithms.'})
            Topic.objects.get_or_create(course=c_ml, order_index=2, defaults={'title': 'Classification & Decision Trees', 'description': 'Logistic regression, entropy, random forests.'})
            Topic.objects.get_or_create(course=c_ml, order_index=3, defaults={'title': 'Unsupervised Learning & Clustering', 'description': 'K-Means, PCA dimensionality reduction.'})

            # Course 4: Intro to Programming (Past completed term)
            c_prog, _ = Course.objects.get_or_create(
                code='CS101',
                defaults={
                    'department': dept_cse,
                    'title': 'Introduction to Computer Systems & C',
                    'description': 'Foundational programming concepts, memory pointers, and modular programming.',
                    'credits': 4,
                    'is_active': True
                }
            )
            c_prog.programs.set([prog_cse, prog_ai, prog_csbs])

            # Course 5: Discrete Mathematics (Past completed term)
            c_math, _ = Course.objects.get_or_create(
                code='MA101',
                defaults={
                    'department': dept_math,
                    'title': 'Discrete Mathematics & Logic',
                    'description': 'Sets, relations, graph theory, propositional logic, and combinatorics.',
                    'credits': 4,
                    'is_active': True
                }
            )
            c_math.programs.set([prog_cse, prog_ai, prog_csbs])

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Curricular Courses (CS201, CS301, AI301, CS101, MA101) with Topics and Program links'))

            # ================================================================
            # 4. Seed Faculty / Instructors
            # ================================================================
            # Teacher 1: Alan Turing
            t1_user, _ = User.objects.get_or_create(
                email='teacher@example.com',
                defaults={'first_name': 'Alan', 'last_name': 'Turing', 'role': Role.TEACHER}
            )
            t1_user.set_password('Teacher@12345')
            t1_user.role = Role.TEACHER
            t1_user.save()

            t1_prof, _ = TeacherProfile.objects.update_or_create(
                user=t1_user,
                defaults={
                    'employee_id': 'FAC-1001',
                    'department': dept_cse,
                    'designation': 'Associate Professor',
                    'office_location': 'Room 402, Turing Block'
                }
            )

            # Teacher 2: Grace Hopper
            t2_user, _ = User.objects.get_or_create(
                email='teacher2@example.com',
                defaults={'first_name': 'Grace', 'last_name': 'Hopper', 'role': Role.TEACHER}
            )
            t2_user.set_password('Teacher@12345')
            t2_user.role = Role.TEACHER
            t2_user.save()

            t2_prof, _ = TeacherProfile.objects.update_or_create(
                user=t2_user,
                defaults={
                    'employee_id': 'FAC-1002',
                    'department': dept_cse,
                    'designation': 'Professor',
                    'office_location': 'Room 501, Hopper Hall'
                }
            )

            # Teacher 3: Claude Shannon
            t3_user, _ = User.objects.get_or_create(
                email='teacher3@example.com',
                defaults={'first_name': 'Claude', 'last_name': 'Shannon', 'role': Role.TEACHER}
            )
            t3_user.set_password('Teacher@12345')
            t3_user.role = Role.TEACHER
            t3_user.save()

            t3_prof, _ = TeacherProfile.objects.update_or_create(
                user=t3_user,
                defaults={
                    'employee_id': 'FAC-1003',
                    'department': dept_ai,
                    'designation': 'Associate Professor',
                    'office_location': 'Room 303, Shannon Block'
                }
            )

            # Administrator
            admin_user, _ = User.objects.get_or_create(
                email='admin@example.com',
                defaults={'first_name': 'System', 'last_name': 'Administrator', 'role': Role.ADMINISTRATOR, 'is_staff': True, 'is_superuser': True}
            )
            admin_user.set_password('Admin@12345')
            admin_user.role = Role.ADMINISTRATOR
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Faculty (Alan Turing, Grace Hopper, Claude Shannon) and Administrator'))

            # ================================================================
            # 5. Seed Class Sections & 7-Day Timetables
            # ================================================================
            # Spring 2026 (Active) Sections
            sec_ds, _ = ClassSection.objects.get_or_create(
                course=c_ds,
                semester=sem_spring26,
                section_code='A',
                defaults={'primary_teacher': t1_prof, 'capacity': 60, 'room_number': 'Lab 301', 'is_active': True}
            )

            sec_db, _ = ClassSection.objects.get_or_create(
                course=c_db,
                semester=sem_spring26,
                section_code='A',
                defaults={'primary_teacher': t2_prof, 'capacity': 60, 'room_number': 'Room 402', 'is_active': True}
            )

            sec_ml, _ = ClassSection.objects.get_or_create(
                course=c_ml,
                semester=sem_spring26,
                section_code='A',
                defaults={'primary_teacher': t3_prof, 'capacity': 45, 'room_number': 'AI Lab 102', 'is_active': True}
            )

            # Fall 2025 (Historical Completed) Sections
            sec_prog_hist, _ = ClassSection.objects.get_or_create(
                course=c_prog,
                semester=sem_fall25,
                section_code='A',
                defaults={'primary_teacher': t1_prof, 'capacity': 60, 'room_number': 'Lab 201', 'is_active': False}
            )

            sec_math_hist, _ = ClassSection.objects.get_or_create(
                course=c_math,
                semester=sem_fall25,
                section_code='A',
                defaults={'primary_teacher': t3_prof, 'capacity': 60, 'room_number': 'Room 301', 'is_active': False}
            )

            # Timetable Slots (Days 1 to 7 support)
            ClassSchedule.objects.get_or_create(class_section=sec_ds, day_of_week=1, start_time=time(9, 0), defaults={'end_time': time(10, 30), 'teacher': t1_prof, 'room': 'Lab 301'})
            ClassSchedule.objects.get_or_create(class_section=sec_ds, day_of_week=3, start_time=time(9, 0), defaults={'end_time': time(10, 30), 'teacher': t1_prof, 'room': 'Lab 301'})
            ClassSchedule.objects.get_or_create(class_section=sec_ds, day_of_week=5, start_time=time(9, 0), defaults={'end_time': time(10, 30), 'teacher': t1_prof, 'room': 'Lab 301'})

            ClassSchedule.objects.get_or_create(class_section=sec_db, day_of_week=2, start_time=time(11, 0), defaults={'end_time': time(12, 30), 'teacher': t2_prof, 'room': 'Room 402'})
            ClassSchedule.objects.get_or_create(class_section=sec_db, day_of_week=4, start_time=time(11, 0), defaults={'end_time': time(12, 30), 'teacher': t2_prof, 'room': 'Room 402'})
            ClassSchedule.objects.get_or_create(class_section=sec_db, day_of_week=6, start_time=time(10, 0), defaults={'end_time': time(11, 30), 'teacher': t2_prof, 'room': 'Room 402'})

            ClassSchedule.objects.get_or_create(class_section=sec_ml, day_of_week=1, start_time=time(14, 0), defaults={'end_time': time(15, 30), 'teacher': t3_prof, 'room': 'AI Lab 102'})
            ClassSchedule.objects.get_or_create(class_section=sec_ml, day_of_week=7, start_time=time(10, 0), defaults={'end_time': time(11, 30), 'teacher': t3_prof, 'room': 'AI Lab 102'})  # Sunday timetable demo

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Class Sections and 7-day Timetable (including Sunday slot)'))

            # ================================================================
            # 6. Seed 7 Distinct Student Performance Personas
            # ================================================================
            personas_info = [
                ('student@example.com', 'Ada', 'Lovelace', 'STU-2026-001', prog_cse, 'High Achiever'),
                ('student2@example.com', 'Charles', 'Babbage', 'STU-2026-002', prog_cse, 'Chronic Attendance Deficit'),
                ('student3@example.com', 'John', 'von Neumann', 'STU-2026-003', prog_cse, 'Declining Trajectory'),
                ('student4@example.com', 'Margaret', 'Hamilton', 'STU-2026-004', prog_cse, 'Missing Assignments'),
                ('student5@example.com', 'Linus', 'Torvalds', 'STU-2026-005', prog_cse, 'Steady Improver'),
                ('student6@example.com', 'Dennis', 'Ritchie', 'STU-2026-006', prog_cse, 'Theory Struggle / Lab Ace'),
                ('student7@example.com', 'Katherine', 'Johnson', 'STU-2026-007', prog_ai, 'Sudden Performance Anomaly'),
            ]

            student_profiles = {}
            for email, fn, ln, roll, prog, desc in personas_info:
                u, _ = User.objects.get_or_create(email=email, defaults={'first_name': fn, 'last_name': ln, 'role': Role.STUDENT})
                u.set_password('Student@12345')
                u.role = Role.STUDENT
                u.save()

                sp, _ = StudentProfile.objects.update_or_create(
                    user=u,
                    defaults={
                        'student_id': roll,
                        'department': prog.department,
                        'program': prog,
                        'current_semester': 4 if 'Past' in desc else 3,
                        'academic_year': 2026,
                        'academic_status': StudentProfile.AcademicStatus.ACTIVE
                    }
                )
                student_profiles[email] = sp

                # Enroll in active semester sections
                Enrollment.objects.get_or_create(student=sp, class_section=sec_ds, defaults={'status': Enrollment.EnrollmentStatus.ENROLLED})
                Enrollment.objects.get_or_create(student=sp, class_section=sec_db, defaults={'status': Enrollment.EnrollmentStatus.ENROLLED})
                if prog == prog_ai:
                    Enrollment.objects.get_or_create(student=sp, class_section=sec_ml, defaults={'status': Enrollment.EnrollmentStatus.ENROLLED})

                # Enroll in completed Fall 2025 semester sections with snapshots
                hist_enr1, _ = Enrollment.objects.get_or_create(
                    student=sp,
                    class_section=sec_prog_hist,
                    defaults={
                        'status': Enrollment.EnrollmentStatus.COMPLETED,
                        'final_percentage': Decimal('88.50'),
                        'final_grade_letter': 'A',
                        'is_grade_published': True,
                        'published_at': timezone.now() - timedelta(days=60)
                    }
                )
                hist_enr2, _ = Enrollment.objects.get_or_create(
                    student=sp,
                    class_section=sec_math_hist,
                    defaults={
                        'status': Enrollment.EnrollmentStatus.COMPLETED,
                        'final_percentage': Decimal('84.00'),
                        'final_grade_letter': 'A',
                        'is_grade_published': True,
                        'published_at': timezone.now() - timedelta(days=60)
                    }
                )

            self.stdout.write(self.style.SUCCESS('[OK] Seeded 7 Student Personas and Active/Historical Enrollments'))

            # ================================================================
            # 7. Seed Formative Assignments & Submissions
            # ================================================================
            asgn1, _ = Assignment.objects.get_or_create(
                class_section=sec_ds,
                title='Problem Set 1: Dynamic Arrays & Linked Lists',
                defaults={
                    'teacher': t1_prof,
                    'description': 'Implement doubly linked list and dynamic array reallocation with O(1) amortized insertion.',
                    'max_marks': Decimal('50.00'),
                    'due_date': timezone.now() - timedelta(days=40),
                    'allow_late_submission': True,
                    'is_published': True
                }
            )

            asgn2, _ = Assignment.objects.get_or_create(
                class_section=sec_ds,
                title='Problem Set 2: Binary Search Trees & AVL Balancing',
                defaults={
                    'teacher': t1_prof,
                    'description': 'Implement self-balancing AVL tree insertion and subtree rotations.',
                    'max_marks': Decimal('50.00'),
                    'due_date': timezone.now() - timedelta(days=25),
                    'allow_late_submission': True,
                    'is_published': True
                }
            )

            asgn3, _ = Assignment.objects.get_or_create(
                class_section=sec_ds,
                title='Problem Set 3: Graph Traversal & Dijkstra Implementation',
                defaults={
                    'teacher': t1_prof,
                    'description': 'Shortest path implementation using priority queues.',
                    'max_marks': Decimal('50.00'),
                    'due_date': timezone.now() - timedelta(days=10),
                    'allow_late_submission': True,
                    'is_published': True
                }
            )

            asgn4, _ = Assignment.objects.get_or_create(
                class_section=sec_ds,
                title='Problem Set 4: Dynamic Programming Matrix Chain',
                defaults={
                    'teacher': t1_prof,
                    'description': 'Optimal matrix chain multiplication memoization table.',
                    'max_marks': Decimal('50.00'),
                    'due_date': timezone.now() + timedelta(days=5),
                    'allow_late_submission': True,
                    'is_published': True
                }
            )

            # Granular Submissions per Persona for Assignment 1-3
            # Persona 1 (Ada - High Achiever): 49, 48, 50
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('49.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('48.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('50.00'), 'graded_by': t1_prof})

            # Persona 2 (Charles - Chronic Attendance): 36, 38, 35
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student2@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('36.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student2@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('38.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student2@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('35.00'), 'graded_by': t1_prof})

            # Persona 3 (John - Declining Trajectory): 45 -> 32 -> 18
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student3@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('45.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student3@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('32.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student3@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('18.00'), 'graded_by': t1_prof})

            # Persona 4 (Margaret - Missing Assignments): PS1=46, PS2 & PS3 unsubmitted
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student4@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('46.00'), 'graded_by': t1_prof})

            # Persona 5 (Linus - Steady Improver): 28 -> 36 -> 46
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student5@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('28.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student5@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('36.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student5@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('46.00'), 'graded_by': t1_prof})

            # Persona 6 (Dennis - Practical Ace): 48, 49, 50
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student6@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('48.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student6@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('49.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student6@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('50.00'), 'graded_by': t1_prof})

            # Persona 7 (Katherine - Sudden Anomaly Baseline): 39, 40, 38
            AssignmentSubmission.objects.update_or_create(assignment=asgn1, student=student_profiles['student7@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('39.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn2, student=student_profiles['student7@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('40.00'), 'graded_by': t1_prof})
            AssignmentSubmission.objects.update_or_create(assignment=asgn3, student=student_profiles['student7@example.com'], defaults={'status': AssignmentSubmission.SubmissionStatus.GRADED, 'obtained_marks': Decimal('38.00'), 'graded_by': t1_prof})

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Formative Coursework Assignments & Submissions across all 7 Personas'))

            # ================================================================
            # 8. Seed Evaluative Assessments & Granular Results
            # ================================================================
            # In CS201-A (Data Structures):
            # 1. Quiz 1 (15% weight)
            # 2. Assignments Portfolio (20% weight - aggregate)
            # 3. Midterm Examination (30% weight)
            # 4. Practical Lab Exam (15% weight)
            # 5. Recent Assessment / Review Test (20% weight) -> Total 100%
            ass_q1, _ = Assessment.objects.get_or_create(
                class_section=sec_ds,
                title='Quiz 1: Complexity & Basic Structures',
                defaults={
                    'assessment_type': Assessment.AssessmentType.QUIZ,
                    'date': date(2026, 1, 28),
                    'max_marks': Decimal('100.00'),
                    'weightage_percentage': Decimal('15.00'),
                    'is_published': True
                }
            )

            ass_portfolio, _ = Assessment.objects.get_or_create(
                class_section=sec_ds,
                title='Assignments Evaluation Portfolio',
                defaults={
                    'assessment_type': Assessment.AssessmentType.ASSIGNMENTS,
                    'date': date(2026, 2, 20),
                    'max_marks': Decimal('100.00'),
                    'weightage_percentage': Decimal('20.00'),
                    'is_published': True
                }
            )

            ass_mid, _ = Assessment.objects.get_or_create(
                class_section=sec_ds,
                title='Midterm Examination: Trees & Sorting',
                defaults={
                    'assessment_type': Assessment.AssessmentType.MIDTERM,
                    'date': date(2026, 3, 10),
                    'max_marks': Decimal('100.00'),
                    'weightage_percentage': Decimal('30.00'),
                    'is_published': True
                }
            )

            ass_lab, _ = Assessment.objects.get_or_create(
                class_section=sec_ds,
                title='Practical Laboratory Evaluation',
                defaults={
                    'assessment_type': Assessment.AssessmentType.PRACTICAL,
                    'date': date(2026, 4, 5),
                    'max_marks': Decimal('100.00'),
                    'weightage_percentage': Decimal('15.00'),
                    'is_published': True
                }
            )

            ass_recent, _ = Assessment.objects.get_or_create(
                class_section=sec_ds,
                title='Recent Comprehensive Unit Assessment',
                defaults={
                    'assessment_type': Assessment.AssessmentType.PROJECT,
                    'date': date(2026, 4, 25),
                    'max_marks': Decimal('100.00'),
                    'weightage_percentage': Decimal('20.00'),
                    'is_published': True
                }
            )

            # Scores Matrix: (Quiz1, Midterm, Lab, Recent)
            scores_matrix = {
                'student@example.com': (Decimal('94.00'), Decimal('92.00'), Decimal('96.00'), Decimal('95.00')),
                'student2@example.com': (Decimal('72.00'), Decimal('74.00'), Decimal('70.00'), Decimal('73.00')),
                'student3@example.com': (Decimal('88.00'), Decimal('68.00'), Decimal('58.00'), Decimal('42.00')),   # Declining trend
                'student4@example.com': (Decimal('85.00'), Decimal('84.00'), Decimal('82.00'), Decimal('86.00')),
                'student5@example.com': (Decimal('52.00'), Decimal('68.00'), Decimal('80.00'), Decimal('86.00')),   # Steady improvement
                'student6@example.com': (Decimal('48.00'), Decimal('46.00'), Decimal('95.00'), Decimal('45.00')),   # Theory struggle, Lab ace
                'student7@example.com': (Decimal('75.00'), Decimal('78.00'), Decimal('76.00'), Decimal('38.00')),   # Sudden Drop Anomaly 75->78->76->38!
            }

            for email, (q1_m, mid_m, lab_m, rec_m) in scores_matrix.items():
                sp = student_profiles[email]
                AssessmentResult.objects.update_or_create(assessment=ass_q1, student=sp, defaults={'marks_obtained': q1_m, 'graded_by': t1_prof})
                AssessmentResult.objects.update_or_create(assessment=ass_mid, student=sp, defaults={'marks_obtained': mid_m, 'graded_by': t1_prof})
                AssessmentResult.objects.update_or_create(assessment=ass_lab, student=sp, defaults={'marks_obtained': lab_m, 'graded_by': t1_prof})
                AssessmentResult.objects.update_or_create(assessment=ass_recent, student=sp, defaults={'marks_obtained': rec_m, 'graded_by': t1_prof})

            # Calculate and publish snapshots for DS section
            GradingService.publish_section_grades(sec_ds, actor=admin_user)
            self.stdout.write(self.style.SUCCESS('[OK] Seeded Evaluative Assessments and published calculated grade snapshots'))

            # ================================================================
            # 9. Seed Authentic Granular Session Attendance
            # ================================================================
            # Create 20 dated lectures across Jan - April 2026
            start_lecture_date = date(2026, 1, 12)
            session_dates = [start_lecture_date + timedelta(days=i * 4) for i in range(20)]

            for i, sdate in enumerate(session_dates):
                sess, _ = ClassSession.objects.get_or_create(
                    class_section=sec_ds,
                    session_date=sdate,
                    defaults={
                        'teacher': t1_prof,
                        'title': f'Lecture {i+1}: Advanced Data Structure Implementation',
                        'is_completed': True
                    }
                )

                for email, sp in student_profiles.items():
                    # Attendance policy per persona:
                    if email == 'student@example.com':
                        status = AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student2@example.com':
                        # Chronic Deficit: 10 absences out of 20
                        status = AttendanceRecord.AttendanceStatus.ABSENT if (i % 2 == 1) else AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student3@example.com':
                        # Declining: absent in recent lectures 14, 16, 18, 19
                        status = AttendanceRecord.AttendanceStatus.ABSENT if i in [14, 16, 18, 19] else AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student4@example.com':
                        status = AttendanceRecord.AttendanceStatus.ABSENT if i in [5, 12] else AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student5@example.com':
                        status = AttendanceRecord.AttendanceStatus.LATE if i in [2, 7] else AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student6@example.com':
                        status = AttendanceRecord.AttendanceStatus.PRESENT
                    elif email == 'student7@example.com':
                        status = AttendanceRecord.AttendanceStatus.ABSENT if i == 18 else AttendanceRecord.AttendanceStatus.PRESENT
                    else:
                        status = AttendanceRecord.AttendanceStatus.PRESENT

                    AttendanceRecord.objects.update_or_create(
                        session=sess,
                        student=sp,
                        defaults={'status': status}
                    )

            self.stdout.write(self.style.SUCCESS(f'[OK] Seeded 20 granular Class Sessions and {20 * len(student_profiles)} Attendance Records'))

            # ================================================================
            # 10. Seed Learning Resources & Announcements
            # ================================================================
            LearningResource.objects.get_or_create(
                course=c_ds,
                title='Binary Search Trees & AVL Rotations Cheatsheet',
                defaults={
                    'resource_type': LearningResource.ResourceType.PDF,
                    'description': 'Comprehensive visual guide to single and double tree rotations.',
                    'uploaded_by': t1_user,
                    'is_published': True
                }
            )

            LearningResource.objects.get_or_create(
                course=c_ds,
                title='Graph Traversal Algorithms Video Lecture',
                defaults={
                    'resource_type': LearningResource.ResourceType.VIDEO,
                    'external_url': 'https://example.com/lectures/graphs-bfs-dfs',
                    'description': 'In-depth explanation of BFS queue state and DFS stack recursion.',
                    'uploaded_by': t1_user,
                    'is_published': True
                }
            )

            CourseAnnouncement.objects.get_or_create(
                class_section=sec_ds,
                title='Midterm Review Session & Office Hours',
                defaults={
                    'teacher': t1_prof,
                    'content': 'Office hours are extended this Wednesday from 2 PM to 5 PM in Room 402 for midterm exam Q&A.',
                    'is_pinned': True
                }
            )

            self.stdout.write(self.style.SUCCESS('[OK] Seeded Learning Resources and Course Announcements'))

        self.stdout.write(self.style.SUCCESS('\n======================================================='))
        self.stdout.write(self.style.SUCCESS('Phase 2 Academic Core Seeding Successfully Completed!'))
        self.stdout.write(self.style.SUCCESS('======================================================='))
        self.stdout.write('Persona Accounts:')
        self.stdout.write('  1. High Achiever      : student@example.com   / Student@12345 (Ada Lovelace)')
        self.stdout.write('  2. Attendance Deficit : student2@example.com  / Student@12345 (Charles Babbage)')
        self.stdout.write('  3. Declining Trend    : student3@example.com  / Student@12345 (John von Neumann)')
        self.stdout.write('  4. Missing Assignments: student4@example.com  / Student@12345 (Margaret Hamilton)')
        self.stdout.write('  5. Steady Improver    : student5@example.com  / Student@12345 (Linus Torvalds)')
        self.stdout.write('  6. Theory Struggle    : student6@example.com  / Student@12345 (Dennis Ritchie)')
        self.stdout.write('  7. Sudden Anomaly     : student7@example.com  / Student@12345 (Katherine Johnson: 75->78->76->38)')
        self.stdout.write('Faculty / Admin:')
        self.stdout.write('  Teacher (CS)          : teacher@example.com   / Teacher@12345 (Alan Turing)')
        self.stdout.write('  Teacher (DB)          : teacher2@example.com  / Teacher@12345 (Grace Hopper)')
        self.stdout.write('  Teacher (AI)          : teacher3@example.com  / Teacher@12345 (Claude Shannon)')
        self.stdout.write('  Administrator         : admin@example.com     / Admin@12345')
        self.stdout.write('=======================================================\n')
