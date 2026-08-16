"""
Interventions app configuration.
"""

from django.apps import AppConfig


class InterventionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.interventions'
    label = 'interventions'
    verbose_name = 'Closed-Loop Academic Interventions'
