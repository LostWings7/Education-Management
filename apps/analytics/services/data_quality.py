"""
Academic Data Quality Engine.
Performs deterministic, 6-dimension institutional integrity audits.
Calculates transparent dimension scores and flags critical integrity issues.
Never lets high average scores mask critical errors.
"""

from typing import Dict, Any, List
from apps.core.models import User, Role
from apps.academic.models import (
    Department,
    Program,
    Course,
    Topic,
    StudentProfile,
    TeacherProfile,
    ClassSection,
    Enrollment,
    ClassSchedule,
    ClassSession,
    AttendanceRecord,
    Assignment,
    Assessment
)


class DataQualityEngineService:
    """
    Evaluates institutional academic data quality across 6 key dimensions.
    """

    @classmethod
    def run_full_audit(cls) -> Dict[str, Any]:
        """
        Executes complete institutional audit across all 6 dimensions.
        """
        issues: List[Dict[str, Any]] = []

        # 1. Profile Completeness
        users_without_profile = 0
        students_missing_program = 0
        students = StudentProfile.objects.all()
        for s in students:
            if not s.program_id or not s.department_id:
                students_missing_program += 1
                issues.append({
                    'dimension': 'Profile Completeness',
                    'severity': 'CRITICAL',
                    'entity': f"Student {s.student_id}",
                    'description': f"Student profile is missing assigned academic program or department.",
                    'suggestion': "Assign program and department in student profile admin."
                })

        dim1_score = 100.0 if not students_missing_program else max(0.0, 100.0 - (students_missing_program * 15.0))

        # 2. Curriculum Completeness
        courses_without_topics = 0
        courses = Course.objects.all()
        for c in courses:
            if not c.topics.exists():
                courses_without_topics += 1
                issues.append({
                    'dimension': 'Curriculum Completeness',
                    'severity': 'WARNING',
                    'entity': f"Course {c.code}",
                    'description': f"Course '{c.title}' has no syllabus topics mapped for mastery diagnostics.",
                    'suggestion': "Add curricular topics under course syllabus management."
                })

        sections_without_teacher = ClassSection.objects.filter(primary_teacher__isnull=True).count()
        if sections_without_teacher > 0:
            issues.append({
                'dimension': 'Curriculum Completeness',
                'severity': 'CRITICAL',
                'entity': f"{sections_without_teacher} Class Section(s)",
                'description': "Active teaching sections exist without an assigned primary faculty instructor.",
                'suggestion': "Assign primary teacher to each active section."
            })

        dim2_score = 100.0 - (courses_without_topics * 10.0) - (sections_without_teacher * 20.0)
        dim2_score = max(0.0, min(100.0, dim2_score))

        # 3. Assessment & Grading Completeness
        assessments_unweighted = 0
        assignments_no_due_date = Assignment.objects.filter(due_date__isnull=True).count()
        if assignments_no_due_date > 0:
            issues.append({
                'dimension': 'Assessment Completeness',
                'severity': 'WARNING',
                'entity': f"{assignments_no_due_date} Assignment(s)",
                'description': "Assignments exist with missing submission deadlines.",
                'suggestion': "Set explicit due date timestamps on all assignments."
            })

        dim3_score = 100.0 - (assignments_no_due_date * 10.0)
        dim3_score = max(0.0, min(100.0, dim3_score))

        # 4. Attendance Completeness
        sessions_without_records = 0
        sessions = ClassSession.objects.all()
        for sess in sessions:
            if not sess.attendance_records.exists():
                sessions_without_records += 1
                issues.append({
                    'dimension': 'Attendance Completeness',
                    'severity': 'WARNING',
                    'entity': f"Session {sess.title} ({sess.class_section.course.code})",
                    'description': f"Conducted class session has 0 attendance records recorded.",
                    'suggestion': "Submit attendance roll-call for this session."
                })

        dim4_score = 100.0 if not sessions_without_records else max(0.0, 100.0 - (sessions_without_records * 10.0))

        # 5. Enrollment Consistency
        orphan_enrollments = Enrollment.objects.filter(class_section__isnull=True).count()
        if orphan_enrollments > 0:
            issues.append({
                'dimension': 'Enrollment Consistency',
                'severity': 'CRITICAL',
                'entity': f"{orphan_enrollments} Enrollment(s)",
                'description': "Enrollment records exist without linked class sections.",
                'suggestion': "Audit and link or purge orphan enrollment records."
            })

        dim5_score = 100.0 if not orphan_enrollments else max(0.0, 100.0 - (orphan_enrollments * 25.0))

        # 6. Schedule Consistency
        conflicts_count = 0
        slots = list(ClassSchedule.objects.select_related('class_section__course').all())
        # Pairwise overlap check
        for i, s1 in enumerate(slots):
            for s2 in slots[i+1:]:
                if s1.day_of_week == s2.day_of_week and s1.room == s2.room and bool(s1.room):
                    # Check time overlap
                    if not (s1.end_time <= s2.start_time or s1.start_time >= s2.end_time):
                        conflicts_count += 1
                        issues.append({
                            'dimension': 'Schedule Consistency',
                            'severity': 'CRITICAL',
                            'entity': f"Room {s1.room} ({s1.get_day_of_week_display()})",
                            'description': f"Timetable room clash between {s1.class_section.course.code} and {s2.class_section.course.code} at {s1.start_time.strftime('%H:%M')}-{s1.end_time.strftime('%H:%M')}.",
                            'suggestion': "Adjust timetable slot times or reassign classroom."
                        })

        dim6_score = 100.0 if not conflicts_count else max(0.0, 100.0 - (conflicts_count * 20.0))

        dimension_scores = {
            'Profile Completeness': round(dim1_score, 1),
            'Curriculum Completeness': round(dim2_score, 1),
            'Assessment Completeness': round(dim3_score, 1),
            'Attendance Completeness': round(dim4_score, 1),
            'Enrollment Consistency': round(dim5_score, 1),
            'Schedule Consistency': round(dim6_score, 1),
        }

        overall_score = round(sum(dimension_scores.values()) / len(dimension_scores), 1)
        critical_count = sum(1 for iss in issues if iss['severity'] == 'CRITICAL')
        warning_count = sum(1 for iss in issues if iss['severity'] == 'WARNING')

        return {
            'overall_score': overall_score,
            'critical_count': critical_count,
            'warning_count': warning_count,
            'dimension_scores': dimension_scores,
            'issues': issues,
            'total_issues': len(issues),
            'is_healthy': critical_count == 0 and overall_score >= 90.0
        }
