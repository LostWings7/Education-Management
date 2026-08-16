"""
Deterministic Institutional Change Detection Service for Phase 7 Admin Pulse.
Compares active term performance against preceding terms and calculates explainable delta shifts.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.db.models import Avg, Count, Q
from apps.academic.models import Semester, Enrollment, AttendanceRecord, StudentProfile
from apps.interventions.models import Intervention
from .data_quality import DataQualityEngineService


class InstitutionalChangeDetectionService:
    """
    Evaluates institutional macro performance shifts between academic terms.
    """

    @classmethod
    def evaluate_institutional_changes(cls) -> Dict[str, Any]:
        """
        Compare active semester metrics against preceding completed semester.
        """
        active_sem = Semester.objects.filter(is_active=True).first()
        prev_sem = Semester.objects.filter(is_completed=True).order_by('-end_date').first()

        if not active_sem or not prev_sem:
            return {
                'status': 'INSUFFICIENT_HISTORICAL_DATA',
                'active_semester': active_sem.name if active_sem else 'N/A',
                'previous_semester': prev_sem.name if prev_sem else 'N/A',
                'metrics': {},
                'summary': 'Insufficient multi-semester data to perform comparative change detection.'
            }

        # -------------------------------------------------------------
        # 1. Macro Attendance Delta
        # -------------------------------------------------------------
        curr_att_total = AttendanceRecord.objects.filter(session__class_section__semester=active_sem).count()
        curr_att_pres = AttendanceRecord.objects.filter(
            session__class_section__semester=active_sem,
            status__in=['PRESENT', 'LATE']
        ).count()
        curr_att_rate = round((curr_att_pres / curr_att_total) * 100.0, 1) if curr_att_total > 0 else 0.0

        prev_att_total = AttendanceRecord.objects.filter(session__class_section__semester=prev_sem).count()
        prev_att_pres = AttendanceRecord.objects.filter(
            session__class_section__semester=prev_sem,
            status__in=['PRESENT', 'LATE']
        ).count()
        prev_att_rate = round((prev_att_pres / prev_att_total) * 100.0, 1) if prev_att_total > 0 else 0.0

        delta_att = round(curr_att_rate - prev_att_rate, 1)

        # -------------------------------------------------------------
        # 2. Average Grade / GPA Delta
        # -------------------------------------------------------------
        curr_gpa_avg = Enrollment.objects.filter(
            class_section__semester=active_sem,
            is_grade_published=True
        ).aggregate(Avg('final_percentage'))['final_percentage__avg'] or Decimal('0.0')

        prev_gpa_avg = Enrollment.objects.filter(
            class_section__semester=prev_sem,
            is_grade_published=True
        ).aggregate(Avg('final_percentage'))['final_percentage__avg'] or Decimal('0.0')

        curr_perf = round(float(curr_gpa_avg), 1)
        prev_perf = round(float(prev_gpa_avg), 1)
        delta_perf = round(curr_perf - prev_perf, 1)

        # -------------------------------------------------------------
        # 3. Intervention Resolution Rate Delta
        # -------------------------------------------------------------
        curr_intvs = Intervention.objects.filter(class_section__semester=active_sem)
        curr_intv_total = curr_intvs.count()
        curr_intv_eff = curr_intvs.filter(status__in=[Intervention.Status.EFFECTIVE, Intervention.Status.PARTIALLY_EFFECTIVE]).count()
        curr_intv_rate = round((curr_intv_eff / curr_intv_total) * 100.0, 1) if curr_intv_total > 0 else 0.0

        prev_intvs = Intervention.objects.filter(class_section__semester=prev_sem)
        prev_intv_total = prev_intvs.count()
        prev_intv_eff = prev_intvs.filter(status__in=[Intervention.Status.EFFECTIVE, Intervention.Status.PARTIALLY_EFFECTIVE]).count()
        prev_intv_rate = round((prev_intv_eff / prev_intv_total) * 100.0, 1) if prev_intv_total > 0 else 0.0

        delta_intv = round(curr_intv_rate - prev_intv_rate, 1)

        # -------------------------------------------------------------
        # 4. Data Quality Health
        # -------------------------------------------------------------
        dq_res = DataQualityEngineService.run_full_audit()
        overall_dq = dq_res.get('overall_score', 100.0)

        # -------------------------------------------------------------
        # Assemble Indicators
        # -------------------------------------------------------------
        metrics = {
            'attendance': {
                'label': 'Institutional Attendance',
                'current': curr_att_rate,
                'previous': prev_att_rate,
                'delta': delta_att,
                'status': 'IMPROVED' if delta_att > 1.0 else ('DECLINED' if delta_att < -1.0 else 'STABLE')
            },
            'performance': {
                'label': 'Average Course Percentage',
                'current': curr_perf,
                'previous': prev_perf,
                'delta': delta_perf,
                'status': 'IMPROVED' if delta_perf > 1.0 else ('DECLINED' if delta_perf < -1.0 else 'STABLE')
            },
            'interventions': {
                'label': 'Intervention Resolution Rate',
                'current': curr_intv_rate,
                'previous': prev_intv_rate,
                'delta': delta_intv,
                'status': 'IMPROVED' if delta_intv > 2.0 else ('DECLINED' if delta_intv < -2.0 else 'STABLE')
            },
            'data_quality': {
                'label': 'Academic Data Quality Health',
                'current': overall_dq,
                'status': 'EXCELLENT' if overall_dq >= 90 else ('GOOD' if overall_dq >= 75 else 'WARNING')
            }
        }

        return {
            'status': 'VALID',
            'active_semester': active_sem.name,
            'previous_semester': prev_sem.name,
            'metrics': metrics
        }
