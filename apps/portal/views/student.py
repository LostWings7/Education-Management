"""
Student portal views for Phase 2 Academic Management.
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import StudentRequiredMixin
from apps.academic.models import (
    StudentProfile,
    ClassSection,
    Enrollment,
    Assignment,
    AssignmentSubmission,
    Semester,
    Course
)
from apps.academic.services import (
    EnrollmentService,
    AttendanceService,
    AssignmentService,
    GradingService,
    ScheduleService,
    ResourceService
)
from apps.portal.reporting import TranscriptService
from apps.analytics.services import (
    RiskEngineService,
    AttendanceAnalyticsService,
    AssignmentAnalyticsService,
    PerformanceAnalyticsService,
    TrendAnalyticsService,
    StudentActionPriorityService,
    LongitudinalJourneyService,
    AcademicMomentsService
)
from apps.interventions.models import Intervention


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """
    Academic Command Center:
      1. How am I doing? (Academic Health Scorecard & Overall Status)
      2. What needs my attention? (Categorized Critical / Important / Positive)
      3. What should I do next? (Deterministic Prioritized Action Queue)
    """
    template_name = 'portal/student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = StudentProfile.objects.select_related('department', 'program').get(user=user)
        except StudentProfile.DoesNotExist:
            profile = None

        context['student_profile'] = profile
        context['page_title'] = 'Academic Command Center'

        if profile:
            active_semester = Semester.objects.filter(is_active=True).first()
            context['active_semester'] = active_semester

            # 1. Authoritative Transcripts & CGPA
            transcript = TranscriptService.get_student_transcript(profile)
            context['transcript'] = transcript
            context['cumulative_gpa'] = transcript.get('cumulative_gpa', 0.0)
            context['academic_standing'] = transcript.get('academic_standing', 'Good Standing')
            context['total_credits_earned'] = transcript.get('total_credits_earned', 0.0)

            # 2. Overall Multi-Dimensional Risk
            overall_risk = RiskEngineService.evaluate_overall_risk(profile, semester=active_semester)
            context['overall_risk'] = overall_risk

            # 3. Overall Attendance & Trend Analytics
            att_summary = AttendanceAnalyticsService.calculate_overall_attendance(profile, semester=active_semester)
            context['attendance_summary'] = att_summary

            overall_trend = TrendAnalyticsService.calculate_overall_trajectory(profile, semester=active_semester)
            context['overall_trend'] = overall_trend

            # 4. Overall Coursework Analytics
            assign_summary = AssignmentAnalyticsService.calculate_overall_assignments(profile, semester=active_semester)
            context['assignment_summary'] = assign_summary

            # 5. Active Enrollments
            enrollments = EnrollmentService.get_student_enrollments(profile, semester=active_semester)
            context['enrollments'] = enrollments

            # 6. Prioritized Student Actions (What should I do next?)
            prioritized_actions = StudentActionPriorityService.get_prioritized_actions(profile, semester=active_semester)
            context['prioritized_actions'] = prioritized_actions

            # 7. Positive Academic Moments
            moments = AcademicMomentsService.get_student_moments(profile, semester=active_semester)
            context['academic_moments'] = moments

            # 8. Attention Panels Partitioning
            critical_items = [a for a in prioritized_actions if a['priority_level'] == 'URGENT' or a['risk_subscore'] >= 75.0]
            important_items = [a for a in prioritized_actions if a['priority_level'] in ['HIGH', 'RECOMMENDED'] and a not in critical_items]

            context['critical_items'] = critical_items
            context['important_items'] = important_items
            context['positive_items'] = moments

            # 9. Academic Health Scorecard
            context['health_scorecard'] = {
                'performance_score': transcript.get('term_average', 80.0),
                'performance_status': 'EXCELLENT' if (transcript.get('cumulative_gpa') or 0.0) >= 3.7 else ('GOOD' if (transcript.get('cumulative_gpa') or 0.0) >= 3.0 else 'WARNING'),
                'attendance_score': att_summary.attendance_percentage if att_summary else 100.0,
                'attendance_status': 'DANGER' if (att_summary and att_summary.attendance_percentage < 60.0) else ('WARNING' if (att_summary and att_summary.attendance_percentage < 75.0) else 'GOOD'),
                'coursework_score': assign_summary.completion_rate if assign_summary else 100.0,
                'coursework_status': 'GOOD' if (assign_summary and assign_summary.completion_rate >= 80.0) else 'WARNING',
                'trajectory_direction': str(overall_trend.direction) if overall_trend else 'STABLE',
                'risk_level': str(overall_risk.risk_level) if overall_risk else 'LOW',
                'composite_score': overall_risk.composite_score if overall_risk else 0.0
            }

            # 10. Today's Timetable
            import datetime
            today_day = datetime.datetime.today().isoweekday()
            timetable = ScheduleService.get_student_weekly_timetable(profile, semester=active_semester)
            context['today_schedule'] = timetable.filter(day_of_week=today_day)

        return context


class StudentJourneyView(StudentRequiredMixin, TemplateView):
    """
    Longitudinal Academic Journey: Where you started -> Where you are -> Where you are headed.
    """
    template_name = 'portal/student/journey.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        context['journey'] = LongitudinalJourneyService.get_student_journey(student)
        return context


class StudentCoursesView(StudentRequiredMixin, TemplateView):
    """
    View enrolled courses (active term and historical completed terms).
    """
    template_name = 'portal/student/courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        active_semester = Semester.objects.filter(is_active=True).first()
        active_enrollments = EnrollmentService.get_student_enrollments(student, semester=active_semester)
        all_enrollments = EnrollmentService.get_student_enrollments(student)

        # Separate into active and historical
        context['active_enrollments'] = active_enrollments
        context['historical_enrollments'] = all_enrollments.filter(class_section__semester__is_completed=True)
        context['active_semester'] = active_semester
        return context


class StudentCourseDetailView(StudentRequiredMixin, TemplateView):
    """
    Detailed course view for an enrolled student (Syllabus, Topics, Announcements, Resources).
    """
    template_name = 'portal/student/course_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        section_id = self.kwargs.get('section_id')

        enrollment = get_object_or_404(
            Enrollment.objects.select_related(
                'class_section__course__department',
                'class_section__semester',
                'class_section__primary_teacher__user'
            ),
            student=student,
            class_section_id=section_id
        )

        section = enrollment.class_section
        course = section.course

        context['enrollment'] = enrollment
        context['class_section'] = section
        context['course'] = course
        context['topics'] = course.topics.all()
        context['announcements'] = ResourceService.get_section_announcements(section)
        context['resources'] = ResourceService.get_course_resources(course)
        context['attendance_metrics'] = AttendanceService.calculate_student_attendance(student, class_section=section)
        context['grade_breakdown'] = GradingService.calculate_student_course_grade(student, section)
        return context


class StudentAttendanceView(StudentRequiredMixin, TemplateView):
    """
    Comprehensive attendance records and breakdown across all enrolled courses.
    """
    template_name = 'portal/student/attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        selected_semester_id = self.request.GET.get('semester')
        if selected_semester_id:
            semester = Semester.objects.filter(pk=selected_semester_id).first()
        else:
            semester = Semester.objects.filter(is_active=True).first()

        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['selected_semester'] = semester
        context['course_matrix'] = AttendanceService.get_student_course_attendance_matrix(student, semester=semester)
        context['overall_summary'] = AttendanceService.calculate_student_attendance(student, semester=semester)
        return context


class StudentAssignmentsView(StudentRequiredMixin, TemplateView):
    """
    List assignments across all enrolled courses with status, due dates, and marks.
    """
    template_name = 'portal/student/assignments.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        active_semester = Semester.objects.filter(is_active=True).first()
        context['assignments'] = AssignmentService.get_student_assignments_overview(student, semester=active_semester)
        context['active_semester'] = active_semester
        return context


class StudentAssignmentSubmitView(StudentRequiredMixin, View):
    """
    Handle assignment submission form and file upload.
    """
    def post(self, request, assignment_id):
        student = request.user.student_profile
        assignment = get_object_or_404(Assignment, pk=assignment_id)

        submission_text = request.POST.get('submission_text', '')
        attachment = request.FILES.get('attachment')

        try:
            submission = AssignmentService.submit_assignment(
                assignment=assignment,
                student=student,
                submission_text=submission_text,
                attachment=attachment,
                actor=request.user
            )
            messages.success(request, f"Assignment '{assignment.title}' submitted successfully ({submission.get_status_display()}).")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('portal:student_assignments')


class StudentGradesView(StudentRequiredMixin, TemplateView):
    """
    Comprehensive grade report showing continuous assessment marks and published course grades.
    """
    template_name = 'portal/student/grades.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        selected_semester_id = self.request.GET.get('semester')
        if selected_semester_id:
            semester = Semester.objects.filter(pk=selected_semester_id).first()
        else:
            semester = Semester.objects.filter(is_active=True).first()

        context['semesters'] = Semester.objects.all().order_by('-start_date')
        context['selected_semester'] = semester

        enrollments = EnrollmentService.get_student_enrollments(student, semester=semester)

        course_grades = []
        total_grade_points = Decimal('0.00')
        total_credits = 0

        for enrollment in enrollments:
            calc = GradingService.calculate_student_course_grade(student, enrollment.class_section)
            credits = enrollment.class_section.course.credits
            course_grades.append({
                'enrollment': enrollment,
                'class_section': enrollment.class_section,
                'course': enrollment.class_section.course,
                'calc': calc,
                'credits': credits,
            })
            total_grade_points += (calc['grade_points'] * Decimal(str(credits)))
            total_credits += credits

        term_gpa = round(total_grade_points / Decimal(str(total_credits)), 2) if total_credits > 0 else Decimal('0.00')

        context['course_grades'] = course_grades
        context['term_gpa'] = term_gpa
        context['total_credits'] = total_credits
        return context


class StudentTimetableView(StudentRequiredMixin, TemplateView):
    """
    7-Day weekly class schedule grid for enrolled courses.
    """
    template_name = 'portal/student/timetable.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        timetable_qs = ScheduleService.get_student_weekly_timetable(student, semester=active_semester)

        # Group by day 1..7
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


class StudentResourcesView(StudentRequiredMixin, TemplateView):
    """
    Browse and download educational materials for enrolled courses.
    """
    template_name = 'portal/student/resources.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        active_semester = Semester.objects.filter(is_active=True).first()

        enrollments = EnrollmentService.get_student_enrollments(student, semester=active_semester)
        course_ids = enrollments.values_list('class_section__course_id', flat=True)

        courses = Course.objects.filter(id__in=course_ids)
        selected_course_id = self.request.GET.get('course')

        if selected_course_id:
            selected_course = courses.filter(pk=selected_course_id).first()
        else:
            selected_course = courses.first()

        resources = []
        if selected_course:
            resources = ResourceService.get_course_resources(selected_course)

        context['courses'] = courses
        context['selected_course'] = selected_course
        context['resources'] = resources
        return context


class StudentTimelineView(StudentRequiredMixin, TemplateView):
    """
    Chronological student academic journey view.
    """
    template_name = 'portal/student/timeline.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        from apps.portal.services.timeline_service import AcademicTimelineService
        context['student'] = student
        context['timeline_events'] = AcademicTimelineService.get_student_timeline(student)
        return context
