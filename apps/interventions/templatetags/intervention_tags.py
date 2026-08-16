"""
Template tags and filters for Phase 4 Interventions UI.
"""

from django import template
from django.utils.safestring import mark_safe
from apps.interventions.models import Intervention, InterventionAction, InterventionEvaluation

register = template.Library()


@register.filter(name='intervention_status_badge')
def intervention_status_badge(status: str) -> str:
    """Render a styled badge for an intervention lifecycle status."""
    badge_map = {
        Intervention.Status.RECOMMENDED: ('badge-warning', 'Recommended'),
        Intervention.Status.APPROVED: ('badge-info', 'Approved'),
        Intervention.Status.CREATED: ('badge-info', 'Created'),
        Intervention.Status.ASSIGNED: ('badge-primary', 'Assigned'),
        Intervention.Status.IN_PROGRESS: ('badge-info', 'In Progress'),
        Intervention.Status.COMPLETED: ('badge-success', 'Completed'),
        Intervention.Status.EVALUATING: ('badge-warning', 'Evaluating'),
        Intervention.Status.EFFECTIVE: ('badge-success', 'Effective'),
        Intervention.Status.PARTIALLY_EFFECTIVE: ('badge-warning', 'Partially Effective'),
        Intervention.Status.NO_MEASURABLE_CHANGE: ('badge-neutral', 'No Measurable Change'),
        Intervention.Status.INEFFECTIVE: ('badge-danger', 'Ineffective'),
        Intervention.Status.ESCALATED: ('badge-danger', 'Escalated'),
        Intervention.Status.DISMISSED: ('badge-neutral', 'Dismissed'),
        Intervention.Status.CLOSED: ('badge-neutral', 'Closed')
    }
    css_class, label = badge_map.get(status, ('badge-neutral', status))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter(name='intervention_priority_badge')
def intervention_priority_badge(priority: str) -> str:
    """Render a styled badge for an intervention priority level."""
    badge_map = {
        Intervention.Priority.URGENT: ('badge-danger', 'URGENT'),
        Intervention.Priority.HIGH: ('badge-danger', 'HIGH'),
        Intervention.Priority.MEDIUM: ('badge-warning', 'MEDIUM'),
        Intervention.Priority.LOW: ('badge-success', 'LOW')
    }
    css_class, label = badge_map.get(priority, ('badge-neutral', priority))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter(name='action_status_badge')
def action_status_badge(status: str) -> str:
    """Render a styled badge for an action item status."""
    badge_map = {
        InterventionAction.ActionStatus.PENDING: ('badge-neutral', 'Pending'),
        InterventionAction.ActionStatus.IN_PROGRESS: ('badge-info', 'In Progress'),
        InterventionAction.ActionStatus.COMPLETED: ('badge-success', 'Completed'),
        InterventionAction.ActionStatus.SKIPPED: ('badge-neutral', 'Skipped')
    }
    css_class, label = badge_map.get(status, ('badge-neutral', status))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter(name='effectiveness_badge')
def effectiveness_badge(classification: str) -> str:
    """Render a styled badge for evaluation outcome."""
    badge_map = {
        InterventionEvaluation.EffectivenessClassification.EFFECTIVE: ('badge-success', 'Effective'),
        InterventionEvaluation.EffectivenessClassification.PARTIALLY_EFFECTIVE: ('badge-warning', 'Partially Effective'),
        InterventionEvaluation.EffectivenessClassification.NO_MEASURABLE_CHANGE: ('badge-neutral', 'No Measurable Change'),
        InterventionEvaluation.EffectivenessClassification.INEFFECTIVE: ('badge-danger', 'Ineffective'),
        InterventionEvaluation.EffectivenessClassification.INSUFFICIENT_DATA: ('badge-warning', 'Insufficient Data')
    }
    css_class, label = badge_map.get(classification, ('badge-neutral', classification))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')
