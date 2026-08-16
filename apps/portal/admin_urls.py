"""
Custom Administrator portal URL routing for comprehensive Phase 2.5 Academic Management.
"""

from django.urls import path
from .views import admin as admin_views

app_name = 'portal_admin'

urlpatterns = [
    # Dashboard
    path('', admin_views.AdminDashboardView.as_view(), name='dashboard'),

    # Departments
    path('departments/', admin_views.AdminDepartmentListView.as_view(), name='department_list'),
    path('departments/list/', admin_views.AdminDepartmentListView.as_view(), name='departments'),
    path('departments/create/', admin_views.AdminDepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', admin_views.AdminDepartmentEditView.as_view(), name='department_edit'),
    path('departments/<int:pk>/toggle-status/', admin_views.AdminDepartmentToggleStatusView.as_view(), name='department_toggle_status'),

    # Programs
    path('programs/', admin_views.AdminProgramListView.as_view(), name='program_list'),
    path('programs/list/', admin_views.AdminProgramListView.as_view(), name='programs'),
    path('programs/create/', admin_views.AdminProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/edit/', admin_views.AdminProgramEditView.as_view(), name='program_edit'),
    path('programs/<int:pk>/toggle-status/', admin_views.AdminProgramToggleStatusView.as_view(), name='program_toggle_status'),

    # Academic Periods / Terms
    path('terms/', admin_views.AdminTermsListView.as_view(), name='terms_list'),
    path('terms/list/', admin_views.AdminTermsListView.as_view(), name='terms'),
    path('terms/years/create/', admin_views.AdminYearCreateView.as_view(), name='year_create'),
    path('terms/years/<int:pk>/edit/', admin_views.AdminYearEditView.as_view(), name='year_edit'),
    path('terms/semesters/create/', admin_views.AdminSemesterCreateView.as_view(), name='semester_create'),
    path('terms/semesters/<int:pk>/edit/', admin_views.AdminSemesterEditView.as_view(), name='semester_edit'),
    path('terms/semesters/<int:pk>/set-active/', admin_views.AdminSemesterToggleActiveView.as_view(), name='semester_toggle_active'),

    # Students
    path('students/', admin_views.AdminStudentListView.as_view(), name='student_list'),
    path('students/list/', admin_views.AdminStudentListView.as_view(), name='students'),
    path('students/create/', admin_views.AdminStudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/edit/', admin_views.AdminStudentEditView.as_view(), name='student_edit'),
    path('students/<int:pk>/toggle-status/', admin_views.AdminStudentToggleStatusView.as_view(), name='student_toggle_status'),

    # Teachers
    path('teachers/', admin_views.AdminTeacherListView.as_view(), name='teacher_list'),
    path('teachers/list/', admin_views.AdminTeacherListView.as_view(), name='teachers'),
    path('teachers/create/', admin_views.AdminTeacherCreateView.as_view(), name='teacher_create'),
    path('teachers/<int:pk>/edit/', admin_views.AdminTeacherEditView.as_view(), name='teacher_edit'),
    path('teachers/<int:pk>/toggle-status/', admin_views.AdminTeacherToggleStatusView.as_view(), name='teacher_toggle_status'),

    # Courses & Topics
    path('courses/', admin_views.AdminCoursesView.as_view(), name='courses'),
    path('courses/create/', admin_views.AdminCourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/edit/', admin_views.AdminCourseEditView.as_view(), name='course_edit'),
    path('courses/<int:pk>/toggle-status/', admin_views.AdminCourseToggleStatusView.as_view(), name='course_toggle_status'),
    path('courses/<int:course_id>/topics/create/', admin_views.AdminTopicCreateView.as_view(), name='topic_create'),
    path('courses/<int:course_id>/topics/<int:topic_id>/delete/', admin_views.AdminTopicDeleteView.as_view(), name='topic_delete'),

    # Class Sections
    path('sections/', admin_views.AdminSectionsView.as_view(), name='sections'),
    path('sections/create/', admin_views.AdminSectionCreateView.as_view(), name='section_create'),
    path('sections/<int:pk>/edit/', admin_views.AdminSectionEditView.as_view(), name='section_edit'),
    path('sections/<int:pk>/toggle-status/', admin_views.AdminSectionToggleStatusView.as_view(), name='section_toggle_status'),
    path('sections/<int:pk>/roster/', admin_views.AdminSectionRosterView.as_view(), name='section_roster'),

    # Enrollments
    path('enrollments/', admin_views.AdminEnrollmentsView.as_view(), name='enrollments'),
    path('enrollments/create/', admin_views.AdminEnrollmentCreateView.as_view(), name='enrollment_create'),
    path('enrollments/<int:pk>/drop/', admin_views.AdminEnrollmentDropView.as_view(), name='enrollment_drop'),
    path('enrollments/<int:pk>/re-enroll/', admin_views.AdminEnrollmentReEnrollView.as_view(), name='enrollment_re_enroll'),

    # Timetable
    path('timetable/', admin_views.AdminTimetableView.as_view(), name='timetable'),
    path('timetable/create/', admin_views.AdminTimetableCreateView.as_view(), name='timetable_create'),
    path('timetable/<int:pk>/delete/', admin_views.AdminTimetableDeleteView.as_view(), name='timetable_delete'),

    # Attendance Oversight
    path('attendance/', admin_views.AdminAttendanceListView.as_view(), name='attendance_list'),
    path('attendance/<int:pk>/', admin_views.AdminAttendanceSessionDetailView.as_view(), name='attendance_detail'),

    # Assessments & Grades
    path('assessments/', admin_views.AdminAssessmentListView.as_view(), name='assessment_list'),
    path('grades/<int:enrollment_id>/recalculate/', admin_views.AdminGradeRecalculateView.as_view(), name='grade_recalculate'),

    # Resources & Announcements
    path('resources/', admin_views.AdminResourceListView.as_view(), name='resource_list'),
    path('resources/<int:pk>/delete/', admin_views.AdminResourceDeleteView.as_view(), name='resource_delete'),
    path('announcements/', admin_views.AdminAnnouncementListView.as_view(), name='announcement_list'),
    path('announcements/<int:pk>/delete/', admin_views.AdminAnnouncementDeleteView.as_view(), name='announcement_delete'),

    # Academic Records Search
    path('records/', admin_views.AdminAcademicRecordsView.as_view(), name='records'),

    # Institutional Analytics & Intelligence
    path('analytics/', __import__('apps.analytics.views', fromlist=['AdminInstitutionAnalyticsView']).AdminInstitutionAnalyticsView.as_view(), name='analytics'),
    path('risk-heatmap/', admin_views.AdminRiskHeatmapView.as_view(), name='risk_heatmap'),

    # Institutional Academic Interventions Oversight
    path('interventions/', __import__('apps.interventions.views', fromlist=['AdminInterventionOverviewView']).AdminInterventionOverviewView.as_view(), name='interventions_overview'),
    path('interventions/outcomes/', admin_views.AdminInterventionOutcomeView.as_view(), name='intervention_outcomes'),
    path('interventions/<int:pk>/', __import__('apps.interventions.views', fromlist=['AdminInterventionDetailView']).AdminInterventionDetailView.as_view(), name='intervention_detail'),

    # Academic Data Quality Center
    path('data-quality/', __import__('apps.portal.views.admin_data_quality_view', fromlist=['AdminDataQualityView']).AdminDataQualityView.as_view(), name='data_quality'),

    # Institutional AI Intelligence Hub
    path('ai/', __import__('apps.ai_service.views', fromlist=['AdminAIIntelligenceView']).AdminAIIntelligenceView.as_view(), name='ai_intelligence'),
    path('ai/observability/', __import__('apps.ai_service.views.admin_views', fromlist=['AdminAIObservabilityView']).AdminAIObservabilityView.as_view(), name='ai_observability'),
    path('ai/chat/', __import__('apps.ai_service.views', fromlist=['AdminAIChatAPIView']).AdminAIChatAPIView.as_view(), name='ai_chat_api'),

    # Institutional Reporting & CSV Exports
    path('reports/institutional/csv/', __import__('apps.portal.views.reporting_views', fromlist=['AdminInstitutionalCSVExportView']).AdminInstitutionalCSVExportView.as_view(), name='export_institutional_csv'),
    path('reports/interventions/csv/', __import__('apps.portal.views.reporting_views', fromlist=['AdminInterventionsCSVExportView']).AdminInterventionsCSVExportView.as_view(), name='export_interventions_csv'),
]
