"""
Academic domain models for Education Management Portal.
Defines:
- Academic Periods: AcademicYear, Semester
- Curricular Hierarchy: Department -> Program <-> Course -> Topic
- Operations: ClassSection, Enrollment, ClassSchedule, ClassSession, AttendanceRecord
- Evaluation: Assignment, AssignmentSubmission, Assessment, AssessmentResult
- Materials: LearningResource, CourseAnnouncement
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import TimeStampedModel


# ============================================================================
# 1. Academic Periods & Term Models
# ============================================================================

class AcademicYear(TimeStampedModel):
    """
    Academic Year container (e.g. 2024-2025, 2025-2026).
    """
    name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('is current year'), default=False)

    class Meta:
        verbose_name = _('academic year')
        verbose_name_plural = _('academic years')
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': _('End date must be strictly after start date.')})

    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one academic year is marked as current
            AcademicYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        self.clean()
        super().save(*args, **kwargs)


class Semester(TimeStampedModel):
    """
    Academic Semester / Term (e.g. Fall 2025, Spring 2026).
    Tracks live active terms versus finalized historical terms.
    """
    class TermType(models.TextChoices):
        FALL = 'FALL', _('Fall Term')
        SPRING = 'SPRING', _('Spring Term')
        SUMMER = 'SUMMER', _('Summer Term')
        WINTER = 'WINTER', _('Winter Term')

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='semesters',
        verbose_name=_('academic year')
    )
    name = models.CharField(_('semester name'), max_length=100)
    semester_number = models.PositiveSmallIntegerField(_('term number'), default=1)
    term_type = models.CharField(
        _('term type'),
        max_length=20,
        choices=TermType.choices,
        default=TermType.FALL
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_active = models.BooleanField(
        _('is active / ongoing term'),
        default=False,
        help_text=_('Designates the currently active semester for ongoing operations.')
    )
    is_completed = models.BooleanField(
        _('is completed historical term'),
        default=False,
        help_text=_('Designates whether grades and records in this term have been finalized.')
    )

    class Meta:
        verbose_name = _('semester')
        verbose_name_plural = _('semesters')
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['academic_year', 'term_type', 'semester_number'],
                name='unique_semester_per_year_term'
            )
        ]

    def __str__(self):
        status = " (Active)" if self.is_active else (" (Completed)" if self.is_completed else "")
        return f"{self.name} - {self.academic_year.name}{status}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': _('End date must be after start date.')})

    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one semester is marked as active across the institution
            Semester.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        self.clean()
        super().save(*args, **kwargs)


# ============================================================================
# 2. Departments & Degree Programs
# ============================================================================

class Department(TimeStampedModel):
    """
    Academic Department (e.g. Computer Science, Electrical Engineering).
    """
    code = models.CharField(_('code'), max_length=20, unique=True, db_index=True)
    name = models.CharField(_('name'), max_length=150)
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('active status'), default=True)

    class Meta:
        verbose_name = _('department')
        verbose_name_plural = _('departments')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Program(TimeStampedModel):
    """
    Academic Program / Degree (e.g., B.Tech Computer Science).
    Belongs strictly to a Department.
    """
    class DegreeLevel(models.TextChoices):
        BACHELOR = 'BACHELOR', _('Bachelor Degree')
        MASTER = 'MASTER', _('Master Degree')
        DOCTORATE = 'DOCTORATE', _('Doctorate / PhD')
        DIPLOMA = 'DIPLOMA', _('Diploma / Certificate')

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='programs',
        verbose_name=_('department')
    )
    code = models.CharField(_('code'), max_length=20, unique=True, db_index=True)
    name = models.CharField(_('name'), max_length=150)
    degree_level = models.CharField(
        _('degree level'),
        max_length=20,
        choices=DegreeLevel.choices,
        default=DegreeLevel.BACHELOR
    )
    duration_years = models.PositiveSmallIntegerField(_('duration in years'), default=4)
    total_semesters = models.PositiveSmallIntegerField(_('total semesters'), default=8)
    is_active = models.BooleanField(_('active status'), default=True)

    class Meta:
        verbose_name = _('program')
        verbose_name_plural = _('programs')
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_degree_level_display()} ({self.code})"


# ============================================================================
# 3. User Academic Profiles
# ============================================================================

class StudentProfile(TimeStampedModel):
    """
    Academic profile for users with STUDENT role.
    Explicitly references Program and Department, with consistency validation.
    """
    class AcademicStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        ON_LEAVE = 'ON_LEAVE', _('On Leave')
        PROBATION = 'PROBATION', _('Academic Probation')
        GRADUATED = 'GRADUATED', _('Graduated')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('user')
    )
    student_id = models.CharField(
        _('student ID / roll number'),
        max_length=50,
        unique=True,
        db_index=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='students',
        verbose_name=_('department')
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name='students',
        verbose_name=_('academic program')
    )
    current_semester = models.PositiveSmallIntegerField(_('current semester'), default=1)
    academic_year = models.PositiveSmallIntegerField(_('academic year'), default=2026)
    academic_status = models.CharField(
        _('academic status'),
        max_length=20,
        choices=AcademicStatus.choices,
        default=AcademicStatus.ACTIVE
    )
    enrollment_date = models.DateField(_('enrollment date'), default=timezone.now)

    class Meta:
        verbose_name = _('student profile')
        verbose_name_plural = _('student profiles')
        ordering = ['student_id']

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name() or self.user.email}"

    def clean(self):
        super().clean()
        if self.program_id and not self.department_id:
            self.department = self.program.department
        elif self.program_id and self.department_id:
            if self.program.department_id != self.department_id:
                raise ValidationError({
                    'program': _(
                        f"The selected program '{self.program.name}' does not belong to "
                        f"department '{self.department.name}'."
                    )
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class TeacherProfile(TimeStampedModel):
    """
    Academic profile for users with TEACHER role.
    References Department.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('user')
    )
    employee_id = models.CharField(
        _('employee ID'),
        max_length=50,
        unique=True,
        db_index=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='teachers',
        verbose_name=_('department')
    )
    designation = models.CharField(_('designation'), max_length=100, default='Assistant Professor')
    qualification = models.CharField(_('qualification'), max_length=200, blank=True)
    office_location = models.CharField(_('office location'), max_length=100, blank=True)
    joining_date = models.DateField(_('joining date'), default=timezone.now)

    class Meta:
        verbose_name = _('teacher profile')
        verbose_name_plural = _('teacher profiles')
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.designation} {self.user.get_full_name() or self.user.email}"


