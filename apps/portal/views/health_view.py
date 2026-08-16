"""
System Health Check View and Diagnostics.
Never exposes secret keys, passwords, or sensitive environment values.
"""

import os
from django.views import View
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from apps.core.models import User
from apps.ai_service.providers.factory import get_ai_provider


class HealthCheckView(View):
    """
    Public / monitoring health check endpoint.
    """

    def get(self, request):
        checks = {}
        is_healthy = True

        # 1. Database Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                checks['database'] = 'HEALTHY' if row and row[0] == 1 else 'ERROR'
        except Exception as e:
            checks['database'] = f'ERROR: {type(e).__name__}'
            is_healthy = False

        # 2. AI Service Check
        try:
            provider = get_ai_provider()
            checks['ai_provider'] = f"HEALTHY ({provider.provider_name}, online={provider.is_online})"
        except Exception as e:
            checks['ai_provider'] = f'ERROR: {type(e).__name__}'

        # 3. Storage Directory Check
        media_root = getattr(settings, 'MEDIA_ROOT', '')
        if media_root and os.path.exists(media_root):
            checks['media_storage'] = 'HEALTHY'
        else:
            checks['media_storage'] = 'WARNING (Directory not created)'

        # 4. Auth & User Table Check
        try:
            u_count = User.objects.count()
            checks['auth_system'] = f"HEALTHY ({u_count} registered users)"
        except Exception:
            checks['auth_system'] = 'ERROR'
            is_healthy = False

        status_code = 200 if is_healthy else 503
        return JsonResponse({
            'status': 'HEALTHY' if is_healthy else 'UNHEALTHY',
            'checks': checks
        }, status=status_code)
