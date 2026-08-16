"""
AI Service app configuration.
"""

from django.apps import AppConfig


class AIServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_service'
    label = 'ai_service'
    verbose_name = 'AI Academic Assistant & Explanation Service'