# ============================================================================
# 4. Courses & Granular Topics
# ============================================================================

class Course(TimeStampedModel):
    """
    Canonical curricular unit of instruction.
    Owned by a Department, with Many-to-Many inclusion in multiple Degree Programs.
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='courses',
        verbose_name=_('administering department')
    )
    programs = models.ManyToManyField(
        Program,
        related_name='courses',
        blank=True,
        verbose_name=_('curriculum programs'),
        help_text=_('Degree programs where this course is offered in the syllabus.')
    )
    code = models.CharField(_('course code'), max_length=20, unique=True, db_index=True)
    title = models.CharField(_('course title'), max_length=200)
    description = models.TextField(_('course description'), blank=True)
    credits = models.PositiveSmallIntegerField(_('academic credits'), default=4)
    is_active = models.BooleanField(_('is active course'), default=True)

    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.title}"

    def is_eligible_for_program(self, program):
        """Check if this course is part of the given program's curriculum."""
        if not program:
            return False
        return self.programs.filter(pk=program.pk).exists()


class Topic(TimeStampedModel):
    """
    Topic / Module within a Course syllabus.
    Enables topic-level diagnostics, weak-area detection, and study planning.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='topics',
        verbose_name=_('course')
    )
    title = models.CharField(_('topic title'), max_length=200)
    description = models.TextField(_('topic description'), blank=True)
    order_index = models.PositiveSmallIntegerField(_('syllabus sequence order'), default=1)
    learning_objectives = models.TextField(_('learning objectives / competencies'), blank=True)

    class Meta:
        verbose_name = _('topic')
        verbose_name_plural = _('topics')
        ordering = ['course', 'order_index']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'order_index'],
                name='unique_topic_order_per_course'
            )
        ]

    def __str__(self):
        return f"{self.course.code} - Topic {self.order_index}: {self.title}"


# ============================================================================
# 5. Course Offerings (Class Sections) & Student Enrollment
# ============================================================================

class ClassSection(TimeStampedModel):
    """
    Specific offering of a Course in an Academic Semester.
    Tied to a primary teacher, section code, schedule, and room.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='sections',
        verbose_name=_('course')
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.PROTECT,
        related_name='class_sections',
        verbose_name=_('academic semester')
    )
    section_code = models.CharField(
        _('section / batch code'),
        max_length=20,
        default='A',
        help_text=_('e.g. A, B, Section-1, Morning Batch')
    )
    primary_teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='assigned_sections',
        verbose_name=_('primary instructor')
    )
    capacity = models.PositiveIntegerField(_('student capacity'), default=60)
    room_number = models.CharField(_('default room / laboratory'), max_length=100, blank=True)
    is_active = models.BooleanField(_('is active section'), default=True)

    class Meta:
        verbose_name = _('class section')
        verbose_name_plural = _('class sections')
        ordering = ['-semester__start_date', 'course__code', 'section_code']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'semester', 'section_code'],
                name='unique_section_per_course_semester'
            )
        ]

    def __str__(self):
        return f"{self.course.code} - Sec {self.section_code} ({self.semester.name})"

    @property
    def enrolled_count(self):
        """Current number of active enrolled students."""
        return self.enrollments.filter(status=Enrollment.EnrollmentStatus.ENROLLED).count()

    @property
    def is_full(self):
        """Check if class section is at or above capacity."""
        return self.enrolled_count >= self.capacity


