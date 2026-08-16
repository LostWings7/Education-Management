"""
AI Observability & Quality Telemetry Service.
Aggregates operational performance, provider reliability, validation metrics,
and user feedback without exposing raw sensitive prompts.
"""

from typing import Dict, Any, List
from django.db.models import Avg, Count, Q
from apps.ai_service.models import AIInteractionLog, AIMessageFeedback, AIConversation


class AIObservabilityService:
    """
    Computes AI reliability, latency, fallback frequency, and user satisfaction metrics.
    """

    @classmethod
    def get_observability_metrics(cls) -> Dict[str, Any]:
        """
        Compiles institutional AI telemetry metrics.
        """
        logs = AIInteractionLog.objects.all()
        total_requests = logs.count()

        if total_requests == 0:
            return {
                'total_requests': 0,
                'success_rate': 100.0,
                'avg_latency_ms': 0,
                'online_provider_requests': 0,
                'fallback_provider_requests': 0,
                'fallback_rate': 0.0,
                'validation_valid_count': 0,
                'validation_remediated_count': 0,
                'validation_pass_rate': 100.0,
                'total_feedback_count': 0,
                'helpful_count': 0,
                'unhelpful_count': 0,
                'satisfaction_percentage': 100.0,
                'feedback_category_breakdown': {},
                'recent_interactions': []
            }

        successful_requests = logs.filter(success=True).count()
        success_rate = round((successful_requests / total_requests) * 100.0, 1)

        avg_latency = logs.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
        avg_latency = round(float(avg_latency), 0)

        online_reqs = logs.filter(provider='gemini').count()
        fallback_reqs = logs.filter(provider='fallback_heuristic').count()
        fallback_rate = round((fallback_reqs / total_requests) * 100.0, 1)

        valid_count = logs.filter(validation_status='VALID').count()
        remediated_count = logs.filter(validation_status='VALIDATED_AND_REMEDIATED').count()
        pass_rate = round((valid_count / total_requests) * 100.0, 1)

        # Feedback analytics
        feedbacks = AIMessageFeedback.objects.all()
        total_fb = feedbacks.count()
        helpful_fb = feedbacks.filter(is_helpful=True).count()
        unhelpful_fb = feedbacks.filter(is_helpful=False).count()
        satisfaction = round((helpful_fb / total_fb) * 100.0, 1) if total_fb > 0 else 100.0

        cat_breakdown = {}
        for cat_item in feedbacks.filter(is_helpful=False).values('category').annotate(c=Count('id')):
            cat_breakdown[cat_item['category'] or 'UNSPECIFIED'] = cat_item['c']

        recent_logs = list(logs.order_by('-created_at')[:15])

        return {
            'total_requests': total_requests,
            'success_rate': success_rate,
            'avg_latency_ms': int(avg_latency),
            'online_provider_requests': online_reqs,
            'fallback_provider_requests': fallback_reqs,
            'fallback_rate': fallback_rate,
            'validation_valid_count': valid_count,
            'validation_remediated_count': remediated_count,
            'validation_pass_rate': pass_rate,
            'total_feedback_count': total_fb,
            'helpful_count': helpful_fb,
            'unhelpful_count': unhelpful_fb,
            'satisfaction_percentage': satisfaction,
            'feedback_category_breakdown': cat_breakdown,
            'recent_interactions': recent_logs
        }
