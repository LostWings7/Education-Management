"""
Structured schemas and context definitions for Phase 4 Closed-Loop Academic Interventions.
Designed to be framework-agnostic and 100% compatible with future Phase 5 AI reasoning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class InterventionActionSchema:
    action_id: int
    order_index: int
    title: str
    description: str
    status: str
    verification_type: str
    due_date: Optional[str]
    completed_at: Optional[str]
    linked_resource_id: Optional[int]
    linked_resource_title: Optional[str]


@dataclass
class InterventionEvaluationSchema:
    checkpoint_number: int
    evaluation_type: str
    classification: str
    progress_percentage: float
    metrics_snapshot: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    evaluator_email: str
    created_at: str


@dataclass
class InterventionContext:
    """
    Complete structured context representing an intervention instance for downstream decision support & AI reasoning.
    """
    intervention_id: int
    student_id: str
    student_name: str
    student_email: str
    course_code: str
    course_title: str
    section_code: str
    topic_title: Optional[str]
    category: str
    status: str
    priority: str
    primary_target_metric: str
    objective: str
    educator_notes: str
    due_date: str
    supervisor_name: str
    supervisor_email: str
    trigger_insight_type: str
    baseline_metrics: Dict[str, Any]
    followup_metrics: Dict[str, Any]
    effectiveness_summary: str
    actions: List[InterventionActionSchema] = field(default_factory=list)
    evaluations: List[InterventionEvaluationSchema] = field(default_factory=list)
    acknowledgement_status: Optional[str] = None
    engine_version: str = "1.0"
