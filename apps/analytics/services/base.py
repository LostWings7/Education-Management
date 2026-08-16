"""
Base architectural interfaces for deterministic academic analytics services.
These interfaces will be implemented in Phase 3.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseAnalyticsService(ABC):
    """
    Abstract contract for all deterministic academic calculation services.
    Ensures analytics are pure Python calculations without external LLM dependencies.
    """

    @abstractmethod
    def calculate(self, target_id: int, **kwargs) -> Dict[str, Any]:
        """
        Execute deterministic calculations and return structured statistical metrics.
        """
        raise NotImplementedError
