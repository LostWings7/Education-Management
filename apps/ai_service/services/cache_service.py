"""
Caching layer for AI briefings and summaries.
"""

from typing import Optional
from django.core.cache import cache
from apps.ai_service.schemas.responses import StructuredAIResponse


class AICacheService:
    """
    Tiered caching for executive and class briefings.
    """
    DEFAULT_TIMEOUT = 1800 # 30 minutes

    @classmethod
    def get_cached_briefing(cls, cache_key: str) -> Optional[StructuredAIResponse]:
        return cache.get(cache_key)

    @classmethod
    def set_cached_briefing(cls, cache_key: str, briefing: StructuredAIResponse, timeout: int = DEFAULT_TIMEOUT):
        cache.set(cache_key, briefing, timeout)

    @classmethod
    def invalidate_briefing(cls, cache_key: str):
        cache.delete(cache_key)
