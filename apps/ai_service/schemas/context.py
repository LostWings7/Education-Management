"""
Context dataclasses for Student, Teacher, and Administrator AI Copilot scoping.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from .responses import FactAttribution


@dataclass
class StudentAIContext:
    student_id: str
    student_name: str
    program_name: str
    department_name: str
    semester_name: str
    enrolled_courses: List[Dict[str, Any]] = field(default_factory=list)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    attendance_summary: Dict[str, Any] = field(default_factory=dict)
    coursework_summary: Dict[str, Any] = field(default_factory=dict)
    risk_summary: Dict[str, Any] = field(default_factory=dict)
    trajectory_summary: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    topic_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    active_interventions: List[Dict[str, Any]] = field(default_factory=list)
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    learning_resources: List[Dict[str, Any]] = field(default_factory=list)
    fact_registry: List[FactAttribution] = field(default_factory=list)
    context_generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    engine_version: str = "1.0"


@dataclass
class TeacherAIContext:
    teacher_id: str
    teacher_name: str
    department_name: str
    assigned_sections: List[Dict[str, Any]] = field(default_factory=list)
    section_kpis: Dict[str, Any] = field(default_factory=dict)
    flagged_students: List[Dict[str, Any]] = field(default_factory=list)
    topic_weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    interventions_overview: Dict[str, Any] = field(default_factory=dict)
    fact_registry: List[FactAttribution] = field(default_factory=list)
    context_generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    engine_version: str = "1.0"


@dataclass
class AdminAIContext:
    institution_name: str = "Central University Portal"
    total_enrollments: int = 0
    average_attendance: float = 0.0
    average_performance: float = 0.0
    risk_distribution: Dict[str, int] = field(default_factory=dict)
    department_summary: List[Dict[str, Any]] = field(default_factory=list)
    curriculum_hotspots: List[Dict[str, Any]] = field(default_factory=list)
    interventions_macro: Dict[str, Any] = field(default_factory=dict)
    fact_registry: List[FactAttribution] = field(default_factory=list)
    context_generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    engine_version: str = "1.0"
