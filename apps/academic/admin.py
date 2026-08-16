"""
Django built-in administration configuration for Academic models.
Provides inlines, search, list filters, ordering, autocomplete, and snapshot protection.
"""

from django.contrib import admin
from .models import (
    AcademicYear,
    Semester,
    Department,
    Program,
    StudentProfile,
    TeacherProfile,
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


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1
    fields = ('order_index', 'title', 'description', 'learning_objectives')
    ordering = ('order_index',)


class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1
    fields = ('day_of_week', 'start_time', 'end_time', 'room', 'teacher')


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ('student', 'status', 'remarks')
    readonly_fields = ('student',)


class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    fields = ('student', 'status', 'submission_date', 'obtained_marks', 'graded_by')
    readonly_fields = ('student', 'submission_date')


class AssessmentResultInline(admin.TabularInline):
    model = AssessmentResult
    extra = 0
    fields = ('student', 'marks_obtained', 'remarks', 'graded_by')
    readonly_fields = ('student',)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current', 'created_at')
    list_filter = ('is_current',)
    search_fields = ('name',)
    ordering = ('-start_date',)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'term_type', 'semester_number', 'start_date', 'end_date', 'is_active', 'is_completed')
    list_filter = ('academic_year', 'term_type', 'is_active', 'is_completed')
    search_fields = ('name', 'academic_year__name')
    ordering = ('-start_date',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    ordering = ('name',)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'degree_level', 'duration_years', 'total_semesters', 'is_active')
    list_filter = ('degree_level', 'department', 'is_active')
    search_fields = ('code', 'name', 'department__name')
    ordering = ('department', 'name')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'department', 'program', 'current_semester', 'academic_status')
    list_filter = ('academic_status', 'department', 'program', 'current_semester')
    search_fields = ('student_id', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('student_id',)
    raw_id_fields = ('user',)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'designation', 'office_location')
    list_filter = ('department', 'designation')
    search_fields = ('employee_id', 'user__email', 'user__first_name', 'user__last_name', 'qualification')
    ordering = ('employee_id',)
    raw_id_fields = ('user',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'department', 'credits', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('code', 'title', 'description')
    filter_horizontal = ('programs',)
    inlines = [TopicInline]
    ordering = ('code',)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('course', 'order_index', 'title')
    list_filter = ('course__department', 'course')
    search_fields = ('title', 'course__code', 'description')
    ordering = ('course', 'order_index')


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ('course', 'section_code', 'semester', 'primary_teacher', 'capacity', 'room_number', 'is_active')
    list_filter = ('semester', 'course__department', 'is_active')
    search_fields = ('course__code', 'course__title', 'section_code', 'primary_teacher__user__first_name')
    inlines = [ClassScheduleInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_section', 'status', 'final_percentage', 'final_grade_letter', 'is_grade_published')
    list_filter = ('status', 'class_section__semester', 'is_grade_published')
    search_fields = ('student__student_id', 'student__user__email', 'class_section__course__code')
    readonly_fields = ('final_percentage', 'final_grade_letter', 'published_at')


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_section', 'day_of_week', 'start_time', 'end_time', 'room', 'teacher')
    list_filter = ('day_of_week', 'class_section__semester')
    search_fields = ('class_section__course__code', 'room', 'teacher__user__email')


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('class_section', 'session_date', 'title', 'teacher', 'is_completed')
    list_filter = ('session_date', 'class_section__semester')
    search_fields = ('title', 'class_section__course__code')
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('session', 'student', 'status', 'remarks')
    list_filter = ('status', 'session__session_date')
    search_fields = ('student__student_id', 'student__user__email', 'session__class_section__course__code')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_section', 'max_marks', 'due_date', 'allow_late_submission', 'is_published')
    list_filter = ('class_section__semester', 'is_published')
    search_fields = ('title', 'class_section__course__code')
    inlines = [AssignmentSubmissionInline]


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submission_date', 'status', 'obtained_marks', 'graded_by')
    list_filter = ('status', 'assignment__class_section__semester')
    search_fields = ('student__student_id', 'assignment__title')
    readonly_fields = ('submission_date', 'graded_at')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_section', 'assessment_type', 'max_marks', 'weightage_percentage', 'date', 'is_published')
    list_filter = ('assessment_type', 'class_section__semester', 'is_published')
    search_fields = ('title', 'class_section__course__code')
    inlines = [AssessmentResultInline]


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'student', 'marks_obtained', 'graded_by')
    list_filter = ('assessment__class_section__semester', 'assessment__assessment_type')
    search_fields = ('student__student_id', 'assessment__title')


@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'resource_type', 'is_published', 'created_at')
    list_filter = ('resource_type', 'course__department', 'is_published')
    search_fields = ('title', 'course__code')


@admin.register(CourseAnnouncement)
class CourseAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_section', 'teacher', 'is_pinned', 'created_at')
    list_filter = ('is_pinned', 'class_section__semester')
    search_fields = ('title', 'content')
