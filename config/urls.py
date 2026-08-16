"""
URL Configuration for Education Management Portal.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

urlpatterns = [
    # Chrome DevTools Workspace discovery endpoint
    path('.well-known/appspecific/com.chrome.devtools.json', lambda request: JsonResponse({})),

    # Django Built-in Administration Interface
    path('django-admin/', admin.site.urls),

    # Custom Education Management Portal Admin Dashboard
    path('admin/', include('apps.portal.admin_urls', namespace='portal_admin')),

    # Notifications & Preferences
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),

    # Core Authentication and Identity URLs
    path('accounts/', include('apps.core.urls', namespace='core')),

    # Role Portals and Dispatcher
    path('portal/', include('apps.portal.portal_urls', namespace='portal')),

    # System Health Check Endpoint
    path('health/', __import__('apps.portal.views.health_view', fromlist=['HealthCheckView']).HealthCheckView.as_view(), name='health_check'),

    # Public Website URLs
    path('', include('apps.portal.public_urls', namespace='public')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
