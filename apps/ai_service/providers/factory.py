"""
Factory for instantiating the active AI Provider.
"""

from django.conf import settings
from .base import BaseAIProvider
from .gemini import GeminiProvider
from .fallback import FallbackHeuristicProvider


def get_ai_provider() -> BaseAIProvider:
    """
    Returns configured AI provider (Gemini or FallbackHeuristic).
    """
    provider_type = getattr(settings, 'AI_PROVIDER', 'gemini').lower()
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if provider_type == 'gemini' and api_key:
        return GeminiProvider(api_key=api_key)

    return FallbackHeuristicProvider()
