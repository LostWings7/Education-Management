"""
URL configuration for apps.interventions.
"""

from django.urls import path
from . import views

app_name = 'interventions'

urlpatterns = [
    # Student Endpoints
    path('student/', views.StudentInterventionListView.as_view(), name='student_list'),
    path('student/<int:pk>/', views.StudentInterventionDetailView.as_view(), name='student_detail'),
    path('student/<int:pk>/acknowledge/', views.StudentInterventionAcknowledgeView.as_view(), name='student_acknowledge'),
    path('student/<int:pk>/actions/<int:action_id>/toggle/', views.StudentActionToggleView.as_view(), name='student_action_toggle'),

    # Teacher Endpoints
    path('teacher/', views.TeacherInterventionCenterView.as_view(), name='teacher_center'),
    path('teacher/scan/', views.TeacherScanRecommendationsView.as_view(), name='teacher_scan'),
    path('teacher/<int:pk>/', views.TeacherInterventionDetailView.as_view(), name='teacher_detail'),
    path('teacher/<int:pk>/approve/', views.TeacherRecommendationApproveView.as_view(), name='teacher_approve'),
    path('teacher/<int:pk>/dismiss/', views.TeacherRecommendationDismissView.as_view(), name='teacher_dismiss'),
    path('teacher/<int:pk>/actions/add/', views.TeacherActionAddView.as_view(), name='teacher_action_add'),
    path('teacher/<int:pk>/actions/<int:action_id>/update/', views.TeacherActionUpdateView.as_view(), name='teacher_action_update'),
    path('teacher/<int:pk>/checkpoint/', views.TeacherCheckpointRecordView.as_view(), name='teacher_checkpoint'),
    path('teacher/<int:pk>/evaluate/', views.TeacherEvaluateOutcomeView.as_view(), name='teacher_evaluate'),
    path('teacher/<int:pk>/close/', views.TeacherCloseInterventionView.as_view(), name='teacher_close'),
    path('teacher/<int:pk>/escalate/', views.TeacherEscalateInterventionView.as_view(), name='teacher_escalate'),

    # Admin Endpoints
    path('admin/', views.AdminInterventionOverviewView.as_view(), name='admin_overview'),
    path('admin/<int:pk>/', views.AdminInterventionDetailView.as_view(), name='admin_detail'),
]
