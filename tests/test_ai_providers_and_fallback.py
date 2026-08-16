"""
Unit tests for AI Providers, Provider Factory, and Fallback Resilience.
"""

from django.test import TestCase
from django.test.utils import override_settings
from apps.ai_service.providers import (
    BaseAIProvider,
    GeminiProvider,
    FallbackHeuristicProvider,
    get_ai_provider
)
from apps.ai_service.schemas.messages import ChatMessage


class AIProvidersAndFallbackTest(TestCase):
    def test_fallback_provider_direct_execution(self):
        """Fallback provider executes deterministically without external network."""
        provider = FallbackHeuristicProvider()
        self.assertEqual(provider.provider_name, "fallback_heuristic")
        self.assertFalse(provider.is_online)

        context_data = {
            'student_name': 'Test Student',
            'attendance_summary': {'overall_percentage': 50.0, 'absence_buffer': 2},
            'risk_summary': {'composite_score': 60.0, 'risk_level': 'HIGH', 'contributing_factors': ['Attendance Deficit']}
        }

        # Attendance query
        resp_att = provider.chat(
            system_instruction="You are an assistant.",
            messages=[ChatMessage(role="user", content="How is my attendance?")],
            context_data=context_data
        )
        self.assertEqual(resp_att.provider, "fallback_heuristic")
        self.assertIn("50.0%", resp_att.content)
        self.assertIn("2", resp_att.content)
        self.assertEqual(resp_att.validation_status, "VALID")

        # Risk query
        resp_risk = provider.chat(
            system_instruction="You are an assistant.",
            messages=[ChatMessage(role="user", content="Why is my risk high?")],
            context_data=context_data
        )
        self.assertIn("HIGH", resp_risk.content)
        self.assertIn("60.0", resp_risk.content)

    @override_settings(AI_PROVIDER='fallback', GEMINI_API_KEY='')
    def test_factory_returns_fallback_provider(self):
        """Factory returns FallbackHeuristicProvider when configured or API key absent."""
        provider = get_ai_provider()
        self.assertIsInstance(provider, FallbackHeuristicProvider)
        self.assertFalse(provider.is_online)

    @override_settings(AI_PROVIDER='gemini', GEMINI_API_KEY='')
    def test_gemini_without_api_key_falls_back_gracefully(self):
        """GeminiProvider falls back gracefully without throwing exceptions when API key is empty."""
        provider = GeminiProvider(api_key='')
        self.assertFalse(provider.is_online)

        resp = provider.chat(
            system_instruction="System prompt",
            messages=[ChatMessage(role="user", content="Hello")],
            context_data={'student_name': 'Ada'}
        )
        self.assertEqual(resp.validation_status, "VALID")
        self.assertEqual(resp.provider, "fallback_heuristic")
