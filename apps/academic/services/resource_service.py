"""
Learning resources and announcements service.
"""

from typing import Optional, List
from django.db import transaction
from apps.academic.models import (
    Course,
    Topic,
    ClassSection,
    LearningResource,
    CourseAnnouncement,
    TeacherProfile
)
from apps.core.models import User, AuditLog


class ResourceService:
    """
    Service for querying and publishing educational materials and class announcements.
    """

    @classmethod
    def get_course_resources(
        cls,
        course: Course,
        topic: Optional[Topic] = None,
        resource_type: Optional[str] = None
    ):
        """
        Query published learning materials for a course.
        """
        qs = LearningResource.objects.filter(course=course, is_published=True).select_related('topic', 'uploaded_by')
        if topic:
            qs = qs.filter(topic=topic)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        return qs.order_by('topic__order_index', '-created_at')

    @classmethod
    @transaction.atomic
    def create_resource(
        cls,
        course: Course,
        title: str,
        resource_type: str,
        uploaded_by: User,
        description: str = '',
        topic: Optional[Topic] = None,
        file=None,
        external_url: Optional[str] = None,
        is_published: bool = True
    ) -> LearningResource:
        """
        Add a new educational resource to a course syllabus.
        """
        return LearningResource.objects.create(
            course=course,
            title=title.strip(),
            resource_type=resource_type,
            uploaded_by=uploaded_by,
            description=description.strip(),
            topic=topic,
            file=file,
            external_url=external_url,
            is_published=is_published
        )

    @classmethod
    def get_section_announcements(cls, class_section: ClassSection):
        """
        Return all announcements for a class section with pinned items first.
        """
        return CourseAnnouncement.objects.filter(
            class_section=class_section
        ).select_related('teacher__user').order_by('-is_pinned', '-created_at')

    @classmethod
    @transaction.atomic
    def create_announcement(
        cls,
        class_section: ClassSection,
        teacher: TeacherProfile,
        title: str,
        content: str,
        is_pinned: bool = False
    ) -> CourseAnnouncement:
        """
        Broadcast a new announcement to a class section.
        """
        return CourseAnnouncement.objects.create(
            class_section=class_section,
            teacher=teacher,
            title=title.strip(),
            content=content.strip(),
            is_pinned=is_pinned
        )
