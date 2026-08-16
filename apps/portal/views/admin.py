"""
Custom Administrator portal management views for Phase 2.5 Academic CRUD.
Provides comprehensive management interfaces with validation, audit trails, and deletion protection.
"""

from decimal import Decimal
from datetime import date
from django.db import models, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.mixins import AdminRequiredMixin
from apps.core.models import User, Role, AuditLog
from apps.academic.models import (
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
    AcademicYear,
    Semester,
    Course,
    Topic,
    ClassSection,
    Enrollment,
    ClassSchedule,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    LearningResource,
    CourseAnnouncement,
)
from apps.academic.forms import (
    DepartmentForm,
    ProgramForm,
    AcademicYearForm,
    SemesterForm,
    StudentCreateForm,
    StudentEditForm,
    TeacherCreateForm,
    TeacherEditForm,
    CourseForm,
    TopicForm,
    ClassSectionForm,
    ClassScheduleForm,
    AssignmentForm,
    AssessmentForm,
    LearningResourceForm,
    CourseAnnouncementForm,
)
from apps.academic.services import (
    EnrollmentService,
    ScheduleService,
    GradingService,
    AttendanceService,
    ResourceService,
)


from apps.analytics.services import (
    InstitutionalChangeDetectionService,
    RiskEngineService,
    DataQualityEngineService
)
from apps.ai_service.services.observability_service import AIObservabilityService
from apps.interventions.models import Intervention


# ============================================================================
# 1. Primary Dashboard: Institutional Pulse & Macro Intelligence
# ============================================================================

class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """
    Administrator Executive Command Hub & Institutional Pulse:
    Integrates period-over-period change detection, macro risk distribution, data quality, and AI telemetry.
    """
    template_name = 'portal/admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Institutional Pulse & Administrator Command'

        active_semester = Semester.objects.filter(is_active=True).first()
        context['active_semester'] = active_semester

        # Counts
        context['total_students'] = User.objects.filter(role=Role.STUDENT, is_active=True).count()
        context['total_teachers'] = User.objects.filter(role=Role.TEACHER, is_active=True).count()
        context['total_departments'] = Department.objects.filter(is_active=True).count()
        context['total_programs'] = Program.objects.filter(is_active=True).count()
        context['total_courses'] = Course.objects.filter(is_active=True).count()
        context['total_sections'] = ClassSection.objects.filter(semester=active_semester).count() if active_semester else 0
        context['total_active_enrollments'] = Enrollment.objects.filter(
            class_section__semester=active_semester,
            status=Enrollment.EnrollmentStatus.ENROLLED
        ).count() if active_semester else 0

        # Institutional Change Detection (What Changed?)
        context['change_detection'] = InstitutionalChangeDetectionService.evaluate_institutional_changes()

        # Macro Risk Aggregation across all active students
        students = StudentProfile.objects.filter(user__is_active=True)
        risk_counts = {'LOW': 0, 'MODERATE': 0, 'HIGH': 0, 'CRITICAL': 0}
        for st in students:
            res = RiskEngineService.evaluate_overall_risk(st, semester=active_semester)
            if res:
                risk_counts[str(res.risk_level)] = risk_counts.get(str(res.risk_level), 0) + 1

        context['macro_risk'] = risk_counts

        # Data Quality & AI Telemetry
        context['data_quality'] = DataQualityEngineService.run_full_audit()
        context['ai_metrics'] = AIObservabilityService.get_observability_metrics()

        # Active Interventions
        context['active_interventions_count'] = Intervention.objects.filter(
            status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]
        ).count()

        # Recent activities and logs
        context['recent_logs'] = AuditLog.objects.select_related('user')[:10]
        context['departments'] = Department.objects.filter(is_active=True)[:5]
        context['active_sections'] = ClassSection.objects.filter(semester=active_semester).select_related('course', 'primary_teacher__user')[:6] if active_semester else []

        return context


