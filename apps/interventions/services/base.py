"""
Intervention service interfaces for Phase 4 closed-loop interventions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseInterventionService(ABC):
    """
    Abstract interface for academic intervention workflows.
    """

    @abstractmethod
    def evaluate_risk_trigger(self, student_id: int) -> Dict[str, Any]:
        """Check whether a student meets intervention thresholds."""
        raise NotImplementedError
