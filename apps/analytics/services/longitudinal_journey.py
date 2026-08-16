"""
Deterministic Longitudinal Student Academic Journey & Multi-Term Trajectory Service.
Aggregates historical semester milestones and generates transparent, explainable forward projections.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from apps.academic.models import StudentProfile, Semester, Enrollment
from .trends import TrendAnalyticsService


class LongitudinalJourneyService:
    """
    Constructs multi-term longitudinal academic trajectory and safe forward projections.
    Guarantees:
      1. Never invents historical records.
      2. Requires >= 3 observations for forward-looking projections; otherwise returns INSUFFICIENT_DATA.
      3. All projections are strictly labeled as [PROJECTION] or [SIMULATION].
    """

    MIN_PROJECTION_OBSERVATIONS = 3
    GRADE_POINTS = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D': 1.0, 'F': 0.0, 'I': 0.0, 'W': 0.0
    }

    @classmethod
    def get_student_journey(cls, student: StudentProfile) -> Dict[str, Any]:
        """
        Build complete longitudinal journey object.
        """
        # Fetch all enrollments ordered chronologically by semester start_date
        enrollments = student.enrollments.select_related(
            'class_section__semester__academic_year',
            'class_section__course'
        ).order_by('class_section__semester__start_date')

        # Group enrollments by semester
        semesters_map: Dict[int, Dict[str, Any]] = {}
        for enr in enrollments:
            sem = enr.class_section.semester
            if sem.pk not in semesters_map:
                semesters_map[sem.pk] = {
                    'semester_id': sem.pk,
                    'semester_name': sem.name,
                    'academic_year': sem.academic_year.name,
                    'start_date': sem.start_date,
                    'end_date': sem.end_date,
                    'is_active': sem.is_active,
                    'is_completed': sem.is_completed,
                    'courses': [],
                    'total_credits': 0.0,
                    'earned_credits': 0.0,
                    'weighted_points': 0.0
                }

            course = enr.class_section.course
            credits = float(course.credits)
            pct = float(enr.final_percentage) if enr.final_percentage is not None else None
            grade = enr.final_grade_letter or 'IP'

            gpa_pt = cls.GRADE_POINTS.get(grade, 0.0) if enr.is_grade_published else None

            semesters_map[sem.pk]['courses'].append({
                'course_code': course.code,
                'course_title': course.title,
                'credits': credits,
                'percentage': pct,
                'grade': grade,
                'is_published': enr.is_grade_published
            })

            semesters_map[sem.pk]['total_credits'] += credits
            if enr.is_grade_published and grade != 'F':
                semesters_map[sem.pk]['earned_credits'] += credits
                semesters_map[sem.pk]['weighted_points'] += credits * gpa_pt

        # Build chronological milestones
        milestones: List[Dict[str, Any]] = []
        gpa_series: List[float] = []
        cumulative_credits = 0.0
        cumulative_points = 0.0

        for sem_id, sem_data in sorted(semesters_map.items(), key=lambda x: x[1]['start_date']):
            tot_cr = sem_data['total_credits']
            wt_pts = sem_data['weighted_points']
            term_gpa = round(wt_pts / tot_cr, 2) if tot_cr > 0 and sem_data['is_completed'] else None

            if term_gpa is not None:
                gpa_series.append(term_gpa)
                cumulative_credits += tot_cr
                cumulative_points += wt_pts

            cgpa = round(cumulative_points / cumulative_credits, 2) if cumulative_credits > 0 else None

            milestones.append({
                'semester_id': sem_id,
                'semester_name': sem_data['semester_name'],
                'academic_year': sem_data['academic_year'],
                'is_active': sem_data['is_active'],
                'is_completed': sem_data['is_completed'],
                'term_gpa': term_gpa,
                'cumulative_gpa': cgpa,
                'courses_count': len(sem_data['courses']),
                'earned_credits': sem_data['earned_credits'],
                'courses': sem_data['courses']
            })

        # -------------------------------------------------------------
        # Safe Forward Projection Engine
        # -------------------------------------------------------------
        projection_info: Dict[str, Any] = {
            'status': 'INSUFFICIENT_DATA',
            'projected_next_gpa': None,
            'confidence': 'LOW',
            'methodology': 'Ordinary Least Squares Linear Extrapolation',
            'disclaimer': '[PROJECTION] Statistical trajectory extrapolation based on completed terms. Not a guaranteed outcome.'
        }

        if len(gpa_series) >= cls.MIN_PROJECTION_OBSERVATIONS:
            trend_res = TrendAnalyticsService.calculate_linear_trend(gpa_series)
            n = len(gpa_series)
            slope = trend_res.slope or 0.0
            mean_y = sum(gpa_series) / n
            mean_x = (n + 1) / 2.0
            intercept = mean_y - (slope * mean_x)
            next_x = n + 1
            projected = round(max(0.0, min(4.0, intercept + slope * next_x)), 2)

            projection_info['status'] = 'VALID'
            projection_info['projected_next_gpa'] = projected
            projection_info['slope'] = trend_res.slope
            projection_info['direction'] = str(trend_res.direction)
            projection_info['confidence'] = 'HIGH' if (trend_res.std_dev or 0.0) < 0.3 else 'MEDIUM'

        # Current narrative framing
        start_point = milestones[0] if milestones else None
        current_point = milestones[-1] if milestones else None

        return {
            'student_id': student.student_id,
            'student_name': student.user.get_full_name(),
            'milestones': milestones,
            'completed_terms_count': len(gpa_series),
            'where_you_started': {
                'semester_name': start_point['semester_name'] if start_point else 'N/A',
                'initial_gpa': start_point['term_gpa'] if start_point else None
            },
            'where_you_are': {
                'semester_name': current_point['semester_name'] if current_point else 'N/A',
                'current_cgpa': current_point['cumulative_gpa'] if current_point else None
            },
            'where_you_are_headed': projection_info
        }
