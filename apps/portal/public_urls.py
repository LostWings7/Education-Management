"""
Public website URL routing.
"""

from django.urls import path
from .views import HomeView, CoursesCatalogView, CourseDetailView, ContactView

app_name = 'public'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('courses/', CoursesCatalogView.as_view(), name='courses'),
    path('courses/<str:code>/', CourseDetailView.as_view(), name='course_detail'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('demo/', __import__('apps.portal.views.demo_views', fromlist=['DemoShowcaseView']).DemoShowcaseView.as_view(), name='demo_showcase'),
    path('demo/rescue/execute-step/', __import__('apps.portal.views.demo_views', fromlist=['DemoExecuteRescueStepView']).DemoExecuteRescueStepView.as_view(), name='demo_execute_rescue_step'),
]
