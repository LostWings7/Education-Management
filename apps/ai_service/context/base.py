"""
Base Context Builder and Fact Registry.
Attaches authentic source identifiers to verified database and analytical values.
"""

from typing import Dict, Any, List
from apps.ai_service.schemas.responses import FactAttribution


class BaseContextBuilder:
    """
    Abstract base for role-scoped context generators.
    """

    @classmethod
    def create_fact_attribution(
        cls,
        fact_id: str,
        classification: str,
        metric_name: str,
        value: Any,
        source_service: str,
        course_code: str = None
    ) -> FactAttribution:
        """
        Creates an immutable fact attribution record.
        """
        return FactAttribution(
            fact_id=fact_id,
            classification=classification,
            metric_name=metric_name,
            value=value,
            source_service=source_service,
            course_code=course_code
        )
