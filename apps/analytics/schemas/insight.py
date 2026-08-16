"""
Structured analytical dataclasses and schemas for deterministic academic intelligence.
Standardizes percentages to 0.0 - 100.0 scale and provides data quality / confidence ratings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _


class DataQuality(models.TextChoices):
    VALID = 'VALID', _('Valid / Sufficient Data')
    INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', _('Insufficient Data')
    NOT_AVAILABLE = 'NOT_AVAILABLE', _('Not Applicable / Unavailable')
    UNDEFINED = 'UNDEFINED', _('Mathematically Undefined')


class ConfidenceLevel(models.TextChoices):
    HIGH = 'HIGH', _('High Confidence (100% factors available)')
    MEDIUM = 'MEDIUM', _('Medium Confidence (80-99% factors available)')
    LOW = 'LOW', _('Low Confidence (<80% factors available)')


class TrendDirection(models.TextChoices):
    IMPROVING = 'IMPROVING', _('Improving Trajectory')
    DECLINING = 'DECLINING', _('Declining Trajectory')
    STABLE = 'STABLE', _('Stable Performance')
    VOLATILE = 'VOLATILE', _('High Volatility / Inconsistent')
    INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', _('Insufficient Data (<3 observations)')


class RiskLevel(models.TextChoices):
    LOW = 'LOW', _('Low Academic Risk')
    MODERATE = 'MODERATE', _('Moderate Academic Risk')
    HIGH = 'HIGH', _('High Academic Risk')
    CRITICAL = 'CRITICAL', _('Critical Academic Risk')


class Severity(models.TextChoices):
    INFO = 'INFO', _('Informational')
    WARNING = 'WARNING', _('Warning')
    DANGER = 'DANGER', _('Danger')
    CRITICAL = 'CRITICAL', _('Critical')


@dataclass
class InsightObject:
    """
    Framework-independent structured insight payload.
    Consumable by dashboards, Phase 4 intervention engine, and future Phase 5 LLM.
    """
    insight_type: str        # RISK_ALERT, TRAJECTORY_SHIFT, ANOMALY_DETECTED, ATTENDANCE_DEFICIT, TOPIC_GAP, CORRELATION, DISCORDANCE
    severity: str            # INFO, WARNING, DANGER, CRITICAL
    title: str
    summary: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    student_id: Optional[int] = None
    course_id: Optional[int] = None
    section_id: Optional[int] = None
    topic_id: Optional[int] = None
    data_quality: str = DataQuality.VALID
    confidence: str = ConfidenceLevel.HIGH
    engine_version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PerformanceProfile:
    course_id: Optional[int]
    course_code: str
    course_title: str
    weighted_score: Optional[float]        # 0.0 - 100.0
    average_score: Optional[float]         # 0.0 - 100.0
    consistency_metric: Optional[float]    # Std Dev (0.0 - 100.0)
    consistency_label: str                 # High Consistency, Moderate, Volatile
    completed_weight: float                # Sum of completed component weights (0.0 - 100.0)
    evaluations_count: int
    data_quality: str = DataQuality.VALID


@dataclass
class AttendanceAnalyticsResult:
    attendance_percentage: float           # 0.0 - 100.0
    total_conducted: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    remaining_sessions: int
    target_threshold: float                # Default 75.0
    absence_buffer: int                    # Remaining sessions that can be missed while staying >= T
    required_sessions: int                 # Sessions required to reach target threshold
    is_below_threshold: bool
    is_recovery_possible: bool
    data_quality: str = DataQuality.VALID


@dataclass
class AssignmentAnalyticsResult:
    total_assigned: int
    submitted_count: int
    missing_count: int
    on_time_count: int
    late_count: int
    completion_rate: float                 # 0.0 - 100.0
    missing_rate: float                    # 0.0 - 100.0
    on_time_rate: float                    # 0.0 - 100.0
    average_score: Optional[float]         # 0.0 - 100.0 on graded submissions
    discordance_flag: Optional[str]        # None, Underperforming Effort, Disengaged Capability
    data_quality: str = DataQuality.VALID


@dataclass
class TrendResult:
    direction: str                         # TrendDirection choice
    slope: Optional[float]                 # Points per sequential evaluation step
    observations_count: int
    scores_sequence: List[float]           # Sequential scores (0.0 - 100.0)
    std_dev: float
    data_quality: str = DataQuality.VALID


@dataclass
class RiskEvaluationResult:
    risk_level: str                        # RiskLevel choice
    composite_score: float                 # 0.0 - 100.0
    risk_model_version: str = "1.0"
    data_confidence: str = ConfidenceLevel.HIGH
    attendance_risk: Optional[float] = None
    performance_risk: Optional[float] = None
    trend_risk: Optional[float] = None
    assignment_risk: Optional[float] = None
    historical_risk: Optional[float] = None
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    escalations_applied: List[str] = field(default_factory=list)
    data_quality: str = DataQuality.VALID


@dataclass
class AnomalyEvent:
    is_anomaly: bool
    anomaly_type: Optional[str]            # ACUTE_DROP, ACUTE_SURGE, NONE
    severity: str                          # NONE, WARNING, CRITICAL
    baseline_mean: Optional[float]
    baseline_std: Optional[float]
    current_score: Optional[float]
    delta: Optional[float]                 # baseline_mean - current_score
    z_score: Optional[float]
    summary: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    data_quality: str = DataQuality.VALID


@dataclass
class CorrelationResult:
    metric_x: str
    metric_y: str
    pearson_r: Optional[float]             # -1.0 to +1.0
    sample_size: int
    relationship_description: str
    disclaimer: str = "Statistical correlation indicates an observed association across the dataset and does not imply causation."
    data_quality: str = DataQuality.VALID


@dataclass
class WhatIfResult:
    simulation_type: str                   # NEXT_ASSESSMENT, ATTENDANCE_IMPACT, TARGET_GRADE_SOLVER
    current_value: float                   # 0.0 - 100.0
    projected_value: Optional[float]       # 0.0 - 100.0
    required_score: Optional[float]        # 0.0 - 100.0 (or >100.0 if impossible)
    is_feasible: bool                      # True if required score <= 100.0
    explanation: str
    data_quality: str = DataQuality.VALID
