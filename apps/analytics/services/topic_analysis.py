"""
Deterministic Topic Analysis Service.
Maps student evaluations to syllabus topics and classifies them into Strong Mastery, Developing, and Needs Attention.
"""

from typing import Dict, Any, List, Optional
from apps.academic.models import StudentProfile, ClassSection, Topic, Assessment, Assignment
from apps.analytics.schemas.insight import DataQuality
from .data_preparation import AnalyticsDataPreparationService


class TopicAnalyticsService:
    """
    Computes topic-level mastery diagnostics across syllabus components.
    """

    @classmethod
    def calculate_topic_mastery(
        cls,
        student: StudentProfile,
        class_section: ClassSection,
        dataset: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculates topic-by-topic diagnostic scores for a student in a course.
        """
        if not dataset:
            dataset = AnalyticsDataPreparationService.get_student_course_dataset(student, class_section)

        course = class_section.course
        topics = list(Topic.objects.filter(course=course).order_by('order_index'))

        assessments = dataset['assessments']
        results = dataset['results']
        assignments = dataset['assignments']
        submissions = dataset['submissions']

        topic_diagnostics = []

        for topic in topics:
            obtained_sum = 0.0
            max_sum = 0.0
            eval_count = 0

            # 1. Check assessments tagged with this topic
            for a in assessments:
                if a.topic_id == topic.pk:
                    res = results.get(a.pk)
                    if res and res.marks_obtained is not None and a.max_marks > 0:
                        obtained_sum += float(res.marks_obtained)
                        max_sum += float(a.max_marks)
                        eval_count += 1

            # 2. Check assignments tagged with this topic
            for assign in assignments:
                if assign.topic_id == topic.pk:
                    sub = submissions.get(assign.pk)
                    if sub and sub.obtained_marks is not None and assign.max_marks > 0:
                        obtained_sum += float(sub.obtained_marks)
                        max_sum += float(assign.max_marks)
                        eval_count += 1

            if max_sum > 0:
                score_pct = (obtained_sum / max_sum) * 100.0
                if score_pct >= 75.0:
                    status = "STRONG_MASTERY"
                    label = "Strong Mastery"
                elif score_pct >= 60.0:
                    status = "DEVELOPING"
                    label = "Developing"
                else:
                    status = "NEEDS_ATTENTION"
                    label = "Needs Attention"
                data_quality = DataQuality.VALID
            else:
                score_pct = None
                status = "NO_EVALUATIONS"
                label = "No Evaluations Yet"
                data_quality = DataQuality.INSUFFICIENT_DATA

            topic_diagnostics.append({
                'topic_id': topic.pk,
                'order_index': topic.order_index,
                'title': topic.title,
                'score_percentage': round(score_pct, 1) if score_pct is not None else None,
                'status': status,
                'status_label': label,
                'evaluations_count': eval_count,
                'data_quality': data_quality
            })

        return topic_diagnostics
