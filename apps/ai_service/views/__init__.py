from .student_views import (
    StudentAICopilotView,
    StudentAIChatAPIView,
    StudentAIStudyPlannerView,
    StudentAIExplanationAPIView,
    StudentAIFeedbackAPIView,
    StudentAIDeleteConversationView
)
from .teacher_views import (
    TeacherAICopilotView,
    TeacherAIChatAPIView,
    TeacherClassBriefingView,
    TeacherStudentBriefingAPIView
)
from .admin_views import (
    AdminAIIntelligenceView,
    AdminAIChatAPIView
)

__all__ = [
    'StudentAICopilotView',
    'StudentAIChatAPIView',
    'StudentAIStudyPlannerView',
    'StudentAIExplanationAPIView',
    'StudentAIFeedbackAPIView',
    'StudentAIDeleteConversationView',
    'TeacherAICopilotView',
    'TeacherAIChatAPIView',
    'TeacherClassBriefingView',
    'TeacherStudentBriefingAPIView',
    'AdminAIIntelligenceView',
    'AdminAIChatAPIView',
]
