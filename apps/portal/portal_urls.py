"""
Role portal URL routing (Student, Teacher, Dispatcher).
"""

from django.urls import path
from .views.dispatcher import PortalDispatcherView
from .views import student as student_views
from .views import teacher as teacher_views
from apps.analytics import views as analytics_views

app_name = 'portal'

urlpatterns = [
    # Role Dispatcher
    path('', PortalDispatcherView.as_view(), name='dispatcher'),
    path('api/search/', __import__('apps.portal.views.search_view', fromlist=['GlobalSearchAPIView']).GlobalSearchAPIView.as_view(), name='global_search_api'),

    # =========================================================================
    # Student Portal Routes
    # =========================================================================
    path('student/', student_views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('student/courses/', student_views.StudentCoursesView.as_view(), name='student_courses'),
    path('student/courses/<int:section_id>/', student_views.StudentCourseDetailView.as_view(), name='student_course_detail'),
    path('student/attendance/', student_views.StudentAttendanceView.as_view(), name='student_attendance'),
    path('student/assignments/', student_views.StudentAssignmentsView.as_view(), name='student_assignments'),
    path('student/assignments/<int:assignment_id>/submit/', student_views.StudentAssignmentSubmitView.as_view(), name='student_assignment_submit'),
    path('student/grades/', student_views.StudentGradesView.as_view(), name='student_grades'),
    path('student/timetable/', student_views.StudentTimetableView.as_view(), name='student_timetable'),
    path('student/resources/', student_views.StudentResourcesView.as_view(), name='student_resources'),
    path('student/transcript/', __import__('apps.portal.views.reporting_views', fromlist=['StudentTranscriptView']).StudentTranscriptView.as_view(), name='student_transcript'),
    path('student/transcript/csv/', __import__('apps.portal.views.reporting_views', fromlist=['StudentTranscriptCSVExportView']).StudentTranscriptCSVExportView.as_view(), name='student_transcript_csv'),
    path('student/timeline/', student_views.StudentTimelineView.as_view(), name='student_timeline'),
    path('student/journey/', student_views.StudentJourneyView.as_view(), name='student_journey'),
    path('student/analytics/', analytics_views.StudentAnalyticsOverviewView.as_view(), name='student_analytics'),
    path('student/what-if/', analytics_views.StudentWhatIfSimulatorView.as_view(), name='student_what_if'),
    path('student/interventions/', __import__('apps.interventions.views', fromlist=['StudentInterventionListView']).StudentInterventionListView.as_view(), name='student_interventions'),
    path('student/interventions/<int:pk>/', __import__('apps.interventions.views', fromlist=['StudentInterventionDetailView']).StudentInterventionDetailView.as_view(), name='student_intervention_detail'),
    path('student/interventions/<int:pk>/acknowledge/', __import__('apps.interventions.views', fromlist=['StudentInterventionAcknowledgeView']).StudentInterventionAcknowledgeView.as_view(), name='student_intervention_acknowledge'),
    path('student/interventions/<int:pk>/actions/<int:action_id>/toggle/', __import__('apps.interventions.views', fromlist=['StudentActionToggleView']).StudentActionToggleView.as_view(), name='student_intervention_action_toggle'),

    # Student AI Academic Copilot & Planner
    path('student/ai/', __import__('apps.ai_service.views', fromlist=['StudentAICopilotView']).StudentAICopilotView.as_view(), name='student_ai_copilot'),
    path('student/ai/chat/', __import__('apps.ai_service.views', fromlist=['StudentAIChatAPIView']).StudentAIChatAPIView.as_view(), name='student_ai_chat_api'),
    path('student/ai/planner/', __import__('apps.ai_service.views', fromlist=['StudentAIStudyPlannerView']).StudentAIStudyPlannerView.as_view(), name='student_ai_planner'),
    path('student/ai/explain/', __import__('apps.ai_service.views', fromlist=['StudentAIExplanationAPIView']).StudentAIExplanationAPIView.as_view(), name='student_ai_explain_api'),
    path('student/ai/feedback/', __import__('apps.ai_service.views', fromlist=['StudentAIFeedbackAPIView']).StudentAIFeedbackAPIView.as_view(), name='student_ai_feedback_api'),
    path('student/ai/conversation/<int:pk>/delete/', __import__('apps.ai_service.views', fromlist=['StudentAIDeleteConversationView']).StudentAIDeleteConversationView.as_view(), name='student_ai_delete_conversation'),

    # =========================================================================
    # Teacher Portal Routes
    # =========================================================================
    path('teacher/', teacher_views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/classes/', teacher_views.TeacherClassesView.as_view(), name='teacher_classes'),
    path('teacher/classes/<int:section_id>/', teacher_views.TeacherClassDetailView.as_view(), name='teacher_class_detail'),
    path('teacher/classes/<int:section_id>/export/', __import__('apps.portal.views.reporting_views', fromlist=['TeacherSectionCSVExportView']).TeacherSectionCSVExportView.as_view(), name='teacher_section_export'),
    path('teacher/classes/<int:section_id>/analytics/', analytics_views.TeacherClassAnalyticsView.as_view(), name='teacher_class_analytics'),
    path('teacher/classes/<int:section_id>/course-intelligence/', teacher_views.TeacherCourseIntelligenceView.as_view(), name='teacher_course_intelligence'),
    path('teacher/assessments/<int:assessment_id>/intelligence/', teacher_views.TeacherAssessmentIntelligenceView.as_view(), name='teacher_assessment_intelligence'),
    path('teacher/classes/<int:section_id>/briefing/', __import__('apps.ai_service.views', fromlist=['TeacherClassBriefingView']).TeacherClassBriefingView.as_view(), name='teacher_class_briefing'),
    path('teacher/analytics/', analytics_views.TeacherClassAnalyticsView.as_view(), name='teacher_analytics'),
    path('teacher/early-warnings/', analytics_views.TeacherEarlyWarningsView.as_view(), name='teacher_early_warnings'),
    path('teacher/early-warnings-timeline/', teacher_views.TeacherEarlyWarningsView.as_view(), name='teacher_early_warnings_timeline'),
    path('teacher/interventions/', __import__('apps.interventions.views', fromlist=['TeacherInterventionCenterView']).TeacherInterventionCenterView.as_view(), name='teacher_interventions'),

    # Teacher AI Academic Copilot
    path('teacher/ai/', __import__('apps.ai_service.views', fromlist=['TeacherAICopilotView']).TeacherAICopilotView.as_view(), name='teacher_ai_copilot'),
    path('teacher/ai/chat/', __import__('apps.ai_service.views', fromlist=['TeacherAIChatAPIView']).TeacherAIChatAPIView.as_view(), name='teacher_ai_chat_api'),
    path('teacher/ai/student-summary/', __import__('apps.ai_service.views', fromlist=['TeacherStudentBriefingAPIView']).TeacherStudentBriefingAPIView.as_view(), name='teacher_ai_student_summary_api'),
    path('teacher/interventions/scan/', __import__('apps.interventions.views', fromlist=['TeacherScanRecommendationsView']).TeacherScanRecommendationsView.as_view(), name='teacher_intervention_scan'),
    path('teacher/interventions/<int:pk>/', __import__('apps.interventions.views', fromlist=['TeacherInterventionDetailView']).TeacherInterventionDetailView.as_view(), name='teacher_intervention_detail'),
    path('teacher/interventions/<int:pk>/approve/', __import__('apps.interventions.views', fromlist=['TeacherRecommendationApproveView']).TeacherRecommendationApproveView.as_view(), name='teacher_intervention_approve'),
    path('teacher/interventions/<int:pk>/dismiss/', __import__('apps.interventions.views', fromlist=['TeacherRecommendationDismissView']).TeacherRecommendationDismissView.as_view(), name='teacher_intervention_dismiss'),
    path('teacher/interventions/<int:pk>/actions/add/', __import__('apps.interventions.views', fromlist=['TeacherActionAddView']).TeacherActionAddView.as_view(), name='teacher_intervention_action_add'),
    path('teacher/interventions/<int:pk>/actions/<int:action_id>/update/', __import__('apps.interventions.views', fromlist=['TeacherActionUpdateView']).TeacherActionUpdateView.as_view(), name='teacher_intervention_action_update'),
    path('teacher/interventions/<int:pk>/checkpoint/', __import__('apps.interventions.views', fromlist=['TeacherCheckpointRecordView']).TeacherCheckpointRecordView.as_view(), name='teacher_intervention_checkpoint'),
    path('teacher/interventions/<int:pk>/evaluate/', __import__('apps.interventions.views', fromlist=['TeacherEvaluateOutcomeView']).TeacherEvaluateOutcomeView.as_view(), name='teacher_intervention_evaluate'),
    path('teacher/interventions/<int:pk>/close/', __import__('apps.interventions.views', fromlist=['TeacherCloseInterventionView']).TeacherCloseInterventionView.as_view(), name='teacher_intervention_close'),
    path('teacher/interventions/<int:pk>/escalate/', __import__('apps.interventions.views', fromlist=['TeacherEscalateInterventionView']).TeacherEscalateInterventionView.as_view(), name='teacher_intervention_escalate'),
    path('teacher/attendance/', teacher_views.TeacherAttendanceView.as_view(), name='teacher_attendance'),
    path('teacher/attendance/take/<int:section_id>/', teacher_views.TeacherTakeAttendanceView.as_view(), name='teacher_take_attendance'),
    path('teacher/assignments/', teacher_views.TeacherAssignmentsView.as_view(), name='teacher_assignments'),
    path('teacher/assignments/create/', teacher_views.TeacherAssignmentCreateView.as_view(), name='teacher_assignment_create'),
    path('teacher/assignments/<int:pk>/edit/', teacher_views.TeacherAssignmentEditView.as_view(), name='teacher_assignment_edit'),
    path('teacher/assignments/<int:pk>/delete/', teacher_views.TeacherAssignmentDeleteView.as_view(), name='teacher_assignment_delete'),
    path('teacher/assignments/<int:assignment_id>/submissions/', teacher_views.TeacherAssignmentSubmissionsView.as_view(), name='teacher_assignment_submissions'),
    path('teacher/submissions/<int:submission_id>/grade/', teacher_views.TeacherGradeSubmissionView.as_view(), name='teacher_grade_submission'),

    path('teacher/assessments/create/', teacher_views.TeacherAssessmentCreateView.as_view(), name='teacher_assessment_create'),
    path('teacher/assessments/<int:pk>/enter-marks/', teacher_views.TeacherAssessmentEnterMarksView.as_view(), name='teacher_assessment_enter_marks'),

    path('teacher/gradebook/', teacher_views.TeacherGradebookView.as_view(), name='teacher_gradebook'),
    path('teacher/gradebook/<int:section_id>/publish/', teacher_views.TeacherPublishGradesView.as_view(), name='teacher_publish_grades'),
    path('teacher/timetable/', teacher_views.TeacherTimetableView.as_view(), name='teacher_timetable'),

    path('teacher/resources/', teacher_views.TeacherResourceListView.as_view(), name='teacher_resources'),
    path('teacher/resources/create/', teacher_views.TeacherResourceCreateView.as_view(), name='teacher_resource_create'),
    path('teacher/resources/<int:pk>/delete/', teacher_views.TeacherResourceDeleteView.as_view(), name='teacher_resource_delete'),

    path('teacher/announcements/create/', teacher_views.TeacherAnnouncementCreateView.as_view(), name='teacher_announcement_create'),
    path('teacher/announcements/<int:pk>/delete/', teacher_views.TeacherAnnouncementDeleteView.as_view(), name='teacher_announcement_delete'),
]
