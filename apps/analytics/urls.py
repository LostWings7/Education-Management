"""
URL configuration for apps.analytics module.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Student
    path('student/overview/', views.StudentAnalyticsOverviewView.as_view(), name='student_overview'),
    path('student/what-if/', views.StudentWhatIfSimulatorView.as_view(), name='student_what_if'),

    # Teacher
    path('teacher/classes/<int:section_id>/', views.TeacherClassAnalyticsView.as_view(), name='teacher_class'),
    path('teacher/early-warnings/', views.TeacherEarlyWarningsView.as_view(), name='teacher_early_warnings'),

    # Admin
    path('institution/', views.AdminInstitutionAnalyticsView.as_view(), name='institution_overview'),
]
