"""
Academic domain services package.
"""

from .enrollment_service import EnrollmentService
from .schedule_service import ScheduleService
from .attendance_service import AttendanceService
from .assignment_service import AssignmentService
from .grading_service import GradingService
from .resource_service import ResourceService

__all__ = [
    'EnrollmentService',
    'ScheduleService',
    'AttendanceService',
    'AssignmentService',
    'GradingService',
    'ResourceService',
]