class Enrollment(TimeStampedModel):
    """
    Student registration in a ClassSection.
    Stores cached/published final grade snapshots calculated solely by GradingService.
    """
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', _('Active Enrollment')
        COMPLETED = 'COMPLETED', _('Completed Term')
        DROPPED = 'DROPPED', _('Dropped Course')
        AUDIT = 'AUDIT', _('Auditing')

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('student')
    )
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name=_('class section')
    )
    enrollment_date = models.DateField(_('enrollment date'), default=timezone.now)
    status = models.CharField(
        _('enrollment status'),
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED
    )
    # Read-only published snapshots generated via GradingService
    final_percentage = models.DecimalField(
        _('final percentage snapshot'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Published final percentage snapshot calculated by GradingService.')
    )
    final_grade_letter = models.CharField(
        _('final grade letter snapshot'),
        max_length=5,
        null=True,
        blank=True,
        help_text=_('Published grade letter (e.g. A+, A, B, C, F) generated by GradingService.')
    )
    is_grade_published = models.BooleanField(_('is grade published to student'), default=False)
    published_at = models.DateTimeField(_('published timestamp'), null=True, blank=True)

    class Meta:
        verbose_name = _('enrollment')
        verbose_name_plural = _('enrollments')
        ordering = ['-class_section__semester__start_date', 'student__student_id']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'class_section'],
                name='unique_student_section_enrollment'
            )
        ]

    def __str__(self):
        return f"{self.student.student_id} in {self.class_section}"


# ============================================================================
# 6. 7-Day Timetable & Scheduling
# ============================================================================