class AdminRiskHeatmapView(AdminRequiredMixin, TemplateView):
    """
    Privacy-guarded Institutional Risk Heatmap:
    Applies minimum-population privacy threshold (MIN_POPULATION = 3) to suppress identifiable cells.
    """
    template_name = 'portal/admin/risk_heatmap.html'
    MIN_AGGREGATION_POPULATION = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_semester = Semester.objects.filter(is_active=True).first()
        context['active_semester'] = active_semester

        # Department Risk Matrix
        dept_matrix = []
        departments = Department.objects.filter(is_active=True)
        for d in departments:
            st_qs = StudentProfile.objects.filter(department=d, user__is_active=True)
            total = st_qs.count()

            if total < self.MIN_AGGREGATION_POPULATION:
                dept_matrix.append({
                    'department': d,
                    'total_students': total,
                    'is_suppressed': True,
                    'suppression_reason': f"Population ({total}) &lt; Minimum Threshold ({self.MIN_AGGREGATION_POPULATION})",
                    'counts': {}
                })
            else:
                counts = {'LOW': 0, 'MODERATE': 0, 'HIGH': 0, 'CRITICAL': 0}
                for st in st_qs:
                    r = RiskEngineService.evaluate_overall_risk(st, semester=active_semester)
                    if r:
                        counts[str(r.risk_level)] = counts.get(str(r.risk_level), 0) + 1
                dept_matrix.append({
                    'department': d,
                    'total_students': total,
                    'is_suppressed': False,
                    'counts': counts
                })

        # Program Risk Matrix
        prog_matrix = []
        programs = Program.objects.filter(is_active=True).select_related('department')
        for p in programs:
            st_qs = StudentProfile.objects.filter(program=p, user__is_active=True)
            total = st_qs.count()

            if total < self.MIN_AGGREGATION_POPULATION:
                prog_matrix.append({
                    'program': p,
                    'total_students': total,
                    'is_suppressed': True,
                    'suppression_reason': f"Population ({total}) &lt; Minimum Threshold ({self.MIN_AGGREGATION_POPULATION})",
                    'counts': {}
                })
            else:
                counts = {'LOW': 0, 'MODERATE': 0, 'HIGH': 0, 'CRITICAL': 0}
                for st in st_qs:
                    r = RiskEngineService.evaluate_overall_risk(st, semester=active_semester)
                    if r:
                        counts[str(r.risk_level)] = counts.get(str(r.risk_level), 0) + 1
                prog_matrix.append({
                    'program': p,
                    'total_students': total,
                    'is_suppressed': False,
                    'counts': counts
                })

        context['dept_matrix'] = dept_matrix
        context['prog_matrix'] = prog_matrix
        context['min_population'] = self.MIN_AGGREGATION_POPULATION
        return context


class AdminInterventionOutcomeView(AdminRequiredMixin, TemplateView):
    """
    Intervention Outcome Analysis & Effectiveness Overview:
    Aggregates outcome distributions with strict non-causal statistical disclosures.
    """
    template_name = 'portal/admin/interventions/outcome_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_intvs = Intervention.objects.all()

        categories = Intervention.InterventionCategory.choices
        category_analytics = []

        for cat_code, cat_label in categories:
            qs = all_intvs.filter(category=cat_code)
            total = qs.count()

            effective = qs.filter(status=Intervention.Status.EFFECTIVE).count()
            partially_effective = qs.filter(status=Intervention.Status.PARTIALLY_EFFECTIVE).count()
            ineffective = qs.filter(status=Intervention.Status.INEFFECTIVE).count()
            in_progress = qs.filter(status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS, Intervention.Status.EVALUATING]).count()

            success_rate = round(((effective + partially_effective) / total) * 100.0, 1) if total > 0 else 0.0

            category_analytics.append({
                'category_code': cat_code,
                'category_label': cat_label,
                'total_count': total,
                'effective_count': effective,
                'partially_effective_count': partially_effective,
                'ineffective_count': ineffective,
                'in_progress_count': in_progress,
                'resolution_rate': success_rate
            })

        context['category_analytics'] = category_analytics
        context['total_interventions'] = all_intvs.count()
        context['non_causal_disclaimer'] = (
            "Intervention resolution rates describe statistical associations and target metric recovery "
            "following support plan completion. Association does not establish sole causality."
        )
        return context


# ============================================================================
# 2. Department Management
# ============================================================================

class AdminDepartmentListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/departments/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        qs = Department.objects.all().prefetch_related('programs', 'courses', 'teachers')
        if query:
            qs = qs.filter(models.Q(name__icontains=query) | models.Q(code__icontains=query))

        context['departments'] = qs.order_by('name')
        context['search_query'] = query
        return context


class AdminDepartmentCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = DepartmentForm()
        return render(request, 'portal/admin/departments/form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_DEPARTMENT', details={'dept_id': dept.pk, 'code': dept.code})
            messages.success(request, f"Department '{dept.name}' ({dept.code}) created successfully.")
            return redirect('portal_admin:department_list')
        return render(request, 'portal/admin/departments/form.html', {'form': form, 'is_create': True})


class AdminDepartmentEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        form = DepartmentForm(instance=dept)
        return render(request, 'portal/admin/departments/form.html', {'form': form, 'department': dept, 'is_create': False})

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            dept = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_DEPARTMENT', details={'dept_id': dept.pk, 'code': dept.code})
            messages.success(request, f"Department '{dept.name}' updated successfully.")
            return redirect('portal_admin:department_list')
        return render(request, 'portal/admin/departments/form.html', {'form': form, 'department': dept, 'is_create': False})


class AdminDepartmentToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        dept.is_active = not dept.is_active
        dept.save()
        status_str = "activated" if dept.is_active else "archived / deactivated"
        AuditLog.log_action(user=request.user, action='TOGGLE_DEPARTMENT_STATUS', details={'dept_id': dept.pk, 'is_active': dept.is_active})
        messages.success(request, f"Department '{dept.name}' is now {status_str}.")
        return redirect('portal_admin:department_list')


