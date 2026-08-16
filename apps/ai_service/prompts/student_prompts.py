"""
Role-specific prompt templates for Student, Teacher, Administrator, and Study Planner.
"""

STUDENT_EXPLANATION_PROMPT = """
Please provide a clear, empathetic explanation of the following academic analytics insight or support plan for the student.
Highlight the primary contributing factors, explain what the numbers mean in plain English, and provide 1-2 actionable recovery steps.

Target Insight / Subject: {subject}
Contextual Evidence: {evidence}
"""

TEACHER_CLASS_BRIEFING_PROMPT = """
Please generate an executive class briefing for the instructor covering section {course_code} ({section_code}).
Include:
1. Overall Section Academic Health (Average grade, attendance rate).
2. Key Topic Friction Points (Syllabus concepts where student mastery is below 60%).
3. Flagged Students requiring immediate attention (High/Critical risk, acute drops, attendance deficits).
4. Intervention Progress (Active support plans, overdue checklists).
5. Suggested pedagogical focus for the upcoming lecture.
"""

TEACHER_STUDENT_BRIEFING_PROMPT = """
Please provide a concise, confidential 1-page briefing on student {student_name} ({student_id}) enrolled in {course_code}.
Synthesize:
1. Current Academic Standing & Attendance.
2. Trajectory & Anomaly Signals.
3. Active Support Plans & Checklist Progress.
4. Suggested discussion topics for a 1-on-1 student advising consultation.
"""

ADMIN_EXECUTIVE_BRIEFING_PROMPT = """
Please generate a university-wide executive intelligence briefing for institutional leadership.
Synthesize:
1. Macro Indicators (Total enrollments, university average score, overall attendance).
2. Risk Distribution (Density of Critical, High, Moderate, and Low risk students across departments).
3. Department Comparative Insights (Top performing vs departments needing support).
4. Academic Intervention ROI (Total support plans, completion & outcome effectiveness rates).
5. Strategic Areas for Further Review.
"""

STUDY_PLANNER_PROMPT = """
Generate a realistic, balanced 5-day study plan (Monday through Friday) for the student.
Requirements:
1. Focus on weak syllabus topics (<60% mastery) and upcoming pending assignments with deadlines.
2. Incorporate active intervention action steps if present.
3. Attach authentic learning resources from the context if available.
4. Enforce feasibility: Daily study time must not exceed 4.5 hours/day. Do NOT schedule duplicate tasks.
5. Clearly identify items as OFFICIAL_EVENT or AI-SUGGESTED study blocks.

Output Schema:
{
  "plan_title": "String",
  "target_week": "String",
  "total_estimated_hours": Float,
  "days": [
    {
      "day_name": "Monday",
      "date_str": "YYYY-MM-DD",
      "focus_summary": "String",
      "tasks": [
        {
          "course_code": "String",
          "task_type": "TOPIC_STUDY" | "ASSIGNMENT_PREP" | "INTERVENTION_TASK",
          "title": "String",
          "duration_minutes": Integer,
          "description": "String",
          "is_official_event": false,
          "assignment_id": Integer (optional),
          "resource_id": Integer (optional),
          "resource_title": "String" (optional),
          "action_id": Integer (optional),
          "due_date": "String" (optional)
        }
      ]
    }
  ]
}
"""
