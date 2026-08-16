"""
Deterministic Assignment Intelligence Service.
Calculates missing-rate, completion percentage (0.0 - 100.0), late submission rate,
average graded coursework score, and discordance indicators.
"""

from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Assignment, AssignmentSubmission, Semester
from apps.analytics.schemas.insight import AssignmentAnalyticsResult, DataQuality
from .data_preparation import AnalyticsDataPreparationService


class AssignmentAnalyticsService:
    """
    Computes assignment metrics, missing rates, and effort vs capability discordance.
    """

    @classmethod
    def calculate_course_assignments(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> AssignmentAnalyticsResult:
        """
        Calculates assignment analytics for a student in a class section.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        assignments: List[Assignment] = dataset['assignments']
        submissions: Dict[int, AssignmentSubmission] = dataset['submissions']

        total_assigned = len(assignments)

        if total_assigned == 0:
            return AssignmentAnalyticsResult(
                total_assigned=0,
                submitted_count=0,
                missing_count=0,
                on_time_count=0,
                late_count=0,
                completion_rate=100.0,
                missing_rate=0.0,
                on_time_rate=100.0,
                average_score=None,
                discordance_flag=None,
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        submitted_count = 0
        missing_count = 0
        on_time_count = 0
        late_count = 0
        obtained_marks_sum = 0.0
        max_marks_sum = 0.0

        for a in assignments:
            sub = submissions.get(a.pk)
            if sub:
                submitted_count += 1
                if sub.status == AssignmentSubmission.SubmissionStatus.LATE:
                    late_count += 1
                else:
                    on_time_count += 1

                if sub.obtained_marks is not None and a.max_marks > 0:
                    obtained_marks_sum += float(sub.obtained_marks)
                    max_marks_sum += float(a.max_marks)
            else:
                missing_count += 1

        completion_rate = (float(submitted_count) / float(total_assigned)) * 100.0
        missing_rate = (float(missing_count) / float(total_assigned)) * 100.0
        on_time_rate = (float(on_time_count) / float(submitted_count)) * 100.0 if submitted_count > 0 else 0.0
        avg_score = (obtained_marks_sum / max_marks_sum) * 100.0 if max_marks_sum > 0 else None

        discordance_flag = None
        if avg_score is not None:
            if completion_rate >= 85.0 and avg_score < 55.0:
                discordance_flag = "Underperforming Effort (High Completion / Low Score)"
            elif completion_rate < 50.0 and avg_score >= 85.0:
                discordance_flag = "Disengaged Capability (Low Completion / High Score)"

        return AssignmentAnalyticsResult(
            total_assigned=total_assigned,
            submitted_count=submitted_count,
            missing_count=missing_count,
            on_time_count=on_time_count,
            late_count=late_count,
            completion_rate=round(completion_rate, 2),
            missing_rate=round(missing_rate, 2),
            on_time_rate=round(on_time_rate, 2),
            average_score=round(avg_score, 2) if avg_score is not None else None,
            discordance_flag=discordance_flag,
            data_quality=DataQuality.VALID
        )

    @classmethod
    def calculate_overall_assignments(
        cls,
        student: StudentProfile,
        semester: Optional[Semester] = None
    ) -> AssignmentAnalyticsResult:
        """
        Calculates cumulative assignment analytics across all active courses in a semester.
        """
        dataset = AnalyticsDataPreparationService.get_student_overall_dataset(student, semester)
        course_datasets = dataset['course_datasets']

        total_assigned = 0
        total_submitted = 0
        total_missing = 0
        total_on_time = 0
        total_late = 0
        total_obtained = 0.0
        total_max = 0.0

        for cds in course_datasets:
            res = cls.calculate_course_assignments(student, cds['class_section'], dataset=cds)
            if res.data_quality != DataQuality.INSUFFICIENT_DATA:
                total_assigned += res.total_assigned
                total_submitted += res.submitted_count
                total_missing += res.missing_count
                total_on_time += res.on_time_count
                total_late += res.late_count
                if res.average_score is not None:
                    # accumulate weighted
                    for a in cds['assignments']:
                        sub = cds['submissions'].get(a.pk)
                        if sub and sub.obtained_marks is not None and a.max_marks > 0:
                            total_obtained += float(sub.obtained_marks)
                            total_max += float(a.max_marks)

        if total_assigned == 0:
            return AssignmentAnalyticsResult(
                total_assigned=0,
                submitted_count=0,
                missing_count=0,
                on_time_count=0,
                late_count=0,
                completion_rate=100.0,
                missing_rate=0.0,
                on_time_rate=100.0,
                average_score=None,
                discordance_flag=None,
                data_quality=DataQuality.INSUFFICIENT_DATA
            )

        completion_rate = (float(total_submitted) / float(total_assigned)) * 100.0
        missing_rate = (float(total_missing) / float(total_assigned)) * 100.0
        on_time_rate = (float(total_on_time) / float(total_submitted)) * 100.0 if total_submitted > 0 else 0.0
        avg_score = (total_obtained / total_max) * 100.0 if total_max > 0 else None

        discordance_flag = None
        if avg_score is not None:
            if completion_rate >= 85.0 and avg_score < 55.0:
                discordance_flag = "Underperforming Effort (High Completion / Low Score)"
            elif completion_rate < 50.0 and avg_score >= 85.0:
                discordance_flag = "Disengaged Capability (Low Completion / High Score)"

        return AssignmentAnalyticsResult(
            total_assigned=total_assigned,
            submitted_count=total_submitted,
            missing_count=total_missing,
            on_time_count=total_on_time,
            late_count=total_late,
            completion_rate=round(completion_rate, 2),
            missing_rate=round(missing_rate, 2),
            on_time_rate=round(on_time_rate, 2),
            average_score=round(avg_score, 2) if avg_score is not None else None,
            discordance_flag=discordance_flag,
            data_quality=DataQuality.VALID
        )
