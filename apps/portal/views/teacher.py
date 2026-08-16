"""
Teacher portal views for Phase 2 Academic Management.
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import TeacherRequiredMixin
from apps.academic.models import (
    TeacherProfile,
    ClassSection,
    ClassSession,
    AttendanceRecord,
    Assignment,
    AssignmentSubmission,
    Assessment,
    AssessmentResult,
    Enrollment,
    Semester,
    Course,
    Topic,
    LearningResource,
    CourseAnnouncement
)
from apps.academic.forms import (
    AssignmentForm,
    AssessmentForm,
    LearningResourceForm,
    CourseAnnouncementForm
)
from apps.academic.services import (
    EnrollmentService,
    AttendanceService,
    AssignmentService,
    GradingService,
    ScheduleService,
    ResourceService
)
from apps.analytics.services import (
    RiskEngineService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    PerformanceAnalyticsService,
    TrendAnalyticsService,
    AnomalyDetectionService,
    TopicAnalyticsService
)
from apps.interventions.models import Intervention


class TeacherDashboardView(TeacherRequiredMixin, TemplateView):
    """
    Primary faculty dashboard featuring the Student Attention Radar:
    Categorizes roster students deterministically into CRITICAL, HIGH, MEDIUM, and STABLE tiers.
    """
    template_name = 'portal/teacher/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            teacher = TeacherProfile.objects.select_related('department').get(user=user)
        except TeacherProfile.DoesNotExist:
            teacher = None

        context['teacher_profile'] = teacher
        context['page_title'] = 'Faculty Command Hub & Attention Radar'

        if teacher:
            active_semester = Semester.objects.filter(is_active=True).first()
            context['active_semester'] = active_semester

            assigned_sections = ClassSection.objects.filter(
                primary_teacher=teacher,
                semester=active_semester
            ).select_related('course', 'semester')
            context['assigned_sections'] = assigned_sections

            # Total enrolled students
            enrollments = Enrollment.objects.filter(
                class_section__in=assigned_sections,
                status=Enrollment.EnrollmentStatus.ENROLLED
            ).select_related('student__user', 'student__program', 'class_section__course')

            context['total_students_enrolled'] = enrollments.count()

            # Pending submissions count
            pending_submissions = AssignmentSubmission.objects.filter(
                assignment__class_section__in=assigned_sections,
                status__in=[AssignmentSubmission.SubmissionStatus.SUBMITTED, AssignmentSubmission.SubmissionStatus.LATE]
            ).count()
            context['pending_submissions_count'] = pending_submissions

            # -------------------------------------------------------------
            # Student Attention Radar (Deterministic Triage)
            # -------------------------------------------------------------
            critical_radar = []
            high_radar = []
            medium_radar = []
            stable_radar = []

            for enr in enrollments:
                st = enr.student
                sec = enr.class_section

                risk_res = RiskEngineService.evaluate_course_risk(st, sec)
                att_res = AttendanceAnalyticsService.calculate_course_attendance(st, sec)
                anom_res = AnomalyDetectionService.detect_course_anomaly(st, sec)
                course_trend = TrendAnalyticsService.calculate_course_trajectory(st, sec)

                intvs_count = Intervention.objects.filter(
                    student=st,
                    class_section=sec,
                    status__in=[Intervention.Status.ASSIGNED, Intervention.Status.IN_PROGRESS]
                ).count()

                item = {
                    'student': st,
                    'student_name': st.user.get_full_name(),
                    'student_id': st.student_id,
                    'course_code': sec.course.code,
                    'section_id': sec.pk,
                    'risk_score': risk_res.composite_score if risk_res else 0.0,
                    'risk_level': str(risk_res.risk_level) if risk_res else 'LOW',
                    'attendance_pct': att_res.attendance_percentage if att_res else 100.0,
                    'absence_buffer': att_res.absence_buffer if att_res else 0,
                    'is_anomaly': anom_res.is_anomaly if anom_res else False,
                    'anomaly_desc': anom_res.description if anom_res and anom_res.is_anomaly else None,
                    'trajectory': str(course_trend.direction) if course_trend else 'STABLE',
                    'active_interventions': intvs_count
                }

                # Deterministic Tier Placement
                if item['risk_level'] == 'CRITICAL' or item['is_anomaly'] or item['attendance_pct'] < 50.0:
                    item['tier'] = 'CRITICAL'
                    item['badge_class'] = 'badge-danger'
                    critical_radar.append(item)
                elif item['risk_level'] == 'HIGH' or item['attendance_pct'] < 60.0:
                    item['tier'] = 'HIGH'
                    item['badge_class'] = 'badge-danger'
                    high_radar.append(item)
                elif item['risk_level'] == 'MODERATE' or item['trajectory'] == 'DECLINING':
                    item['tier'] = 'MEDIUM'
                    item['badge_class'] = 'badge-warning'
                    medium_radar.append(item)
                else:
                    item['tier'] = 'STABLE'
                    item['badge_class'] = 'badge-success'
                    stable_radar.append(item)

            # Sort within tiers
            critical_radar.sort(key=lambda x: x['risk_score'], reverse=True)
            high_radar.sort(key=lambda x: x['risk_score'], reverse=True)
            medium_radar.sort(key=lambda x: x['risk_score'], reverse=True)
            stable_radar.sort(key=lambda x: x['risk_score'], reverse=True)

            context['attention_radar'] = {
                'critical': critical_radar,
                'high': high_radar,
                'medium': medium_radar,
                'stable': stable_radar,
                'total_monitored': len(enrollments),
                'needs_attention_count': len(critical_radar) + len(high_radar)
            }

            # Today's teaching schedule
            import datetime
            today_day = datetime.datetime.today().isoweekday()
            timetable = ScheduleService.get_teacher_weekly_timetable(teacher, semester=active_semester)
            context['today_schedule'] = timetable.filter(day_of_week=today_day)

        return context


class TeacherCourseIntelligenceView(TeacherRequiredMixin, TemplateView):
    """
    Deep curricular intelligence: Topic friction analysis, grade distributions, and attendance profiles.
    """
    template_name = 'portal/teacher/course_intelligence.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        section_id = self.kwargs.get('section_id')
        section = get_object_or_404(ClassSection, pk=section_id, primary_teacher=teacher)

        enrollments = Enrollment.objects.filter(class_section=section, status='ENROLLED').select_related('student__user')
        topics = Topic.objects.filter(course=section.course).order_by('order_index')

        # Compute topic friction
        topic_analysis = []
        for t in topics:
            scores = []
            for enr in enrollments:
                tm = TopicAnalyticsService.calculate_topic_mastery(enr.student, section)
                for item in tm:
                    if item.get('topic_id') == t.pk and item.get('score_percentage') is not None:
                        scores.append(item['score_percentage'])
            avg_score = round(sum(scores) / len(scores), 1) if scores else None
            topic_analysis.append({
                'topic': t,
                'average_score': avg_score,
                'friction_level': 'HIGH' if (avg_score is not None and avg_score < 60.0) else ('MODERATE' if (avg_score is not None and avg_score < 75.0) else 'LOW')
            })

        context['section'] = section
        context['topic_analysis'] = topic_analysis
        context['enrolled_count'] = enrollments.count()
        return context


class TeacherAssessmentIntelligenceView(TeacherRequiredMixin, TemplateView):
    """
    Assessment-level analytics: Mean, median, distribution quartiles, and completion tracking.
    """
    template_name = 'portal/teacher/assessment_intelligence.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        assessment_id = self.kwargs.get('assessment_id')
        assessment = get_object_or_404(Assessment, pk=assessment_id, class_section__primary_teacher=teacher)

        results = AssessmentResult.objects.filter(assessment=assessment).select_related('student__user')
        scores = [float(r.percentage) for r in results]

        import statistics
        mean_score = round(statistics.mean(scores), 1) if scores else 0.0
        median_score = round(statistics.median(scores), 1) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        std_dev = round(statistics.stdev(scores), 1) if len(scores) > 1 else 0.0

        context['assessment'] = assessment
        context['results'] = results
        context['stats'] = {
            'mean': mean_score,
            'median': median_score,
            'min': min_score,
            'max': max_score,
            'std_dev': std_dev,
            'count': len(scores)
        }
        return context


class TeacherEarlyWarningsView(TeacherRequiredMixin, TemplateView):
    """
    Chronological teacher early-warning timeline.
    """
    template_name = 'portal/teacher/early_warnings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher, semester__is_active=True)

        warnings = []
        for sec in sections:
            enrollments = Enrollment.objects.filter(class_section=sec, status='ENROLLED').select_related('student__user')
            for enr in enrollments:
                st = enr.student
                anom = AnomalyDetectionService.detect_course_anomaly(st, sec)
                if anom and anom.is_anomaly:
                    warnings.append({
                        'timestamp': timezone.now(),
                        'student_name': st.user.get_full_name(),
                        'student_id': st.student_id,
                        'course_code': sec.course.code,
                        'warning_type': 'ACUTE_ANOMALY',
                        'badge_class': 'badge-danger',
                        'title': f"Acute Score Plunge in {sec.course.code}",
                        'description': anom.description
                    })
                att = AttendanceAnalyticsService.calculate_course_attendance(st, sec)
                if att and att.attendance_percentage < 60.0:
                    warnings.append({
                        'timestamp': timezone.now(),
                        'student_name': st.user.get_full_name(),
                        'student_id': st.student_id,
                        'course_code': sec.course.code,
                        'warning_type': 'ATTENDANCE_DEFICIT',
                        'badge_class': 'badge-danger',
                        'title': f"Severe Attendance Deficit ({att.attendance_percentage:.1f}%)",
                        'description': f"Student has missed {att.absent_count} sessions. Absence buffer is 0."
                    })

        context['early_warnings'] = warnings
        return context


class TeacherClassesView(TeacherRequiredMixin, TemplateView):
    """
    List all class sections assigned to the faculty member.
    """
    template_name = 'portal/teacher/classes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile

        selected_semester_id = self.request.GET.get('semester')
        if selected_semester_id:
            semester = Semester.objects.filter(pk=selected_semester_id).first()
        else:
            semester = Semester.objects.filter(is_active=True).first()

        sections = ClassSection.objects.filter(primary_teacher=teacher)
        if semester:
            sections = sections.filter(semester=semester)

        context['sections'] = sections.select_related('course', 'semester')
        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['selected_semester'] = semester
        return context


class TeacherClassDetailView(TeacherRequiredMixin, TemplateView):
    """
    Detailed class section dashboard: roster, topics, assignments, announcements.
    """
    template_name = 'portal/teacher/class_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        section_id = self.kwargs.get('section_id')

        section = get_object_or_404(
            ClassSection.objects.select_related('course', 'semester', 'primary_teacher__user'),
            pk=section_id,
            primary_teacher=teacher
        )

        roster = EnrollmentService.get_section_roster(section)
        announcements = ResourceService.get_section_announcements(section)
        assignments = Assignment.objects.filter(class_section=section).order_by('-due_date')
        assessments = Assessment.objects.filter(class_section=section).order_by('date')
        sessions = ClassSession.objects.filter(class_section=section).order_by('-session_date')[:5]

        context['class_section'] = section
        context['roster'] = roster
        context['announcements'] = announcements
        context['assignments'] = assignments
        context['assessments'] = assessments
        context['recent_sessions'] = sessions
        context['topics'] = section.course.topics.all()
        return context


class TeacherAttendanceView(TeacherRequiredMixin, TemplateView):
    """
    Faculty attendance dashboard: past sessions and launch roll-call.
    """
    template_name = 'portal/teacher/attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        sections = ClassSection.objects.filter(primary_teacher=teacher, semester=active_semester).select_related('course')
        selected_section_id = self.request.GET.get('section')

        if selected_section_id:
            selected_section = sections.filter(pk=selected_section_id).first()
        else:
            selected_section = sections.first()

        sessions = []
        roster = []
        if selected_section:
            sessions = ClassSession.objects.filter(class_section=selected_section).order_by('-session_date')
            roster = EnrollmentService.get_section_roster(selected_section)

        context['sections'] = sections
        context['selected_section'] = selected_section
        context['sessions'] = sessions
        context['roster'] = roster
        return context


class TeacherTakeAttendanceView(TeacherRequiredMixin, View):
    """
    Create a new lecture session and submit attendance roll-call.
    """
    template_name = 'portal/teacher/take_attendance.html'

    def get(self, request, section_id):
        teacher = request.user.teacher_profile
        section = get_object_or_404(ClassSection, pk=section_id, primary_teacher=teacher)
        roster = EnrollmentService.get_section_roster(section)
        topics = section.course.topics.all()

        return render(request, self.template_name, {
            'class_section': section,
            'roster': roster,
            'topics': topics,
            'today_date': timezone.now().date().isoformat()
        })

    def post(self, request, section_id):
        teacher = request.user.teacher_profile
        section = get_object_or_404(ClassSection, pk=section_id, primary_teacher=teacher)

        session_date_str = request.POST.get('session_date')
        title = request.POST.get('title', 'Lecture Session').strip()
        topic_id = request.POST.get('topic')
        topic = Topic.objects.filter(pk=topic_id).first() if topic_id else None

        from datetime import date
        try:
            session_date = date.fromisoformat(session_date_str) if session_date_str else timezone.now().date()
        except ValueError:
            session_date = timezone.now().date()

        # Build attendance mapping from POST data
        attendance_dict = {}
        remarks_dict = {}
        roster = EnrollmentService.get_section_roster(section)

        for enrollment in roster:
            student_id = enrollment.student.pk
            status_val = request.POST.get(f'status_{student_id}', AttendanceRecord.AttendanceStatus.PRESENT)
            remarks_val = request.POST.get(f'remarks_{student_id}', '')
            attendance_dict[student_id] = status_val
            remarks_dict[student_id] = remarks_val

        session = AttendanceService.create_session_with_roster(
            class_section=section,
            teacher=teacher,
            session_date=session_date,
            title=title,
            topic=topic,
            actor=request.user
        )

        AttendanceService.mark_attendance(
            session=session,
            attendance_dict=attendance_dict,
            remarks_dict=remarks_dict,
            actor=request.user
        )

        messages.success(request, f"Attendance for session '{title}' on {session_date} logged successfully ({len(attendance_dict)} students).")
        return redirect('portal:teacher_attendance')


class TeacherAssignmentsView(TeacherRequiredMixin, TemplateView):
    """
    Manage coursework assignments for assigned class sections.
    """
    template_name = 'portal/teacher/assignments.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        sections = ClassSection.objects.filter(primary_teacher=teacher, semester=active_semester).select_related('course')
        assignments = Assignment.objects.filter(teacher=teacher).select_related('class_section__course', 'topic').order_by('-due_date')

        context['sections'] = sections
        context['assignments'] = assignments
        return context


class TeacherAssignmentCreateView(TeacherRequiredMixin, View):
    """
    Create a new coursework assignment for assigned class section.
    """
    def get(self, request):
        teacher = request.user.teacher_profile
        form = AssignmentForm()
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        return render(request, 'portal/teacher/assignment_form.html', {'form': form, 'is_create': True})

    def post(self, request):
        teacher = request.user.teacher_profile
        form = AssignmentForm(request.POST, request.FILES)
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = teacher
            assignment.save()
            messages.success(request, f"Assignment '{assignment.title}' created and published successfully.")
            return redirect('portal:teacher_assignments')
        return render(request, 'portal/teacher/assignment_form.html', {'form': form, 'is_create': True})


class TeacherAssignmentSubmissionsView(TeacherRequiredMixin, TemplateView):
    """
    Review and grade submissions for an assignment.
    """
    template_name = 'portal/teacher/submissions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        assignment_id = self.kwargs.get('assignment_id')

        assignment = get_object_or_404(
            Assignment.objects.select_related('class_section__course'),
            pk=assignment_id,
            teacher=teacher
        )

        roster = EnrollmentService.get_section_roster(assignment.class_section)
        submissions_map = {
            s.student_id: s
            for s in AssignmentSubmission.objects.filter(assignment=assignment).select_related('student__user')
        }

        submission_rows = []
        for enrollment in roster:
            student = enrollment.student
            sub = submissions_map.get(student.pk)
            submission_rows.append({
                'student': student,
                'submission': sub,
                'status': sub.get_status_display() if sub else 'Not Submitted'
            })

        context['assignment'] = assignment
        context['submission_rows'] = submission_rows
        return context


class TeacherGradeSubmissionView(TeacherRequiredMixin, View):
    """
    Save grade and feedback for an individual assignment submission.
    """
    def post(self, request, submission_id):
        teacher = request.user.teacher_profile
        submission = get_object_or_404(
            AssignmentSubmission.objects.select_related('assignment'),
            pk=submission_id,
            assignment__teacher=teacher
        )

        marks_str = request.POST.get('obtained_marks', '0.00')
        feedback = request.POST.get('feedback', '').strip()

        try:
            AssignmentService.grade_submission(
                submission=submission,
                teacher=teacher,
                marks=Decimal(marks_str),
                feedback=feedback,
                actor=request.user
            )
            messages.success(request, f"Grade updated for student '{submission.student.student_id}'.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('portal:teacher_assignment_submissions', assignment_id=submission.assignment.pk)


class TeacherGradebookView(TeacherRequiredMixin, TemplateView):
    """
    Interactive Gradebook matrix for a class section.
    Allows entering marks, calculating weighted totals, and publishing grades.
    """
    template_name = 'portal/teacher/gradebook.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        sections = ClassSection.objects.filter(primary_teacher=teacher, semester=active_semester).select_related('course')
        selected_section_id = self.request.GET.get('section')

        if selected_section_id:
            selected_section = sections.filter(pk=selected_section_id).first()
        else:
            selected_section = sections.first()

        gradebook_data = None
        if selected_section:
            gradebook_data = GradingService.calculate_section_gradebook(selected_section)

        context['sections'] = sections
        context['selected_section'] = selected_section
        context['gradebook_data'] = gradebook_data
        return context


class TeacherPublishGradesView(TeacherRequiredMixin, View):
    """
    Publish calculated gradebook totals to student Enrollment snapshots.
    """
    def post(self, request, section_id):
        teacher = request.user.teacher_profile
        section = get_object_or_404(ClassSection, pk=section_id, primary_teacher=teacher)

        published_count = GradingService.publish_section_grades(section, actor=request.user)
        messages.success(request, f"Successfully published final grade snapshots for {published_count} students in '{section}'.")
        return redirect(f"{reverse('portal:teacher_gradebook')}?section={section.pk}")


class TeacherAssignmentEditView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        teacher = request.user.teacher_profile
        assignment = get_object_or_404(Assignment, pk=pk, class_section__primary_teacher=teacher)
        form = AssignmentForm(instance=assignment)
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        return render(request, 'portal/teacher/assignment_form.html', {'form': form, 'assignment': assignment, 'is_create': False})

    def post(self, request, pk):
        teacher = request.user.teacher_profile
        assignment = get_object_or_404(Assignment, pk=pk, class_section__primary_teacher=teacher)
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, f"Assignment '{assignment.title}' updated successfully.")
            return redirect('portal:teacher_assignments')
        return render(request, 'portal/teacher/assignment_form.html', {'form': form, 'assignment': assignment, 'is_create': False})


class TeacherAssignmentDeleteView(TeacherRequiredMixin, View):
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        assignment = get_object_or_404(Assignment, pk=pk, class_section__primary_teacher=teacher)
        assignment.delete()
        messages.success(request, "Assignment deleted successfully.")
        return redirect('portal:teacher_assignments')


class TeacherAssessmentCreateView(TeacherRequiredMixin, View):
    def get(self, request):
        teacher = request.user.teacher_profile
        form = AssessmentForm()
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        return render(request, 'portal/teacher/assessment_form.html', {'form': form, 'is_create': True})

    def post(self, request):
        teacher = request.user.teacher_profile
        form = AssessmentForm(request.POST)
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        if form.is_valid():
            assessment = form.save()
            messages.success(request, f"Assessment component '{assessment.title}' created successfully.")
            return redirect('portal:teacher_gradebook')
        return render(request, 'portal/teacher/assessment_form.html', {'form': form, 'is_create': True})


class TeacherAssessmentEnterMarksView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        teacher = request.user.teacher_profile
        assessment = get_object_or_404(Assessment.objects.select_related('class_section__course'), pk=pk, class_section__primary_teacher=teacher)
        roster = EnrollmentService.get_section_roster(assessment.class_section)

        # Map existing results
        existing_results = {r.student_id: r for r in assessment.results.all()}
        student_rows = []
        for enr in roster:
            result = existing_results.get(enr.student.pk)
            student_rows.append({
                'enrollment': enr,
                'result': result,
                'marks': result.marks_obtained if result else ''
            })

        return render(request, 'portal/teacher/enter_marks.html', {
            'assessment': assessment,
            'student_rows': student_rows
        })

    def post(self, request, pk):
        teacher = request.user.teacher_profile
        assessment = get_object_or_404(Assessment, pk=pk, class_section__primary_teacher=teacher)
        roster = EnrollmentService.get_section_roster(assessment.class_section)

        saved_count = 0
        for enr in roster:
            field_name = f"marks_{enr.student.pk}"
            val = request.POST.get(field_name, '').strip()
            if val != '':
                try:
                    marks = Decimal(val)
                    if 0 <= marks <= assessment.max_marks:
                        AssessmentResult.objects.update_or_create(
                            assessment=assessment,
                            student=enr.student,
                            defaults={'marks_obtained': marks, 'graded_by': teacher}
                        )
                        saved_count += 1
                except (ValueError, TypeError):
                    pass

        messages.success(request, f"Saved marks for {saved_count} students in '{assessment.title}'.")
        return redirect(f"{reverse('portal:teacher_gradebook')}?section={assessment.class_section.pk}")


class TeacherResourceListView(TeacherRequiredMixin, TemplateView):
    template_name = 'portal/teacher/resources/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course')
        course_ids = sections.values_list('course_id', flat=True).distinct()

        resources = LearningResource.objects.filter(course_id__in=course_ids).select_related('course', 'topic')
        context['resources'] = resources
        context['sections'] = sections
        return context


class TeacherResourceCreateView(TeacherRequiredMixin, View):
    def get(self, request):
        teacher = request.user.teacher_profile
        form = LearningResourceForm()
        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course')
        form.fields['course'].queryset = Course.objects.filter(id__in=sections.values_list('course_id', flat=True))
        return render(request, 'portal/teacher/resources/form.html', {'form': form, 'is_create': True})

    def post(self, request):
        teacher = request.user.teacher_profile
        form = LearningResourceForm(request.POST, request.FILES)
        sections = ClassSection.objects.filter(primary_teacher=teacher).select_related('course')
        form.fields['course'].queryset = Course.objects.filter(id__in=sections.values_list('course_id', flat=True))
        if form.is_valid():
            res = form.save(commit=False)
            res.uploaded_by = request.user
            res.save()
            messages.success(request, f"Learning resource '{res.title}' uploaded successfully.")
            return redirect('portal:teacher_resources')
        return render(request, 'portal/teacher/resources/form.html', {'form': form, 'is_create': True})


class TeacherResourceDeleteView(TeacherRequiredMixin, View):
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        res = get_object_or_404(LearningResource, pk=pk, uploaded_by=request.user)
        res.delete()
        messages.success(request, "Learning resource deleted.")
        return redirect('portal:teacher_resources')


class TeacherAnnouncementCreateView(TeacherRequiredMixin, View):
    def get(self, request):
        teacher = request.user.teacher_profile
        form = CourseAnnouncementForm()
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        return render(request, 'portal/teacher/announcement_form.html', {'form': form, 'is_create': True})

    def post(self, request):
        teacher = request.user.teacher_profile
        form = CourseAnnouncementForm(request.POST)
        form.fields['class_section'].queryset = ClassSection.objects.filter(primary_teacher=teacher)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.teacher = teacher
            ann.save()
            messages.success(request, f"Announcement '{ann.title}' posted to class section.")
            return redirect('portal:teacher_class_detail', section_id=ann.class_section.pk)
        return render(request, 'portal/teacher/announcement_form.html', {'form': form, 'is_create': True})


class TeacherAnnouncementDeleteView(TeacherRequiredMixin, View):
    def post(self, request, pk):
        teacher = request.user.teacher_profile
        ann = get_object_or_404(CourseAnnouncement, pk=pk, teacher=teacher)
        sec_id = ann.class_section.pk
        ann.delete()
        messages.success(request, "Announcement removed.")
        return redirect('portal:teacher_class_detail', section_id=sec_id)


class TeacherTimetableView(TeacherRequiredMixin, TemplateView):
    """
    7-Day weekly teaching timetable for faculty.
    """
    template_name = 'portal/teacher/timetable.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        timetable_qs = ScheduleService.get_teacher_weekly_timetable(teacher, semester=active_semester)

        days_map = {day: [] for day in range(1, 8)}
        for entry in timetable_qs:
            days_map[entry.day_of_week].append(entry)

        context['days_map'] = days_map
        context['day_choices'] = [
            (1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'),
            (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')
        ]
        context['active_semester'] = active_semester
        return context