# ============================================================================
# 3. Degree Program Management
# ============================================================================

class AdminProgramListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/programs/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department')
        level = self.request.GET.get('level')

        qs = Program.objects.select_related('department').prefetch_related('students', 'courses')
        if query:
            qs = qs.filter(models.Q(name__icontains=query) | models.Q(code__icontains=query))
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if level:
            qs = qs.filter(degree_level=level)

        context['programs'] = qs.order_by('department__name', 'name')
        context['departments'] = Department.objects.all().order_by('name')
        context['degree_levels'] = Program.DegreeLevel.choices
        context['search_query'] = query
        context['selected_dept'] = dept_id
        context['selected_level'] = level
        return context


class AdminProgramCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = ProgramForm()
        return render(request, 'portal/admin/programs/form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = ProgramForm(request.POST)
        if form.is_valid():
            prog = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_PROGRAM', details={'program_id': prog.pk, 'code': prog.code})
            messages.success(request, f"Program '{prog.name}' ({prog.code}) created successfully.")
            return redirect('portal_admin:program_list')
        return render(request, 'portal/admin/programs/form.html', {'form': form, 'is_create': True})


class AdminProgramEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        prog = get_object_or_404(Program, pk=pk)
        form = ProgramForm(instance=prog)
        return render(request, 'portal/admin/programs/form.html', {'form': form, 'program': prog, 'is_create': False})

    def post(self, request, pk):
        prog = get_object_or_404(Program, pk=pk)
        form = ProgramForm(request.POST, instance=prog)
        if form.is_valid():
            prog = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_PROGRAM', details={'program_id': prog.pk, 'code': prog.code})
            messages.success(request, f"Program '{prog.name}' updated successfully.")
            return redirect('portal_admin:program_list')
        return render(request, 'portal/admin/programs/form.html', {'form': form, 'program': prog, 'is_create': False})


class AdminProgramToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        prog = get_object_or_404(Program, pk=pk)
        prog.is_active = not prog.is_active
        prog.save()
        status_str = "activated" if prog.is_active else "archived / deactivated"
        AuditLog.log_action(user=request.user, action='TOGGLE_PROGRAM_STATUS', details={'program_id': prog.pk, 'is_active': prog.is_active})
        messages.success(request, f"Program '{prog.name}' is now {status_str}.")
        return redirect('portal_admin:program_list')


# ============================================================================
# 4. Academic Periods & Terms Management
# ============================================================================

class AdminTermsListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/terms/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all().prefetch_related('semesters').order_by('-start_date')
        context['semesters'] = Semester.objects.select_related('academic_year').order_by('-start_date')
        return context


class AdminYearCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = AcademicYearForm()
        return render(request, 'portal/admin/terms/year_form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            ay = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_ACADEMIC_YEAR', details={'year_id': ay.pk, 'name': ay.name})
            messages.success(request, f"Academic Year '{ay.name}' created successfully.")
            return redirect('portal_admin:terms_list')
        return render(request, 'portal/admin/terms/year_form.html', {'form': form, 'is_create': True})


class AdminYearEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        ay = get_object_or_404(AcademicYear, pk=pk)
        form = AcademicYearForm(instance=ay)
        return render(request, 'portal/admin/terms/year_form.html', {'form': form, 'year': ay, 'is_create': False})

    def post(self, request, pk):
        ay = get_object_or_404(AcademicYear, pk=pk)
        form = AcademicYearForm(request.POST, instance=ay)
        if form.is_valid():
            ay = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_ACADEMIC_YEAR', details={'year_id': ay.pk, 'name': ay.name})
            messages.success(request, f"Academic Year '{ay.name}' updated successfully.")
            return redirect('portal_admin:terms_list')
        return render(request, 'portal/admin/terms/year_form.html', {'form': form, 'year': ay, 'is_create': False})


class AdminSemesterCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = SemesterForm()
        return render(request, 'portal/admin/terms/semester_form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = SemesterForm(request.POST)
        if form.is_valid():
            sem = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_SEMESTER', details={'semester_id': sem.pk, 'name': sem.name})
            messages.success(request, f"Semester '{sem.name}' created successfully.")
            return redirect('portal_admin:terms_list')
        return render(request, 'portal/admin/terms/semester_form.html', {'form': form, 'is_create': True})


class AdminSemesterEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        sem = get_object_or_404(Semester, pk=pk)
        form = SemesterForm(instance=sem)
        return render(request, 'portal/admin/terms/semester_form.html', {'form': form, 'semester': sem, 'is_create': False})

    def post(self, request, pk):
        sem = get_object_or_404(Semester, pk=pk)
        form = SemesterForm(request.POST, instance=sem)
        if form.is_valid():
            sem = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_SEMESTER', details={'semester_id': sem.pk, 'name': sem.name})
            messages.success(request, f"Semester '{sem.name}' updated successfully.")
            return redirect('portal_admin:terms_list')
        return render(request, 'portal/admin/terms/semester_form.html', {'form': form, 'semester': sem, 'is_create': False})


class AdminSemesterToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        sem = get_object_or_404(Semester, pk=pk)
        sem.is_active = True
        sem.save()
        AuditLog.log_action(user=request.user, action='SET_ACTIVE_SEMESTER', details={'semester_id': sem.pk, 'name': sem.name})
        messages.success(request, f"Semester '{sem.name}' is now set as the active ongoing semester.")
        return redirect('portal_admin:terms_list')


# ============================================================================
# 5. Student Management
# ============================================================================

class AdminStudentListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/students/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department')
        prog_id = self.request.GET.get('program')
        status = self.request.GET.get('status')

        qs = StudentProfile.objects.select_related('user', 'department', 'program').order_by('student_id')

        if query:
            qs = qs.filter(
                models.Q(student_id__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query) |
                models.Q(user__email__icontains=query)
            )
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if prog_id:
            qs = qs.filter(program_id=prog_id)
        if status:
            qs = qs.filter(academic_status=status)

        paginator = Paginator(qs, 15)
        page = self.request.GET.get('page')
        students = paginator.get_page(page)

        context['students'] = students
        context['departments'] = Department.objects.all().order_by('name')
        context['programs'] = Program.objects.all().order_by('name')
        context['statuses'] = StudentProfile.AcademicStatus.choices
        context['search_query'] = query
        context['selected_dept'] = dept_id
        context['selected_prog'] = prog_id
        context['selected_status'] = status
        return context


class AdminStudentCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = StudentCreateForm()
        return render(request, 'portal/admin/students/form.html', {'form': form, 'is_create': True})

    @transaction.atomic
    def post(self, request):
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_number=data['phone_number'],
                role=Role.STUDENT
            )
            profile = StudentProfile.objects.create(
                user=user,
                student_id=data['student_id'],
                department=data['department'],
                program=data['program'],
                current_semester=data['current_semester'],
                academic_year=data['academic_year'],
                academic_status=data['academic_status']
            )
            AuditLog.log_action(user=request.user, action='CREATE_STUDENT', details={'student_id': profile.student_id, 'user_id': user.pk})
            messages.success(request, f"Student '{user.get_full_name()}' ({profile.student_id}) enrolled successfully.")
            return redirect('portal_admin:student_list')
        return render(request, 'portal/admin/students/form.html', {'form': form, 'is_create': True})


class AdminStudentEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user', 'department', 'program'), pk=pk)
        form = StudentEditForm(instance=student)
        return render(request, 'portal/admin/students/form.html', {'form': form, 'student': student, 'is_create': False})

    @transaction.atomic
    def post(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            # Update user info
            user = student.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.phone_number = form.cleaned_data['phone_number']
            user.is_active = form.cleaned_data['is_active_user']
            user.save()

            student = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_STUDENT', details={'student_id': student.student_id})
            messages.success(request, f"Student profile '{student.student_id}' updated successfully.")
            return redirect('portal_admin:student_list')
        return render(request, 'portal/admin/students/form.html', {'form': form, 'student': student, 'is_create': False})


class AdminStudentToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        student = get_object_or_404(StudentProfile, pk=pk)
        new_status = request.POST.get('status')
        if new_status in StudentProfile.AcademicStatus.values:
            student.academic_status = new_status
            student.save()
            AuditLog.log_action(user=request.user, action='CHANGE_STUDENT_STATUS', details={'student_id': student.student_id, 'status': new_status})
            messages.success(request, f"Student '{student.student_id}' status changed to {student.get_academic_status_display()}.")
        return redirect('portal_admin:student_list')


# ============================================================================
# 6. Teacher Management
# ============================================================================

class AdminTeacherListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/teachers/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department')

        qs = TeacherProfile.objects.select_related('user', 'department').prefetch_related('assigned_sections').order_by('employee_id')

        if query:
            qs = qs.filter(
                models.Q(employee_id__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query) |
                models.Q(user__email__icontains=query)
            )
        if dept_id:
            qs = qs.filter(department_id=dept_id)

        paginator = Paginator(qs, 15)
        page = self.request.GET.get('page')
        teachers = paginator.get_page(page)

        context['teachers'] = teachers
        context['departments'] = Department.objects.all().order_by('name')
        context['search_query'] = query
        context['selected_dept'] = dept_id
        return context


class AdminTeacherCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = TeacherCreateForm()
        return render(request, 'portal/admin/teachers/form.html', {'form': form, 'is_create': True})

    @transaction.atomic
    def post(self, request):
        form = TeacherCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_number=data['phone_number'],
                role=Role.TEACHER
            )
            profile = TeacherProfile.objects.create(
                user=user,
                employee_id=data['employee_id'],
                department=data['department'],
                designation=data['designation'],
                qualification=data['qualification'],
                office_location=data['office_location']
            )
            AuditLog.log_action(user=request.user, action='CREATE_TEACHER', details={'employee_id': profile.employee_id, 'user_id': user.pk})
            messages.success(request, f"Teacher '{user.get_full_name()}' ({profile.employee_id}) created successfully.")
            return redirect('portal_admin:teacher_list')
        return render(request, 'portal/admin/teachers/form.html', {'form': form, 'is_create': True})


class AdminTeacherEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        teacher = get_object_or_404(TeacherProfile.objects.select_related('user', 'department'), pk=pk)
        form = TeacherEditForm(instance=teacher)
        return render(request, 'portal/admin/teachers/form.html', {'form': form, 'teacher': teacher, 'is_create': False})

    @transaction.atomic
    def post(self, request, pk):
        teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=pk)
        form = TeacherEditForm(request.POST, instance=teacher)
        if form.is_valid():
            user = teacher.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.phone_number = form.cleaned_data['phone_number']
            user.is_active = form.cleaned_data['is_active_user']
            user.save()

            teacher = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_TEACHER', details={'employee_id': teacher.employee_id})
            messages.success(request, f"Teacher '{teacher.employee_id}' updated successfully.")
            return redirect('portal_admin:teacher_list')
        return render(request, 'portal/admin/teachers/form.html', {'form': form, 'teacher': teacher, 'is_create': False})


class AdminTeacherToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=pk)
        user = teacher.user
        user.is_active = not user.is_active
        user.save()
        status_str = "activated" if user.is_active else "deactivated / archived"
        AuditLog.log_action(user=request.user, action='TOGGLE_TEACHER_STATUS', details={'employee_id': teacher.employee_id, 'is_active': user.is_active})
        messages.success(request, f"Teacher account '{user.get_full_name()}' is now {status_str}.")
        return redirect('portal_admin:teacher_list')


# ============================================================================
# 7. Courses & Topics Management
# ============================================================================

class AdminCoursesView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/courses/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department')
        prog_id = self.request.GET.get('program')

        courses = Course.objects.all().select_related('department').prefetch_related('programs', 'topics')
        if query:
            courses = courses.filter(models.Q(code__icontains=query) | models.Q(title__icontains=query))
        if dept_id:
            courses = courses.filter(department_id=dept_id)
        if prog_id:
            courses = courses.filter(programs__id=prog_id)

        paginator = Paginator(courses, 12)
        page = self.request.GET.get('page')

        context['courses'] = paginator.get_page(page)
        context['departments'] = Department.objects.all().order_by('name')
        context['programs'] = Program.objects.all().order_by('name')
        context['search_query'] = query
        context['selected_dept'] = dept_id
        context['selected_prog'] = prog_id
        return context


class AdminCourseCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = CourseForm()
        return render(request, 'portal/admin/courses/form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_COURSE', details={'course_id': course.pk, 'code': course.code})
            messages.success(request, f"Course '{course.code}' ({course.title}) created successfully.")
            return redirect('portal_admin:courses')
        return render(request, 'portal/admin/courses/form.html', {'form': form, 'is_create': True})


class AdminCourseEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        form = CourseForm(instance=course)
        topics = course.topics.all().order_by('order_index')
        topic_form = TopicForm(initial={'course': course, 'order_index': topics.count() + 1})
        return render(request, 'portal/admin/courses/form.html', {
            'form': form,
            'course': course,
            'topics': topics,
            'topic_form': topic_form,
            'is_create': False
        })

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_COURSE', details={'course_id': course.pk, 'code': course.code})
            messages.success(request, f"Course '{course.code}' updated successfully.")
            return redirect('portal_admin:courses')
        topics = course.topics.all().order_by('order_index')
        topic_form = TopicForm(initial={'course': course, 'order_index': topics.count() + 1})
        return render(request, 'portal/admin/courses/form.html', {
            'form': form,
            'course': course,
            'topics': topics,
            'topic_form': topic_form,
            'is_create': False
        })


class AdminCourseToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        course.is_active = not course.is_active
        course.save()
        status_str = "activated" if course.is_active else "archived / deactivated"
        AuditLog.log_action(user=request.user, action='TOGGLE_COURSE_STATUS', details={'course_id': course.pk, 'is_active': course.is_active})
        messages.success(request, f"Course '{course.code}' is now {status_str}.")
        return redirect('portal_admin:courses')


class AdminTopicCreateView(AdminRequiredMixin, View):
    def post(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id)
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.course = course
            topic.save()
            messages.success(request, f"Topic '{topic.title}' added to course {course.code}.")
        else:
            messages.error(request, "Failed to create topic. Check sequence order.")
        return redirect('portal_admin:course_edit', pk=course_id)


