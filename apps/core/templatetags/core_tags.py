"""
Custom template filters and utility tags for Education Management Portal.
"""

from django import template

register = template.Library()


@register.filter(name='dict_lookup')
def dict_lookup(dictionary, key):
    """Retrieve dictionary value by key or integer key."""
    if not isinstance(dictionary, dict):
        return []
    val = dictionary.get(key)
    if val is None:
        try:
            val = dictionary.get(int(key))
        except (ValueError, TypeError):
            val = None
    return val if val is not None else []


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Safely get item from dictionary."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
