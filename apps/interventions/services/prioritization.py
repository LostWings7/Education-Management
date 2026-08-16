"""
Deterministic Multi-Factor Prioritization Service for Phase 4 Interventions.
"""

from typing import Optional
from apps.interventions.models import Intervention


class InterventionPrioritizationService:
    """
    Computes deterministic priority score and priority classification level:
    P_score = 0.35 * R_risk + 0.30 * S_severity + 0.20 * A_anomaly + 0.15 * D_deadline
    """

    SEVERITY_WEIGHTS = {
        'CRITICAL': 100.0,
        'DANGER': 75.0,
        'WARNING': 40.0,
        'INFO': 15.0
    }

    @classmethod
    def calculate_priority_score(
        cls,
        risk_score: float = 0.0,
        severity: str = 'INFO',
        is_anomaly: bool = False,
        is_deadline_near: bool = False
    ) -> float:
        """
        Calculate composite priority score in [0.0, 100.0].
        """
        r_val = max(0.0, min(100.0, float(risk_score)))
        s_val = cls.SEVERITY_WEIGHTS.get(severity.upper(), 15.0)
        a_val = 100.0 if is_anomaly else 0.0
        d_val = 80.0 if is_deadline_near else 20.0

        p_score = (0.35 * r_val) + (0.30 * s_val) + (0.20 * a_val) + (0.15 * d_val)
        return round(max(0.0, min(100.0, p_score)), 1)

    @classmethod
    def classify_priority(cls, priority_score: float) -> str:
        """
        Map numerical priority score to Intervention.Priority choice:
        - >= 75.0: URGENT
        - 50.0 - 74.9: HIGH
        - 25.0 - 49.9: MEDIUM
        - < 25.0: LOW
        """
        if priority_score >= 75.0:
            return Intervention.Priority.URGENT
        elif priority_score >= 50.0:
            return Intervention.Priority.HIGH
        elif priority_score >= 25.0:
            return Intervention.Priority.MEDIUM
        return Intervention.Priority.LOW
