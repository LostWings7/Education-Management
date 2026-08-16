"""
Provider-independent AI service interfaces.
Ensures clean decoupling between LLM providers (Gemini, OpenAI, Anthropic, Ollama)
and local fallback heuristic mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAIProvider(ABC):
    """
    Abstract contract for all external and internal AI providers.
    """

    @abstractmethod
    def generate_explanation(self, context_data: Dict[str, Any], prompt_type: str) -> str:
        """Generate a natural language explanation for deterministic analytics."""
        raise NotImplementedError

    @abstractmethod
    def generate_recommendations(self, student_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized action items / recommendations."""
        raise NotImplementedError

    @abstractmethod
    def chat(self, message: str, context: Dict[str, Any], history: Optional[list] = None) -> str:
        """Handle conversational interactions for the academic copilot."""
        raise NotImplementedError


class FallbackHeuristicProvider(BaseAIProvider):
    """
    Offline/Rule-based heuristic provider used when no external API key is present.
    Guarantees deterministic uptime without failing or throwing runtime exceptions.
    Full heuristic template library will be populated in Phase 5.
    """

    def generate_explanation(self, context_data: Dict[str, Any], prompt_type: str) -> str:
        return "Deterministic academic analysis completed. External AI explanation layer is available in future phase."

    def generate_recommendations(self, student_context: Dict[str, Any]) -> Dict[str, Any]:
        return {"recommendations": ["Maintain regular attendance", "Complete assignments on schedule"]}

    def chat(self, message: str, context: Dict[str, Any], history: Optional[list] = None) -> str:
        return "Academic Assistant is operating in local mode. Please consult your course instructor or advisor."
