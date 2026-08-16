from django.urls import path
from .views import (
    NotificationListView,
    NotificationMarkReadAPIView,
    NotificationMarkAllReadAPIView,
    NotificationPreferencesView
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('preferences/', NotificationPreferencesView.as_view(), name='preferences'),
    path('<int:pk>/read/', NotificationMarkReadAPIView.as_view(), name='mark_read'),
    path('mark-all-read/', NotificationMarkAllReadAPIView.as_view(), name='mark_all_read'),
]
