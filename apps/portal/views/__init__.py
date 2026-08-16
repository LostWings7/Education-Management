"""
Portal views package.
"""

from .dispatcher import PortalDispatcherView
from .public import HomeView, CoursesCatalogView, CourseDetailView, ContactView
from .student import StudentDashboardView
from .teacher import TeacherDashboardView
from .admin import AdminDashboardView

__all__ = [
    'PortalDispatcherView',
    'HomeView',
    'CoursesCatalogView',
    'CourseDetailView',
    'ContactView',
    'StudentDashboardView',
    'TeacherDashboardView',
    'AdminDashboardView',
]
