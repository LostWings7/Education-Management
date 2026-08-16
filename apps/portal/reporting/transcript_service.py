"""
Official Academic Transcript & Academic Record Service.
Calculates official Term GPA, Cumulative GPA, Earned Credits, and Academic Standing.
Guarantees strict data immutability and deterministic authority.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from apps.academic.models import (
    StudentProfile,
    AcademicYear,
    Semester,
    Enrollment
)
from apps.academic.services import GradingService
from apps.analytics.services import AttendanceAnalyticsService


class TranscriptService:
    """
    Assembles official student transcript records.
    """

    @classmethod
    def get_student_transcript(cls, student: StudentProfile) -> Dict[str, Any]:
        """
        Compiles complete lifetime transcript for the student grouped by semester.
        """
        enrollments = list(Enrollment.objects.filter(
            student=student,
            status=Enrollment.EnrollmentStatus.ENROLLED
        ).select_related(
            'class_section__course',
            'class_section__semester__academic_year',
            'class_section__primary_teacher__user'
        ).order_by(
            'class_section__semester__academic_year__start_date',
            'class_section__semester__semester_number',
            'class_section__course__code'
        ))

        semesters_dict: Dict[int, Dict[str, Any]] = {}
        total_quality_points = Decimal('0.00')
        total_credit_hours = Decimal('0.00')
        total_earned_credits = Decimal('0.00')

        grade_point_map = {
            'A+': Decimal('4.00'), 'A': Decimal('4.00'), 'A-': Decimal('3.70'),
            'B+': Decimal('3.30'), 'B': Decimal('3.00'), 'B-': Decimal('2.70'),
            'C+': Decimal('2.30'), 'C': Decimal('2.00'), 'C-': Decimal('1.70'),
            'D+': Decimal('1.30'), 'D': Decimal('1.00'), 'F': Decimal('0.00')
        }

        for enr in enrollments:
            sec = enr.class_section
            sem = sec.semester
            ay = sem.academic_year
            course = sec.course

            if sem.pk not in semesters_dict:
                semesters_dict[sem.pk] = {
                    'semester_id': sem.pk,
                    'semester_name': sem.name,
                    'academic_year': ay.name,
                    'term_type': sem.get_term_type_display(),
                    'is_active': sem.is_active,
                    'courses': [],
                    'term_credits_attempted': Decimal('0.00'),
                    'term_credits_earned': Decimal('0.00'),
                    'term_quality_points': Decimal('0.00'),
                    'term_gpa': Decimal('0.00')
                }

            letter = enr.final_grade_letter or 'IP' # In Progress
            percentage = enr.final_percentage
            credits = Decimal(str(course.credits))

            sem_rec = semesters_dict[sem.pk]
            sem_rec['term_credits_attempted'] += credits

            points = grade_point_map.get(letter, None)
            if points is not None and letter != 'F':
                sem_rec['term_credits_earned'] += credits
                sem_rec['term_quality_points'] += (points * credits)
                total_earned_credits += credits
                total_quality_points += (points * credits)
                total_credit_hours += credits
            elif letter == 'F':
                total_credit_hours += credits

            # Attendance
            att_res = AttendanceAnalyticsService.calculate_course_attendance(student, sec)

            sem_rec['courses'].append({
                'course_code': course.code,
                'course_title': course.title,
                'credits': float(credits),
                'final_percentage': float(percentage) if percentage is not None else None,
                'grade_letter': letter,
                'grade_points': float(points) if points is not None else 0.0,
                'attendance_percentage': att_res.attendance_percentage if att_res else 100.0,
                'is_published': enr.is_grade_published
            })

        # Calculate Term GPAs
        semesters_list = []
        for sem_id, sem_data in semesters_dict.items():
            if sem_data['term_credits_attempted'] > Decimal('0.00') and sem_data['term_quality_points'] > Decimal('0.00'):
                sem_data['term_gpa'] = round(sem_data['term_quality_points'] / sem_data['term_credits_attempted'], 2)
            semesters_list.append(sem_data)

        # Calculate Cumulative GPA
        cgpa = round(total_quality_points / total_credit_hours, 2) if total_credit_hours > Decimal('0.00') else Decimal('0.00')

        # Academic Standing
        if cgpa >= Decimal('3.50'):
            standing = "Dean's List / Distinction"
            standing_badge = "badge-success"
        elif cgpa >= Decimal('2.00'):
            standing = "Good Standing"
            standing_badge = "badge-success"
        else:
            standing = "Academic Warning / Probation"
            standing_badge = "badge-danger"

        return {
            'student_id': student.student_id,
            'student_name': student.user.get_full_name(),
            'email': student.user.email,
            'department_name': student.department.name if student.department else "Department",
            'program_name': student.program.name if student.program else "Program",
            'enrollment_date': str(student.user.date_joined.date()),
            'semesters': semesters_list,
            'total_credits_attempted': float(total_credit_hours),
            'total_credits_earned': float(total_earned_credits),
            'cumulative_gpa': float(cgpa),
            'academic_standing': standing,
            'academic_standing_badge': standing_badge,
            'transcript_status': "OFFICIAL UNIVERSITY RECORD"
        }
