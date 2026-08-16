"""
URL patterns for AI service endpoints.
"""

from django.urls import path
from .views import (
    StudentAICopilotView,
    StudentAIChatAPIView,
    StudentAIStudyPlannerView,
    StudentAIExplanationAPIView,
    StudentAIFeedbackAPIView,
    StudentAIDeleteConversationView,
    TeacherAICopilotView,
    TeacherAIChatAPIView,
    TeacherClassBriefingView,
    TeacherStudentBriefingAPIView,
    AdminAIIntelligenceView,
    AdminAIChatAPIView
)

app_name = 'ai_service'

urlpatterns = [
    # Student Endpoints
    path('student/copilot/', StudentAICopilotView.as_view(), name='student_copilot'),
    path('student/chat/', StudentAIChatAPIView.as_view(), name='student_chat_api'),
    path('student/planner/', StudentAIStudyPlannerView.as_view(), name='student_study_planner'),
    path('student/explain/', StudentAIExplanationAPIView.as_view(), name='student_explain_api'),
    path('student/feedback/', StudentAIFeedbackAPIView.as_view(), name='student_feedback_api'),
    path('student/conversation/<int:pk>/delete/', StudentAIDeleteConversationView.as_view(), name='student_delete_conversation'),

    # Teacher Endpoints
    path('teacher/copilot/', TeacherAICopilotView.as_view(), name='teacher_copilot'),
    path('teacher/chat/', TeacherAIChatAPIView.as_view(), name='teacher_chat_api'),
    path('teacher/briefing/<int:section_id>/', TeacherClassBriefingView.as_view(), name='teacher_class_briefing'),
    path('teacher/student-summary/', TeacherStudentBriefingAPIView.as_view(), name='teacher_student_summary_api'),

    # Admin Endpoints
    path('admin/intelligence/', AdminAIIntelligenceView.as_view(), name='admin_intelligence'),
    path('admin/chat/', AdminAIChatAPIView.as_view(), name='admin_chat_api'),
]
