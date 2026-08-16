"""
Reporting Views and Export Endpoints.
"""

from django.shortcuts import render, get_object_or_404
from django.views import View
from apps.core.mixins import StudentRequiredMixin, TeacherRequiredMixin, AdminRequiredMixin
from apps.portal.reporting import TranscriptService, ReportingService


class StudentTranscriptView(StudentRequiredMixin, View):
    """
    Official student transcript view with print CSS and CSV export.
    """
    template_name = 'portal/student/transcript.html'

    def get(self, request):
        student = request.user.student_profile
        transcript_data = TranscriptService.get_student_transcript(student)
        return render(request, self.template_name, {
            'student': student,
            'transcript': transcript_data
        })


class StudentTranscriptCSVExportView(StudentRequiredMixin, View):
    """
    Download official CSV transcript for authenticated student.
    """
    def get(self, request):
        student = request.user.student_profile
        return ReportingService.export_student_transcript_csv(student)


class TeacherSectionCSVExportView(TeacherRequiredMixin, View):
    """
    Download section grade/roster CSV export for teacher.
    """
    def get(self, request, section_id):
        teacher = request.user.teacher_profile
        return ReportingService.export_teacher_section_csv(teacher, section_id)


class AdminInstitutionalCSVExportView(AdminRequiredMixin, View):
    """
    Download institutional summary CSV for administrator.
    """
    def get(self, request):
        return ReportingService.export_admin_institutional_csv(request.user)


class AdminInterventionsCSVExportView(AdminRequiredMixin, View):
    """
    Download intervention audit CSV for administrator.
    """
    def get(self, request):
        return ReportingService.export_admin_interventions_csv(request.user)
