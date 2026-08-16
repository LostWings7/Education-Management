"""
Abstract provider interface for all AI engines.
Ensures provider independence across the entire codebase.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from apps.ai_service.schemas.messages import ChatMessage
from apps.ai_service.schemas.responses import StructuredAIResponse, StudyPlanSchema


class BaseAIProvider(ABC):
    """
    Abstract contract for all external and internal AI providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'fallback_heuristic')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_online(self) -> bool:
        """Whether this provider uses active external network intelligence."""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
        context_data: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> StructuredAIResponse:
        """
        Executes conversational turn and returns structured response.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_explanation(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        """
        Generates concise explanation for a specific analytical insight or support plan.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_study_plan(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StudyPlanSchema:
        """
        Generates a structured weekly study plan.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_briefing(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        """
        Generates class or institutional executive briefing.
        """
        raise NotImplementedError
