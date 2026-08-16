"""
Response schemas and 6-tier classification dataclasses for AI service outputs.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class AIClassificationType(str, Enum):
    FACT = 'FACT'                     # Authoritative database value
    CALCULATION = 'CALCULATION'       # Phase 3 deterministic calculation
    SIMULATION = 'SIMULATION'         # Deterministic What-If projection
    ACTION = 'ACTION'                 # Recorded intervention/action
    INTERPRETATION = 'INTERPRETATION' # AI analytical explanation
    RECOMMENDATION = 'RECOMMENDATION' # AI pedagogical suggestion


@dataclass
class FactAttribution:
    """
    Structured attribution token linking an AI statement to verified portal data.
    """
    fact_id: str
    classification: str # FACT, CALCULATION, SIMULATION, ACTION
    metric_name: str
    value: Any
    source_service: str
    timestamp: Optional[str] = None
    course_code: Optional[str] = None


@dataclass
class StructuredAIResponse:
    """
    Standardized AI output payload containing natural language and authentic source evidence.
    """
    content: str
    facts_used: List[FactAttribution] = field(default_factory=list)
    calculations_used: List[FactAttribution] = field(default_factory=list)
    simulations_used: List[FactAttribution] = field(default_factory=list)
    actions_used: List[FactAttribution] = field(default_factory=list)
    interpretations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    prompt_version: str = "v1.0"
    token_count: int = 0
    validation_status: str = "VALID"
    disclaimer: str = "AI-generated guidance. Verify official academic records."


@dataclass
class StudyPlanTaskSchema:
    course_code: str
    task_type: str # OFFICIAL_EVENT (Exam/Deadline), TOPIC_STUDY, ASSIGNMENT_PREP, INTERVENTION_TASK
    title: str
    duration_minutes: int
    description: str
    is_official_event: bool = False
    assignment_id: Optional[int] = None
    resource_id: Optional[int] = None
    resource_title: Optional[str] = None
    action_id: Optional[int] = None
    due_date: Optional[str] = None


@dataclass
class StudyPlanDaySchema:
    day_name: str
    date_str: str
    focus_summary: str
    tasks: List[StudyPlanTaskSchema] = field(default_factory=list)
    total_study_minutes: int = 0


@dataclass
class StudyPlanSchema:
    plan_title: str
    target_week: str
    days: List[StudyPlanDaySchema] = field(default_factory=list)
    total_estimated_hours: float = 0.0
    validation_status: str = "VALID"
    disclaimer: str = "AI-suggested study blocks are not official timetable events."
