"""
Global Role-Scoped Search & Quick Action Service.
Enforces strict database-level RBAC filtering across search queries.
Never exposes cross-user or institutional records to unauthorized roles.
"""

from typing import Dict, Any, List
from django.urls import reverse
from django.db.models import Q
from apps.core.models import User
from apps.academic.models import (
    StudentProfile,
    TeacherProfile,
    Department,
    Program,
    Course,
    Topic,
    ClassSection,
    Assignment,
    LearningResource,
    CourseAnnouncement
)
from apps.interventions.models import Intervention


class GlobalSearchService:
    """
    Executes role-scoped global searches.
    """

    @classmethod
    def search(cls, user: User, query: str) -> List[Dict[str, Any]]:
        """
        Main search dispatcher enforcing user role scope.
        """
        q = query.strip()
        if not q or len(q) < 2:
            return []

        if user.is_student:
            student = getattr(user, 'student_profile', None)
            return cls._search_student(student, q) if student else []
        elif user.is_teacher:
            teacher = getattr(user, 'teacher_profile', None)
            return cls._search_teacher(teacher, q) if teacher else []
        elif user.is_administrator or user.is_superuser:
            return cls._search_admin(q)

        return []

    @classmethod
    def _search_student(cls, student: StudentProfile, q: str) -> List[Dict[str, Any]]:
        results = []

        # 1. Enrolled Courses
        enrolled_courses = Course.objects.filter(
            sections__enrollments__student=student,
            sections__enrollments__status='ENROLLED'
        ).filter(Q(code__icontains=q) | Q(title__icontains=q)).distinct()

        for c in enrolled_courses[:4]:
            sec = c.sections.filter(enrollments__student=student).first()
            results.append({
                'title': f"{c.code} — {c.title}",
                'subtitle': f"Enrolled Course ({c.credits} credits)",
                'category': 'Course',
                'badge_class': 'badge-neutral',
                'url': reverse('portal:student_course_detail', kwargs={'section_id': sec.pk}) if sec else reverse('portal:student_courses')
            })

        # 2. Assignments
        assignments = Assignment.objects.filter(
            class_section__enrollments__student=student,
            class_section__enrollments__status='ENROLLED'
        ).filter(Q(title__icontains=q) | Q(description__icontains=q)).distinct()

        for a in assignments[:4]:
            results.append({
                'title': a.title,
                'subtitle': f"{a.class_section.course.code} (Due: {a.due_date.strftime('%b %d')})",
                'category': 'Assignment',
                'badge_class': 'badge-warning',
                'url': reverse('portal:student_assignments')
            })

        # 3. Learning Resources
        resources = LearningResource.objects.filter(
            course__sections__enrollments__student=student,
            is_published=True
        ).filter(Q(title__icontains=q) | Q(description__icontains=q)).distinct()

        for r in resources[:4]:
            results.append({
                'title': r.title,
                'subtitle': f"{r.course.code} ({r.get_resource_type_display()})",
                'category': 'Resource',
                'badge_class': 'badge-info',
                'url': reverse('portal:student_resources')
            })

        return results

    @classmethod
    def _search_teacher(cls, teacher: TeacherProfile, q: str) -> List[Dict[str, Any]]:
        results = []

        # 1. Assigned Sections
        sections = ClassSection.objects.filter(
            primary_teacher=teacher,
            semester__is_active=True
        ).filter(Q(course__code__icontains=q) | Q(course__title__icontains=q) | Q(section_code__icontains=q))

        for s in sections[:4]:
            results.append({
                'title': f"{s.course.code} (Sec {s.section_code})",
                'subtitle': s.course.title,
                'category': 'Section',
                'badge_class': 'badge-neutral',
                'url': reverse('portal:teacher_class_detail', kwargs={'section_id': s.pk})
            })

        # 2. Enrolled Students
        enrolled_students = StudentProfile.objects.filter(
            enrollments__class_section__primary_teacher=teacher,
            enrollments__status='ENROLLED'
        ).filter(
            Q(student_id__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q)
        ).distinct()

        for st in enrolled_students[:5]:
            results.append({
                'title': st.user.get_full_name(),
                'subtitle': f"ID: {st.student_id} ({st.program.code if st.program else 'Student'})",
                'category': 'Student',
                'badge_class': 'badge-info',
                'url': reverse('portal:teacher_classes')
            })

        # 3. Interventions
        intvs = Intervention.objects.filter(
            class_section__primary_teacher=teacher
        ).filter(Q(title__icontains=q) | Q(student__user__first_name__icontains=q) | Q(student__student_id__icontains=q))

        for iv in intvs[:4]:
            results.append({
                'title': iv.title,
                'subtitle': f"{iv.student.user.get_full_name()} ({iv.course.code})",
                'category': 'Intervention',
                'badge_class': 'badge-warning',
                'url': reverse('portal:teacher_intervention_detail', kwargs={'pk': iv.pk})
            })

        return results

    @classmethod
    def _search_admin(cls, q: str) -> List[Dict[str, Any]]:
        results = []

        # 1. Students
        students = StudentProfile.objects.filter(
            Q(student_id__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q)
        ).select_related('user', 'program')[:4]

        for s in students:
            results.append({
                'title': s.user.get_full_name(),
                'subtitle': f"ID: {s.student_id} ({s.program.name if s.program else 'Student'})",
                'category': 'Student',
                'badge_class': 'badge-info',
                'url': reverse('portal_admin:student_list')
            })

        # 2. Faculty
        teachers = TeacherProfile.objects.filter(
            Q(employee_id__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q)
        ).select_related('user', 'department')[:4]

        for t in teachers:
            results.append({
                'title': t.user.get_full_name(),
                'subtitle': f"Faculty ({t.department.name if t.department else 'Faculty'})",
                'category': 'Faculty',
                'badge_class': 'badge-neutral',
                'url': reverse('portal_admin:teacher_list')
            })

        # 3. Courses
        courses = Course.objects.filter(Q(code__icontains=q) | Q(title__icontains=q))[:4]
        for c in courses:
            results.append({
                'title': f"{c.code} — {c.title}",
                'subtitle': f"Curricular Course ({c.credits} cr)",
                'category': 'Course',
                'badge_class': 'badge-neutral',
                'url': reverse('portal_admin:courses')
            })

        return results
