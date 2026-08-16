"""
Public website views for Education Management Portal.
"""

from django.views.generic import TemplateView
from apps.academic.models import Department, Program
from apps.core.models import User, Role


class HomeView(TemplateView):
    """
    Public landing page with institution highlights, features, and key statistics.
    """
    template_name = 'public/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)[:6]
        context['programs'] = Program.objects.filter(is_active=True)[:6]
        context['total_students'] = User.objects.filter(role=Role.STUDENT, is_active=True).count()
        context['total_teachers'] = User.objects.filter(role=Role.TEACHER, is_active=True).count()
        context['total_departments'] = Department.objects.filter(is_active=True).count()
        context['total_programs'] = Program.objects.filter(is_active=True).count()
        return context


class CoursesCatalogView(TemplateView):
    """
    Public course & program catalog view.
    """
    template_name = 'public/courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dept_filter = self.request.GET.get('department')
        query = self.request.GET.get('q', '').strip()

        programs = Program.objects.filter(is_active=True).select_related('department')
        if dept_filter:
            programs = programs.filter(department__code=dept_filter)
        if query:
            programs = programs.filter(name__icontains=query)

        context['departments'] = Department.objects.filter(is_active=True)
        context['programs'] = programs
        context['selected_dept'] = dept_filter
        context['search_query'] = query
        return context


class CourseDetailView(TemplateView):
    """
    Public course/program detail view shell.
    """
    template_name = 'public/course_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = self.kwargs.get('code')
        try:
            program = Program.objects.select_related('department').get(code=code, is_active=True)
            context['program'] = program
        except Program.DoesNotExist:
            context['program'] = None
        return context


class ContactView(TemplateView):
    """
    Public contact page.
    """
    template_name = 'public/contact.html'
