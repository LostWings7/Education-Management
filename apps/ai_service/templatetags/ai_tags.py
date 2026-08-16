"""
Template tags for Phase 5 AI Intelligence Layer.
Provides provider status indicators, classification pills, and markdown formatting.
"""

from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from apps.ai_service.providers.factory import get_ai_provider

register = template.Library()


@register.simple_tag
def ai_provider_status_indicator():
    """
    Renders subtle status pill showing active AI intelligence mode.
    """
    provider = get_ai_provider()
    if provider.is_online:
        return mark_safe(
            '<span class="badge" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 0.35rem;" title="Connected to Google Gemini Model">'
            '<span style="width: 7px; height: 7px; border-radius: 50%; background: #3b82f6; display: inline-block;"></span>'
            'Online Intelligence'
            '</span>'
        )
    return mark_safe(
        '<span class="badge" style="background: #fffbeb; color: #b45309; border: 1px solid #fde68a; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 0.35rem;" title="Operating in Local Deterministic Mode">'
        '<span style="width: 7px; height: 7px; border-radius: 50%; background: #f59e0b; display: inline-block;"></span>'
        'Local Intelligence'
        '</span>'
    )


@register.filter(name='classification_pill')
def classification_pill(classification: str):
    """
    Renders 6-tier classification badge.
    """
    styles = {
        'FACT': 'background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;',
        'CALCULATION': 'background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;',
        'SIMULATION': 'background: #faf5ff; color: #6b21a8; border: 1px solid #e9d5ff;',
        'ACTION': 'background: #fff7ed; color: #9a3412; border: 1px solid #fed7aa;',
        'INTERPRETATION': 'background: #f8fafc; color: #334155; border: 1px solid #cbd5e1;',
        'RECOMMENDATION': 'background: #ecfeff; color: #0e7490; border: 1px solid #a5f3fc;',
    }
    style = styles.get(str(classification).upper(), 'background: var(--bg-subtle); color: var(--text-primary);')
    return mark_safe(f'<span class="badge" style="{style} font-size: 0.7rem; font-weight: 600;">{classification}</span>')
