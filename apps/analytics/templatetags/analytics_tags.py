"""
Custom template tags and filters for rendering academic analytics.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def risk_badge_class(risk_level):
    """Return CSS class based on academic risk level."""
    mapping = {
        'LOW': 'badge-success',
        'MODERATE': 'badge-warning',
        'HIGH': 'badge-danger',
        'CRITICAL': 'badge-danger',
    }
    return mapping.get(str(risk_level).upper(), 'badge-neutral')


@register.filter
def severity_badge_class(severity):
    """Return CSS class based on severity."""
    mapping = {
        'INFO': 'badge-info',
        'WARNING': 'badge-warning',
        'DANGER': 'badge-danger',
        'CRITICAL': 'badge-danger',
    }
    return mapping.get(str(severity).upper(), 'badge-neutral')


@register.filter
def trend_icon(direction):
    """Return appropriate Lucide icon name for a trend direction."""
    mapping = {
        'IMPROVING': 'trending-up',
        'DECLINING': 'trending-down',
        'STABLE': 'minus',
        'VOLATILE': 'activity',
        'INSUFFICIENT_DATA': 'help-circle',
    }
    return mapping.get(str(direction), 'activity')


@register.filter
def format_pct(val):
    """Format float or decimal as percentage string."""
    if val is None:
        return "—"
    try:
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return "—"


@register.filter
def confidence_badge(confidence):
    """Render a visual pill for analytical data confidence."""
    level = str(confidence).upper()
    if level == 'HIGH':
        return mark_safe('<span class="badge badge-success" title="100% data factors available">High Confidence</span>')
    elif level == 'MEDIUM':
        return mark_safe('<span class="badge badge-warning" title="80-99% data factors available (e.g. no historical baseline)">Medium Confidence</span>')
    else:
        return mark_safe('<span class="badge badge-neutral" title="<80% data factors available">Low Confidence</span>')