class AdminTopicDeleteView(AdminRequiredMixin, View):
    def post(self, request, course_id, topic_id):
        topic = get_object_or_404(Topic, pk=topic_id, course_id=course_id)
        topic.delete()
        messages.success(request, f"Topic '{topic.title}' deleted from syllabus.")
        return redirect('portal_admin:course_edit', pk=course_id)


# ============================================================================
# 8. Class Section Management
# ============================================================================

class AdminSectionsView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/sections/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get('semester')
        dept_id = self.request.GET.get('department')
        query = self.request.GET.get('q', '').strip()

        sections = ClassSection.objects.all().select_related('course__department', 'semester', 'primary_teacher__user').prefetch_related('enrollments')

        if semester_id:
            sections = sections.filter(semester_id=semester_id)
        else:
            active_sem = Semester.objects.filter(is_active=True).first()
            if active_sem:
                sections = sections.filter(semester=active_sem)
                semester_id = active_sem.pk

        if dept_id:
            sections = sections.filter(course__department_id=dept_id)
        if query:
            sections = sections.filter(models.Q(course__code__icontains=query) | models.Q(course__title__icontains=query) | models.Q(section_code__icontains=query))

        context['sections'] = sections.order_by('-semester__start_date', 'course__code')
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['departments'] = Department.objects.all().order_by('name')
        context['selected_semester'] = int(semester_id) if semester_id else None
        context['selected_dept'] = int(dept_id) if dept_id else None
        context['search_query'] = query
        return context


class AdminSectionCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = ClassSectionForm()
        return render(request, 'portal/admin/sections/form.html', {'form': form, 'is_create': True})

    def post(self, request):
        form = ClassSectionForm(request.POST)
        if form.is_valid():
            sec = form.save()
            AuditLog.log_action(user=request.user, action='CREATE_CLASS_SECTION', details={'section_id': sec.pk, 'course': sec.course.code, 'section': sec.section_code})
            messages.success(request, f"Class Section '{sec}' created successfully.")
            return redirect('portal_admin:sections')
        return render(request, 'portal/admin/sections/form.html', {'form': form, 'is_create': True})


class AdminSectionEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        sec = get_object_or_404(ClassSection, pk=pk)
        form = ClassSectionForm(instance=sec)
        return render(request, 'portal/admin/sections/form.html', {'form': form, 'section': sec, 'is_create': False})

    def post(self, request, pk):
        sec = get_object_or_404(ClassSection, pk=pk)
        form = ClassSectionForm(request.POST, instance=sec)
        if form.is_valid():
            sec = form.save()
            AuditLog.log_action(user=request.user, action='EDIT_CLASS_SECTION', details={'section_id': sec.pk, 'course': sec.course.code})
            messages.success(request, f"Class Section '{sec}' updated successfully.")
            return redirect('portal_admin:sections')
        return render(request, 'portal/admin/sections/form.html', {'form': form, 'section': sec, 'is_create': False})


class AdminSectionToggleStatusView(AdminRequiredMixin, View):
    def post(self, request, pk):
        sec = get_object_or_404(ClassSection, pk=pk)
        sec.is_active = not sec.is_active
        sec.save()
        status_str = "activated" if sec.is_active else "archived / deactivated"
        AuditLog.log_action(user=request.user, action='TOGGLE_SECTION_STATUS', details={'section_id': sec.pk, 'is_active': sec.is_active})
        messages.success(request, f"Section '{sec}' is now {status_str}.")
        return redirect('portal_admin:sections')


class AdminSectionRosterView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/sections/roster.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sec_id = self.kwargs.get('pk')
        section = get_object_or_404(ClassSection.objects.select_related('course', 'semester', 'primary_teacher__user'), pk=sec_id)
        roster = EnrollmentService.get_section_roster(section, active_only=False)

        context['section'] = section
        context['roster'] = roster
        return context


# ============================================================================
# 9. Enrollment Management
# ============================================================================

class AdminEnrollmentsView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/enrollments/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get('semester')
        section_id = self.request.GET.get('section')
        status = self.request.GET.get('status')
        query = self.request.GET.get('q', '').strip()

        enrollments = Enrollment.objects.all().select_related(
            'student__user',
            'student__program',
            'class_section__course',
            'class_section__semester',
            'class_section__primary_teacher__user'
        )

        if semester_id:
            enrollments = enrollments.filter(class_section__semester_id=semester_id)
        else:
            active_sem = Semester.objects.filter(is_active=True).first()
            if active_sem:
                enrollments = enrollments.filter(class_section__semester=active_sem)
                semester_id = active_sem.pk

        if section_id:
            enrollments = enrollments.filter(class_section_id=section_id)
        if status:
            enrollments = enrollments.filter(status=status)
        if query:
            enrollments = enrollments.filter(
                models.Q(student__student_id__icontains=query) |
                models.Q(student__user__first_name__icontains=query) |
                models.Q(student__user__last_name__icontains=query) |
                models.Q(class_section__course__code__icontains=query)
            )

        paginator = Paginator(enrollments.order_by('-class_section__semester__start_date', 'student__student_id'), 20)
        page = self.request.GET.get('page')

        context['enrollments'] = paginator.get_page(page)
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['sections'] = ClassSection.objects.filter(is_active=True).select_related('course')
        context['statuses'] = Enrollment.EnrollmentStatus.choices
        context['selected_semester'] = int(semester_id) if semester_id else None
        context['selected_section'] = int(section_id) if section_id else None
        context['selected_status'] = status
        context['search_query'] = query

        # Students & sections for manual enroll modal
        context['eligible_students'] = StudentProfile.objects.filter(academic_status=StudentProfile.AcademicStatus.ACTIVE).select_related('user', 'program')
        return context


