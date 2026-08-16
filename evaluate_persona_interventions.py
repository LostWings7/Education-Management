"""
Evaluates Phase 4 Intervention Recommendation Generation across all 7 Seeded Personas.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import User
from apps.academic.models import StudentProfile, Semester, ClassSection
from apps.interventions.models import Intervention
from apps.interventions.services import InterventionRecommendationService

active_semester = Semester.objects.filter(is_active=True).first()
students = StudentProfile.objects.all().order_by('student_id')
admin_user = User.objects.filter(is_superuser=True).first()

print("=" * 90)
print(f"PHASE 4 INTERVENTION RECOMMENDATION EVALUATION ({active_semester})")
print("=" * 90)

# Clear any previous transient recommendations to simulate clean first-run scan
Intervention.objects.filter(status=Intervention.Status.RECOMMENDED).delete()

for s in students:
    user = s.user
    enr = s.enrollments.filter(class_section__semester=active_semester).first()
    sec = enr.class_section if enr else None

    if not sec:
        continue

    recs = InterventionRecommendationService.generate_recommendations_for_student_section(
        student=s,
        section=sec,
        creator_user=admin_user
    )

    print(f"\n[{s.student_id}] {user.get_full_name()} ({user.email})")
    print(f"  • Course: {sec.course.code} (Sec {sec.section_code})")
    if recs:
        for r in recs:
            print(f"  --> RECOMMENDED INTERVENTION:")
            print(f"      - Title         : {r.title}")
            print(f"      - Category      : {r.get_category_display()}")
            print(f"      - Target Metric : {r.get_primary_target_metric_display()}")
            print(f"      - Priority      : {r.get_priority_display()}")
            print(f"      - Trigger Type  : {r.trigger_insight_type}")
            print(f"      - Objective     : {r.objective}")
            print(f"      - Action Steps  : {r.actions.count()} configured tasks")
    else:
        print("  --> No remedial intervention recommended (Student in good standing).")

print("\n" + "=" * 90)
