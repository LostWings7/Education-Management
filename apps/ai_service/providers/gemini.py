"""
Google Gemini API Provider implementation.
Encapsulates all Google GenAI REST API details, timeouts, retries, and structured parsing.
Fails gracefully to FallbackHeuristicProvider if API key is absent, invalid, or network is down.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from django.conf import settings
from apps.ai_service.schemas.messages import ChatMessage
from apps.ai_service.schemas.responses import (
    StructuredAIResponse,
    FactAttribution,
    StudyPlanSchema,
    StudyPlanDaySchema,
    StudyPlanTaskSchema
)
from .base import BaseAIProvider
from .fallback import FallbackHeuristicProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """
    Provider utilizing Google Gemini GenAI API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'GEMINI_API_KEY', '')
        self.fallback = FallbackHeuristicProvider()
        self.timeout = getattr(settings, 'AI_REQUEST_TIMEOUT', 20)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_online(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
        context_data: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> StructuredAIResponse:
        """
        Executes interactive chat against Gemini API.
        """
        if not self.api_key:
            return self.fallback.chat(system_instruction, messages, context_data, model, temperature)

        target_model = model or getattr(settings, 'AI_MODEL_FAST', 'gemini-2.5-flash')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"

        # Construct Gemini payload
        contents = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

        # Inject authoritative context into system instruction
        context_json_str = json.dumps(self._sanitize_context_for_llm(context_data), default=str)
        enriched_system = (
            f"{system_instruction}\n\n"
            f"<academic_data_context untrusted=\"false\">\n{context_json_str}\n</academic_data_context>"
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": enriched_system}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                token_count = data.get('usageMetadata', {}).get('totalTokenCount', 0)
                facts = self._extract_fact_attributions(context_data)

                return StructuredAIResponse(
                    content=text,
                    facts_used=facts.get('facts', []),
                    calculations_used=facts.get('calculations', []),
                    simulations_used=facts.get('simulations', []),
                    actions_used=facts.get('actions', []),
                    interpretations=["Synthesized from authoritative portal records."],
                    recommendations=[],
                    provider=self.provider_name,
                    model=target_model,
                    token_count=token_count,
                    validation_status="VALID",
                    disclaimer="AI-generated guidance. Verify official academic records."
                )
            else:
                logger.warning("Gemini API error %d: %s. Falling back to local heuristic provider.", resp.status_code, resp.text)
                return self.fallback.chat(system_instruction, messages, context_data, model, temperature)
        except Exception as e:
            logger.exception("Gemini API request failed: %s. Falling back to local heuristic provider.", e)
            return self.fallback.chat(system_instruction, messages, context_data, model, temperature)

    def generate_explanation(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        """
        Generates contextual explanation.
        """
        if not self.api_key:
            return self.fallback.generate_explanation(system_instruction, prompt, context_data, model)

        msg = [ChatMessage(role="user", content=prompt)]
        return self.chat(system_instruction, msg, context_data, model=model)

    def generate_study_plan(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StudyPlanSchema:
        """
        Generates structured JSON study plan.
        """
        if not self.api_key:
            return self.fallback.generate_study_plan(system_instruction, prompt, context_data, model)

        target_model = model or getattr(settings, 'AI_MODEL_DEEP', 'gemini-2.5-pro')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"

        context_json_str = json.dumps(self._sanitize_context_for_llm(context_data), default=str)
        enriched_system = (
            f"{system_instruction}\n\n"
            f"<academic_data_context untrusted=\"false\">\n{context_json_str}\n</academic_data_context>\n\n"
            f"You MUST respond ONLY with a JSON object conforming strictly to the requested schema."
        )

        payload = {
            "system_instruction": {"parts": [{"text": enriched_system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                raw_json = json.loads(resp.json()['candidates'][0]['content']['parts'][0]['text'])
                days = []
                for d in raw_json.get('days', []):
                    tasks = []
                    for t in d.get('tasks', []):
                        tasks.append(StudyPlanTaskSchema(
                            course_code=t.get('course_code', ''),
                            task_type=t.get('task_type', 'TOPIC_STUDY'),
                            title=t.get('title', ''),
                            duration_minutes=int(t.get('duration_minutes', 45)),
                            description=t.get('description', ''),
                            is_official_event=bool(t.get('is_official_event', False)),
                            assignment_id=t.get('assignment_id'),
                            resource_id=t.get('resource_id'),
                            resource_title=t.get('resource_title'),
                            action_id=t.get('action_id'),
                            due_date=t.get('due_date')
                        ))
                    days.append(StudyPlanDaySchema(
                        day_name=d.get('day_name', ''),
                        date_str=d.get('date_str', ''),
                        focus_summary=d.get('focus_summary', ''),
                        tasks=tasks,
                        total_study_minutes=sum(t.duration_minutes for t in tasks)
                    ))
                return StudyPlanSchema(
                    plan_title=raw_json.get('plan_title', 'AI Personalized Study Schedule'),
                    target_week=raw_json.get('target_week', 'Upcoming Academic Week'),
                    days=days,
                    total_estimated_hours=float(raw_json.get('total_estimated_hours', 0.0)),
                    validation_status="VALID",
                    disclaimer="AI-suggested study blocks are not official timetable events."
                )
            else:
                return self.fallback.generate_study_plan(system_instruction, prompt, context_data, model)
        except Exception:
            return self.fallback.generate_study_plan(system_instruction, prompt, context_data, model)

    def generate_briefing(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        """
        Generates executive briefing.
        """
        if not self.api_key:
            return self.fallback.generate_briefing(system_instruction, prompt, context_data, model)

        msg = [ChatMessage(role="user", content=prompt)]
        target_model = model or getattr(settings, 'AI_MODEL_DEEP', 'gemini-2.5-pro')
        return self.chat(system_instruction, msg, context_data, model=target_model)

    def _sanitize_context_for_llm(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts dataclasses and removes non-serializable objects.
        """
        sanitized = {}
        for k, v in context_data.items():
            if k == 'fact_registry':
                continue # Handled separately
            if hasattr(v, '__dict__'):
                sanitized[k] = v.__dict__
            else:
                sanitized[k] = v
        return sanitized

    def _extract_fact_attributions(self, context_data: Dict[str, Any]) -> Dict[str, List[FactAttribution]]:
        return self.fallback._extract_fact_attributions(context_data)