class ClassSchedule(TimeStampedModel):
    """
    Weekly timetable slot for a ClassSection.
    Supports all 7 days of the week (1=Monday to 7=Sunday).
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, _('Monday')
        TUESDAY = 2, _('Tuesday')
        WEDNESDAY = 3, _('Wednesday')
        THURSDAY = 4, _('Thursday')
        FRIDAY = 5, _('Friday')
        SATURDAY = 6, _('Saturday')
        SUNDAY = 7, _('Sunday')

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('class section')
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='schedules',
        verbose_name=_('instructor for slot')
    )
    day_of_week = models.PositiveSmallIntegerField(
        _('day of week'),
        choices=DayOfWeek.choices,
        default=DayOfWeek.MONDAY
    )
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    room = models.CharField(_('classroom / lab'), max_length=100)

    class Meta:
        verbose_name = _('class schedule slot')
        verbose_name_plural = _('class schedule slots')
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.class_section} - {self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': _('End time must be strictly after start time.')})


# ============================================================================
# 7. Session-Based Attendance Models
# ============================================================================

class ClassSession(TimeStampedModel):
    """
    Individual lecture / lab session conducted for a ClassSection.
    Serves as the parent container for granular AttendanceRecords.
    """
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('class section')
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='conducted_sessions',
        verbose_name=_('conducting instructor')
    )
    session_date = models.DateField(_('session date'), default=timezone.now)
    start_time = models.TimeField(_('start time'), null=True, blank=True)
    end_time = models.TimeField(_('end time'), null=True, blank=True)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        verbose_name=_('covered topic')
    )
    title = models.CharField(_('session topic / title'), max_length=200, default='Lecture Session')
    session_notes = models.TextField(_('faculty lecture notes / remarks'), blank=True)
    is_completed = models.BooleanField(_('attendance finalized'), default=True)

    class Meta:
        verbose_name = _('class session')
        verbose_name_plural = _('class sessions')
        ordering = ['-session_date', '-created_at']

    def __str__(self):
        return f"{self.class_section} - {self.session_date.strftime('%Y-%m-%d')} ({self.title})"


class AttendanceRecord(TimeStampedModel):
    """
    Granular session attendance record for a single student.
    Authoritative source for dynamic attendance percentage calculation.
    """
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Late (Tardy)')
        EXCUSED = 'EXCUSED', _('Excused Absence')

    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name=_('class session')
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='attendance_records',
        verbose_name=_('student')
    )
    status = models.CharField(
        _('attendance status'),
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT
    )
    remarks = models.CharField(_('remarks / excuse details'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('attendance record')
        verbose_name_plural = _('attendance records')
        ordering = ['session__session_date', 'student__student_id']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                name='unique_session_student_attendance'
            )
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.session.session_date} ({self.get_status_display()})"


# ============================================================================
# 8. Formative Assignments & Submissions
# ============================================================================

class Assignment(TimeStampedModel):
    """
    Formative coursework activity assigned to a ClassSection.
    """
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('class section')
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='created_assignments',
        verbose_name=_('assigning instructor')
    )
    title = models.CharField(_('assignment title'), max_length=200)
    description = models.TextField(_('problem statement / instructions'))
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments',
        verbose_name=_('syllabus topic')
    )
    issue_date = models.DateTimeField(_('issue date / visible from'), default=timezone.now)
    due_date = models.DateTimeField(_('submission deadline'))
    max_marks = models.DecimalField(
        _('maximum marks'),
        max_digits=6,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    attachment = models.FileField(
        _('reference worksheet / problem file'),
        upload_to='assignments/sheets/',
        blank=True,
        null=True
    )
    allow_late_submission = models.BooleanField(_('allow late submissions'), default=True)
    is_published = models.BooleanField(_('is published to students'), default=True)

    class Meta:
        verbose_name = _('assignment')
        verbose_name_plural = _('assignments')
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.class_section.course.code} - {self.title} (Due: {self.due_date.strftime('%b %d')})"

    def clean(self):
        super().clean()
        if self.issue_date and self.due_date and self.issue_date >= self.due_date:
            raise ValidationError({'due_date': _('Deadline must be strictly after the issue date.')})


class AssignmentSubmission(TimeStampedModel):
    """
    Individual student submission for an Assignment.
    """
    class SubmissionStatus(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Submitted On-Time')
        LATE = 'LATE', _('Submitted Late')
        GRADED = 'GRADED', _('Evaluated / Graded')
        RESUBMITTED = 'RESUBMITTED', _('Resubmitted')

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_('assignment')
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='assignment_submissions',
        verbose_name=_('student')
    )
    submission_date = models.DateTimeField(_('submission timestamp'), default=timezone.now)
    submission_text = models.TextField(_('text solution / code answer'), blank=True)
    attachment = models.FileField(
        _('solution attachment'),
        upload_to='assignments/submissions/',
        blank=True,
        null=True
    )
    status = models.CharField(
        _('submission status'),
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED
    )
    obtained_marks = models.DecimalField(
        _('obtained marks'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    feedback = models.TextField(_('instructor feedback & critique'), blank=True)
    graded_by = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        verbose_name=_('evaluating instructor')
    )
    graded_at = models.DateTimeField(_('graded timestamp'), null=True, blank=True)

    class Meta:
        verbose_name = _('assignment submission')
        verbose_name_plural = _('assignment submissions')
        ordering = ['-submission_date']
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'],
                name='unique_assignment_student_submission'
            )
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.assignment.title} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.obtained_marks is not None:
            if self.obtained_marks > self.assignment.max_marks:
                raise ValidationError({
                    'obtained_marks': _(f'Obtained marks ({self.obtained_marks}) cannot exceed max marks ({self.assignment.max_marks}).')
                })


# ============================================================================
# 9. Evaluative Assessments & Exam Results
# ============================================================================

class Assessment(TimeStampedModel):
    """
    Evaluative component contributing to the final course grade.
    The sum of assessment weightages within a ClassSection constitutes 100%.
    """
    class AssessmentType(models.TextChoices):
        QUIZ = 'QUIZ', _('Quiz / Short Test')
        ASSIGNMENTS = 'ASSIGNMENTS', _('Assignments Aggregate')
        MIDTERM = 'MIDTERM', _('Midterm Examination')
        FINAL = 'FINAL', _('End-Semester Final Examination')
        PRACTICAL = 'PRACTICAL', _('Laboratory / Practical Exam')
        PROJECT = 'PROJECT', _('Capstone / Term Project')

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name=_('class section')
    )
    title = models.CharField(_('assessment title'), max_length=200)
    assessment_type = models.CharField(
        _('assessment type'),
        max_length=20,
        choices=AssessmentType.choices,
        default=AssessmentType.MIDTERM
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessments',
        verbose_name=_('primary topic focus')
    )
    date = models.DateField(_('examination / due date'), default=timezone.now)
    max_marks = models.DecimalField(
        _('maximum marks'),
        max_digits=6,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    weightage_percentage = models.DecimalField(
        _('weightage percentage (0-100)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('25.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    is_published = models.BooleanField(_('is published to gradebook'), default=True)

    class Meta:
        verbose_name = _('assessment')
        verbose_name_plural = _('assessments')
        ordering = ['date', 'created_at']

    def __str__(self):
        return f"{self.class_section.course.code} - {self.title} ({self.get_assessment_type_display()} - {self.weightage_percentage}%)"


class AssessmentResult(TimeStampedModel):
    """
    Individual student score for an Assessment.
    Authoritative building block for weighted course grading.
    """
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('assessment')
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='assessment_results',
        verbose_name=_('student')
    )
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    remarks = models.CharField(_('evaluator remarks'), max_length=255, blank=True)
    graded_by = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_assessment_results',
        verbose_name=_('evaluating instructor')
    )

    class Meta:
        verbose_name = _('assessment result')
        verbose_name_plural = _('assessment results')
        ordering = ['assessment__date', 'student__student_id']
        constraints = [
            models.UniqueConstraint(
                fields=['assessment', 'student'],
                name='unique_assessment_student_result'
            )
        ]

    def __str__(self):
        return f"{self.student.student_id} - {self.assessment.title}: {self.marks_obtained}/{self.assessment.max_marks}"

    def clean(self):
        super().clean()
        if self.marks_obtained is not None:
            if self.marks_obtained > self.assessment.max_marks:
                raise ValidationError({
                    'marks_obtained': _(f'Marks obtained ({self.marks_obtained}) cannot exceed maximum marks ({self.assessment.max_marks}).')
                })

    @property
    def percentage(self):
        """Calculate the percentage score obtained."""
        if not self.assessment.max_marks or self.assessment.max_marks == 0:
            return Decimal('0.00')
        return (self.marks_obtained / self.assessment.max_marks) * Decimal('100.00')


# ============================================================================
# 10. Learning Resources & Course Announcements
# ============================================================================

class LearningResource(TimeStampedModel):
    """
    Educational material (slides, lecture notes, video links, question banks).
    """
    class ResourceType(models.TextChoices):
        PDF = 'PDF', _('PDF Document / Slides')
        VIDEO = 'VIDEO', _('Video Lecture Link')
        PRESENTATION = 'PRESENTATION', _('Presentation (PPT/Keynote)')
        LINK = 'LINK', _('External Web Link / Reference')
        NOTES = 'NOTES', _('Lecture Notes / Cheatsheet')
        QUESTION_BANK = 'QUESTION_BANK', _('Practice Problem Bank')

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='resources',
        verbose_name=_('course')
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources',
        verbose_name=_('syllabus topic')
    )
    title = models.CharField(_('resource title'), max_length=200)
    description = models.TextField(_('resource description'), blank=True)
    resource_type = models.CharField(
        _('resource type'),
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.PDF
    )
    file = models.FileField(
        _('resource file upload'),
        upload_to='resources/docs/',
        blank=True,
        null=True
    )
    external_url = models.URLField(_('external URL / video link'), blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_resources',
        verbose_name=_('uploader')
    )
    is_published = models.BooleanField(_('is published to students'), default=True)

    class Meta:
        verbose_name = _('learning resource')
        verbose_name_plural = _('learning resources')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.code} - {self.title} ({self.get_resource_type_display()})"


class CourseAnnouncement(TimeStampedModel):
    """
    Broadcast notification / bulletin for a ClassSection.
    """
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name=_('class section')
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='posted_announcements',
        verbose_name=_('posting instructor')
    )
    title = models.CharField(_('announcement title'), max_length=200)
    content = models.TextField(_('announcement content / notice'))
    is_pinned = models.BooleanField(_('pin to top of feed'), default=False)

    class Meta:
        verbose_name = _('course announcement')
        verbose_name_plural = _('course announcements')
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"[{self.class_section.course.code}] {self.title}"