class AdminEnrollmentCreateView(AdminRequiredMixin, View):
    def post(self, request):
        student_id = request.POST.get('student')
        section_id = request.POST.get('class_section')

        student = get_object_or_404(StudentProfile, pk=student_id)
        section = get_object_or_404(ClassSection, pk=section_id)

        try:
            enr = EnrollmentService.enroll_student(student=student, class_section=section, actor=request.user)
            messages.success(request, f"Student '{student.student_id}' successfully enrolled in '{section}'.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('portal_admin:enrollments')


class AdminEnrollmentDropView(AdminRequiredMixin, View):
    def post(self, request, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        try:
            EnrollmentService.drop_student(student=enrollment.student, class_section=enrollment.class_section, actor=request.user)
            messages.success(request, f"Student '{enrollment.student.student_id}' dropped from '{enrollment.class_section}'.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('portal_admin:enrollments')


class AdminEnrollmentReEnrollView(AdminRequiredMixin, View):
    def post(self, request, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        try:
            EnrollmentService.enroll_student(student=enrollment.student, class_section=enrollment.class_section, actor=request.user)
            messages.success(request, f"Student '{enrollment.student.student_id}' re-enrolled in '{enrollment.class_section}'.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('portal_admin:enrollments')


# ============================================================================
# 10. Timetable Management
# ============================================================================

class AdminTimetableView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/timetable/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get('semester')
        view_mode = self.request.GET.get('view_mode', 'day')  # day, section, teacher

        if semester_id:
            semester = Semester.objects.filter(pk=semester_id).first()
        else:
            semester = Semester.objects.filter(is_active=True).first()

        schedules = ClassSchedule.objects.all().select_related(
            'class_section__course',
            'class_section__semester',
            'teacher__user'
        )

        if semester:
            schedules = schedules.filter(class_section__semester=semester)

        days_map = {day: [] for day in range(1, 8)}
        for entry in schedules.order_by('day_of_week', 'start_time'):
            days_map[entry.day_of_week].append(entry)

        context['schedules'] = schedules.order_by('day_of_week', 'start_time')
        context['days_map'] = days_map
        context['day_choices'] = [
            (1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'),
            (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')
        ]
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['selected_semester'] = semester
        context['view_mode'] = view_mode
        context['schedule_form'] = ClassScheduleForm()
        context['sections'] = ClassSection.objects.filter(is_active=True, semester=semester).select_related('course') if semester else []
        return context


class AdminTimetableCreateView(AdminRequiredMixin, View):
    def post(self, request):
        form = ClassScheduleForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                entry = ScheduleService.create_schedule_entry(
                    class_section=data['class_section'],
                    teacher=data['teacher'],
                    day_of_week=data['day_of_week'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    room=data['room']
                )
                AuditLog.log_action(user=request.user, action='CREATE_SCHEDULE_SLOT', details={'slot_id': entry.pk, 'section': str(entry.class_section)})
                messages.success(request, f"Timetable slot created successfully for {entry.class_section}.")
            except ValidationError as e:
                messages.error(request, str(e.message_dict if hasattr(e, 'message_dict') else e))
        else:
            messages.error(request, "Invalid schedule data submitted.")
        return redirect('portal_admin:timetable')


class AdminTimetableDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(ClassSchedule, pk=pk)
        AuditLog.log_action(user=request.user, action='DELETE_SCHEDULE_SLOT', details={'slot_id': entry.pk, 'section': str(entry.class_section)})
        entry.delete()
        messages.success(request, "Timetable slot deleted successfully.")
        return redirect('portal_admin:timetable')


# ============================================================================
# 11. Attendance Oversight
# ============================================================================

class AdminAttendanceListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/attendance/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get('semester')
        section_id = self.request.GET.get('section')
        date_filter = self.request.GET.get('date')

        sessions = ClassSession.objects.all().select_related(
            'class_section__course',
            'class_section__semester',
            'teacher__user',
            'topic'
        ).prefetch_related('attendance_records')

        if semester_id:
            sessions = sessions.filter(class_section__semester_id=semester_id)
        else:
            active_sem = Semester.objects.filter(is_active=True).first()
            if active_sem:
                sessions = sessions.filter(class_section__semester=active_sem)
                semester_id = active_sem.pk

        if section_id:
            sessions = sessions.filter(class_section_id=section_id)
        if date_filter:
            sessions = sessions.filter(session_date=date_filter)

        paginator = Paginator(sessions.order_by('-session_date', '-created_at'), 15)
        page = self.request.GET.get('page')

        context['sessions'] = paginator.get_page(page)
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['sections'] = ClassSection.objects.filter(is_active=True).select_related('course')
        context['selected_semester'] = int(semester_id) if semester_id else None
        context['selected_section'] = int(section_id) if section_id else None
        context['selected_date'] = date_filter
        return context


class AdminAttendanceSessionDetailView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/attendance/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = self.kwargs.get('pk')
        session = get_object_or_404(
            ClassSession.objects.select_related(
                'class_section__course',
                'class_section__semester',
                'teacher__user',
                'topic'
            ),
            pk=session_id
        )
        records = session.attendance_records.select_related('student__user', 'student__program').order_by('student__student_id')

        context['session'] = session
        context['records'] = records
        return context


# ============================================================================
# 12. Assessment & Grade Oversight
# ============================================================================

class AdminAssessmentListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/assessments/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get('semester')
        section_id = self.request.GET.get('section')

        assessments = Assessment.objects.all().select_related(
            'class_section__course',
            'class_section__semester',
            'topic'
        ).prefetch_related('results')

        if semester_id:
            assessments = assessments.filter(class_section__semester_id=semester_id)
        else:
            active_sem = Semester.objects.filter(is_active=True).first()
            if active_sem:
                assessments = assessments.filter(class_section__semester=active_sem)
                semester_id = active_sem.pk

        if section_id:
            assessments = assessments.filter(class_section_id=section_id)

        context['assessments'] = assessments.order_by('-date')
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['sections'] = ClassSection.objects.filter(is_active=True).select_related('course')
        context['selected_semester'] = int(semester_id) if semester_id else None
        context['selected_section'] = int(section_id) if section_id else None
        return context


class AdminGradeRecalculateView(AdminRequiredMixin, View):
    """
    Force authoritative recalculation of an enrollment grade snapshot via GradingService.
    """
    def post(self, request, enrollment_id):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
        GradingService.recalculate_and_update_enrollment_snapshot(enrollment, actor=request.user)
        messages.success(request, f"Recalculated grade snapshot for student '{enrollment.student.student_id}'.")
        return redirect('portal_admin:records')


# ============================================================================
# 13. Learning Resources & Announcements Oversight
# ============================================================================

class AdminResourceListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/resources/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.request.GET.get('course')
        qs = LearningResource.objects.all().select_related('course', 'topic', 'uploaded_by')
        if course_id:
            qs = qs.filter(course_id=course_id)

        context['resources'] = qs.order_by('-created_at')
        context['courses'] = Course.objects.filter(is_active=True)
        context['selected_course'] = int(course_id) if course_id else None
        return context


class AdminResourceDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        res = get_object_or_404(LearningResource, pk=pk)
        AuditLog.log_action(user=request.user, action='DELETE_LEARNING_RESOURCE', details={'resource_id': res.pk, 'title': res.title})
        res.delete()
        messages.success(request, "Learning resource deleted successfully.")
        return redirect('portal_admin:resource_list')


class AdminAnnouncementListView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/announcements/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        announcements = CourseAnnouncement.objects.all().select_related('class_section__course', 'teacher__user')
        context['announcements'] = announcements.order_by('-created_at')
        return context


class AdminAnnouncementDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        ann = get_object_or_404(CourseAnnouncement, pk=pk)
        AuditLog.log_action(user=request.user, action='DELETE_ANNOUNCEMENT', details={'announcement_id': ann.pk, 'title': ann.title})
        ann.delete()
        messages.success(request, "Announcement deleted successfully.")
        return redirect('portal_admin:announcement_list')


# ============================================================================
# 14. Academic Records Lookup
# ============================================================================

class AdminAcademicRecordsView(AdminRequiredMixin, TemplateView):
    template_name = 'portal/admin/records.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        students = StudentProfile.objects.all().select_related('user', 'program', 'department')

        if query:
            students = students.filter(
                models.Q(student_id__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query) |
                models.Q(user__email__icontains=query)
            )

        selected_student_id = self.request.GET.get('student_id')
        selected_student = None
        student_history = []

        if selected_student_id:
            selected_student = StudentProfile.objects.filter(pk=selected_student_id).select_related('user', 'program', 'department').first()
            if selected_student:
                student_history = EnrollmentService.get_student_enrollments(selected_student)

        context['students'] = students[:20]
        context['selected_student'] = selected_student
        context['student_history'] = student_history
        context['search_query'] = query
        return context
