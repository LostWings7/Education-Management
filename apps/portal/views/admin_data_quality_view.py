"""
Administrator Academic Data Quality Center View.
"""

from django.shortcuts import render
from django.views import View
from apps.core.mixins import AdminRequiredMixin
from apps.analytics.services.data_quality import DataQualityEngineService


class AdminDataQualityView(AdminRequiredMixin, View):
    """
    Administrator view displaying the 6-dimension data quality audit and integrity issues.
    """
    template_name = 'portal/admin/data_quality.html'

    def get(self, request):
        audit_results = DataQualityEngineService.run_full_audit()
        return render(request, self.template_name, {
            'audit': audit_results
        })
