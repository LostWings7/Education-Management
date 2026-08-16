"""
Academic domain forms for administrative and faculty management.
"""

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import User, Role
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
    ClassSchedule,
    Assignment,
    Assessment,
    LearningResource,
    CourseAnnouncement
)


# ============================================================================
# 1. Department & Program Forms
# ============================================================================

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. CSE'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Computer Science and Engineering'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Department overview...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['department', 'code', 'name', 'degree_level', 'duration_years', 'total_semesters', 'is_active']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BT-CSE'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. B.Tech Computer Science'}),
            'degree_level': forms.Select(attrs={'class': 'form-select'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 6}),
            'total_semesters': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 12}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


# ============================================================================
# 2. Academic Period Forms
# ============================================================================

class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 2026-2027'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ['academic_year', 'name', 'semester_number', 'term_type', 'start_date', 'end_date', 'is_active', 'is_completed']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Fall 2026'}),
            'semester_number': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 12}),
            'term_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


# ============================================================================
# 3. Student & Teacher Management Forms
# ============================================================================

class StudentCreateForm(forms.Form):
    """Form to create User account and StudentProfile concurrently."""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'student@example.com'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Initial Password'}))
    phone_number = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+1-555-0100'}))

    student_id = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. STU-2026-101'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    program = forms.ModelChoiceField(queryset=Program.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    current_semester = forms.IntegerField(initial=1, min_value=1, max_value=12, widget=forms.NumberInput(attrs={'class': 'form-input'}))
    academic_year = forms.IntegerField(initial=2026, min_value=2020, max_value=2040, widget=forms.NumberInput(attrs={'class': 'form-input'}))
    academic_status = forms.ChoiceField(choices=StudentProfile.AcademicStatus.choices, initial=StudentProfile.AcademicStatus.ACTIVE, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id').strip()
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise ValidationError(_('A student with this Student ID / Roll Number already exists.'))
        return student_id

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        program = cleaned_data.get('program')
        if department and program:
            if program.department_id != department.pk:
                raise ValidationError({'program': _(f"Program '{program.name}' does not belong to department '{department.name}'.")})
        return cleaned_data


class StudentEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone_number = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'form-input'}))
    is_active_user = forms.BooleanField(required=False, label='User Account Active', widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))

    class Meta:
        model = StudentProfile
        fields = ['department', 'program', 'current_semester', 'academic_year', 'academic_status']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'current_semester': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 12}),
            'academic_year': forms.NumberInput(attrs={'class': 'form-input'}),
            'academic_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['is_active_user'].initial = self.instance.user.is_active

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        program = cleaned_data.get('program')
        if department and program:
            if program.department_id != department.pk:
                raise ValidationError({'program': _(f"Program '{program.name}' does not belong to department '{department.name}'.")})
        return cleaned_data


class TeacherCreateForm(forms.Form):
    """Form to create User account and TeacherProfile concurrently."""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'teacher@example.com'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Initial Password'}))
    phone_number = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+1-555-0100'}))

    employee_id = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. FAC-1005'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    designation = forms.CharField(initial='Assistant Professor', max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))
    qualification = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Ph.D. in Computer Science'}))
    office_location = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Room 304, Academic Block'}))

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id').strip()
        if TeacherProfile.objects.filter(employee_id=employee_id).exists():
            raise ValidationError(_('A teacher with this Employee ID already exists.'))
        return employee_id


class TeacherEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone_number = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'form-input'}))
    is_active_user = forms.BooleanField(required=False, label='User Account Active', widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))

    class Meta:
        model = TeacherProfile
        fields = ['department', 'designation', 'qualification', 'office_location']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-input'}),
            'qualification': forms.TextInput(attrs={'class': 'form-input'}),
            'office_location': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['is_active_user'].initial = self.instance.user.is_active


# ============================================================================
# 4. Courses & Topics Forms
# ============================================================================

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['department', 'programs', 'code', 'title', 'description', 'credits', 'is_active']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'programs': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. CS201'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Data Structures & Algorithms'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'credits': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class TopicForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Topic
        fields = ['course', 'order_index', 'title', 'description', 'learning_objectives']
        widgets = {
            'order_index': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 50}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Topic title'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Topic scope / syllabus summary'}),
            'learning_objectives': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Key competencies...'}),
        }


# ============================================================================
# 5. Class Section & Timetable Forms
# ============================================================================

class ClassSectionForm(forms.ModelForm):
    class Meta:
        model = ClassSection
        fields = ['course', 'semester', 'section_code', 'primary_teacher', 'capacity', 'room_number', 'is_active']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'section_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. A, B, Sec-1'}),
            'primary_teacher': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 200}),
            'room_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Lab 301'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model = ClassSchedule
        fields = ['class_section', 'teacher', 'day_of_week', 'start_time', 'end_time', 'room']
        widgets = {
            'class_section': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'room': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Room 402'}),
        }


# ============================================================================
# 6. Assignment, Assessment, Resource & Announcement Forms
# ============================================================================

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['class_section', 'title', 'description', 'topic', 'issue_date', 'due_date', 'max_marks', 'attachment', 'allow_late_submission', 'is_published']
        widgets = {
            'class_section': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Assignment Title'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Instructions...'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '1'}),
            'attachment': forms.FileInput(attrs={'class': 'form-input'}),
            'allow_late_submission': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['class_section', 'title', 'assessment_type', 'topic', 'date', 'max_marks', 'weightage_percentage', 'is_published']
        widgets = {
            'class_section': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Midterm Examination'}),
            'assessment_type': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '1'}),
            'weightage_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0', 'max': '100'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class LearningResourceForm(forms.ModelForm):
    class Meta:
        model = LearningResource
        fields = ['course', 'topic', 'title', 'description', 'resource_type', 'file', 'external_url', 'is_published']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Resource Title'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Resource summary...'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-input'}),
            'external_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class CourseAnnouncementForm(forms.ModelForm):
    class Meta:
        model = CourseAnnouncement
        fields = ['class_section', 'title', 'content', 'is_pinned']
        widgets = {
            'class_section': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Announcement Title'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Notice content...'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
