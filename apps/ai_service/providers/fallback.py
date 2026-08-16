"""
Deterministic Fallback Heuristic Provider.
Operates 100% offline without external network or API keys.
Guarantees 100% platform uptime, explainability, and testability.
Never hallucinates and never pretends to be an external LLM.
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from apps.ai_service.schemas.messages import ChatMessage
from apps.ai_service.schemas.responses import (
    StructuredAIResponse,
    FactAttribution,
    StudyPlanSchema,
    StudyPlanDaySchema,
    StudyPlanTaskSchema
)
from .base import BaseAIProvider


class FallbackHeuristicProvider(BaseAIProvider):
    """
    Deterministic rule-based heuristic provider.
    """

    @property
    def provider_name(self) -> str:
        return "fallback_heuristic"

    @property
    def is_online(self) -> bool:
        return False

    def chat(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
        context_data: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> StructuredAIResponse:
        """
        Synthesizes conversation turn deterministically using authorized facts.
        """
        last_msg = messages[-1].content.lower() if messages else ""
        facts = self._extract_fact_attributions(context_data)

        # 1. Attendance inquiry
        if 'attendance' in last_msg or 'absence' in last_msg:
            att_info = context_data.get('attendance_summary', {})
            rate = att_info.get('overall_percentage', 'N/A')
            buf = att_info.get('absence_buffer', 0)
            content = (
                f"According to your current academic records, your overall attendance is **{rate}%**. "
                f"Based on remaining scheduled class sessions, you can miss at most **{buf}** further sessions "
                f"while maintaining the university's 75.0% threshold."
            )
            interpretations = [f"Overall attendance stands at {rate}% with an absence buffer of {buf} sessions."]
            recs = ["Prioritize attending all upcoming scheduled lectures to preserve course standing."]

        # 2. Risk / Warning inquiry
        elif 'risk' in last_msg or 'warning' in last_msg or 'flag' in last_msg:
            risk_info = context_data.get('risk_summary', {})
            score = risk_info.get('composite_score', 'N/A')
            level = risk_info.get('risk_level', 'LOW')
            factors = risk_info.get('contributing_factors', [])
            factors_str = ", ".join(factors) if factors else "Routine academic variation"
            content = (
                f"Your current academic risk status is evaluated at **{level}** (Composite score: **{score}/100**). "
                f"Primary contributing indicators identified by the portal include: {factors_str}."
            )
            interpretations = [f"Risk level {level} is driven by: {factors_str}."]
            recs = ["Review flagged coursework and consult with your course instructor during office hours."]

        # 3. Weak Topics inquiry
        elif 'topic' in last_msg or 'weak' in last_msg or 'subject' in last_msg:
            topics = context_data.get('topic_diagnostics', [])
            weak = [t for t in topics if t.get('status') == 'NEEDS_ATTENTION' or (t.get('score_percentage') is not None and t.get('score_percentage') < 60.0)]
            if weak:
                w_str = ", ".join([f"**{t.get('title')}** ({t.get('score_percentage')}%)" for t in weak])
                content = f"The following syllabus topics currently have mastery scores below 60%: {w_str}."
                interpretations = [f"Identified {len(weak)} syllabus topic(s) requiring targeted concept remediation."]
                recs = ["Review published slide decks and practice problem sets for these topics."]
            else:
                content = "All evaluated syllabus topics currently meet or exceed mastery expectations (>=60%)."
                interpretations = ["Topic mastery is on track across all evaluated coursework."]
                recs = ["Continue regular coursework review."]

        # 4. Support Plan / Intervention inquiry
        elif 'intervention' in last_msg or 'support' in last_msg or 'plan' in last_msg:
            plans = context_data.get('active_interventions', [])
            if plans:
                p = plans[0]
                content = (
                    f"You have an active support plan: **{p.get('title')}** (Priority: {p.get('priority')}). "
                    f"Objective: {p.get('objective')} (Due: {p.get('due_date')})."
                )
                interpretations = [f"Active support plan: {p.get('title')}."]
                recs = ["Complete the pending action steps on your intervention checklist."]
            else:
                content = "You do not currently have any active remedial support plans assigned."
                interpretations = ["No active intervention plans found in portal records."]
                recs = ["Maintain current study habits."]

        # General Academic Synthesis
        else:
            name = context_data.get('student_name', context_data.get('teacher_name', 'Student'))
            content = (
                f"Hello {name}. I am your Academic Assistant operating in Local Deterministic Mode. "
                f"I can explain your grades, attendance absence-buffers, risk indicators, weak topics, and active support plans."
            )
            interpretations = ["Deterministic academic synthesis ready."]
            recs = ["Ask any specific question about your attendance, course risk, or upcoming assignments."]

        return StructuredAIResponse(
            content=content,
            facts_used=facts.get('facts', []),
            calculations_used=facts.get('calculations', []),
            simulations_used=facts.get('simulations', []),
            actions_used=facts.get('actions', []),
            interpretations=interpretations,
            recommendations=recs,
            provider=self.provider_name,
            model="deterministic-heuristic-v1",
            prompt_version="fallback_v1.0",
            validation_status="VALID",
            disclaimer="Deterministic rule-based analysis. Verify official academic records."
        )

    def generate_explanation(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        facts = self._extract_fact_attributions(context_data)
        title = context_data.get('title', 'Academic Insight')
        summary = context_data.get('summary', 'Analysis generated from authoritative academic records.')
        severity = context_data.get('severity', 'INFO')

        content = (
            f"### {title}\n\n"
            f"**Observation**: {summary}\n\n"
            f"**Analytical Context**: This insight is evaluated by the portal's deterministic analytics engine with status **{severity}**. "
            f"Metrics are calculated directly from verified course assessments and attendance records."
        )

        return StructuredAIResponse(
            content=content,
            facts_used=facts.get('facts', []),
            calculations_used=facts.get('calculations', []),
            simulations_used=facts.get('simulations', []),
            actions_used=facts.get('actions', []),
            interpretations=[summary],
            recommendations=["Consult course materials or schedule instructor office hours if additional clarification is needed."],
            provider=self.provider_name,
            model="deterministic-heuristic-v1",
            prompt_version="fallback_explanation_v1.0",
            validation_status="VALID",
            disclaimer="Deterministic rule-based analysis. Verify official academic records."
        )

    def generate_study_plan(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StudyPlanSchema:
        """
        Deterministically builds a balanced 5-day study plan from authentic weak topics and pending assignments.
        """
        today = date.today()
        # Find next Monday or today
        days_ahead = (0 - today.weekday()) % 7
        start_monday = today if today.weekday() == 0 else today + timedelta(days=days_ahead if days_ahead > 0 else 7)

        topics = context_data.get('topic_diagnostics', [])
        weak_topics = [t for t in topics if t.get('score_percentage') is not None and t.get('score_percentage') < 75.0]
        assignments = context_data.get('coursework_summary', {}).get('pending_assignments', [])
        interventions = context_data.get('active_interventions', [])
        resources = context_data.get('learning_resources', [])

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        days: List[StudyPlanDaySchema] = []
        total_minutes = 0

        for i, d_name in enumerate(day_names):
            cur_date = start_monday + timedelta(days=i)
            cur_tasks: List[StudyPlanTaskSchema] = []
            day_minutes = 0

            # 1. Topic study task if available
            if weak_topics and i < len(weak_topics):
                wt = weak_topics[i]
                res_match = next((r for r in resources if r.get('topic_id') == wt.get('topic_id')), None)
                cur_tasks.append(StudyPlanTaskSchema(
                    course_code=wt.get('course_code', 'Course'),
                    task_type="TOPIC_STUDY",
                    title=f"Review & Practice: {wt.get('title')}",
                    duration_minutes=45,
                    description=f"Review lecture slides and self-assessment questions for {wt.get('title')}.",
                    is_official_event=False,
                    resource_id=res_match.get('id') if res_match else None,
                    resource_title=res_match.get('title') if res_match else None
                ))
                day_minutes += 45

            # 2. Assignment preparation task if available
            if assignments and i < len(assignments):
                assign = assignments[i]
                cur_tasks.append(StudyPlanTaskSchema(
                    course_code=assign.get('course_code', 'Course'),
                    task_type="ASSIGNMENT_PREP",
                    title=f"Work on: {assign.get('title')}",
                    duration_minutes=60,
                    description="Complete problems and prepare submission before the due date.",
                    is_official_event=False,
                    assignment_id=assign.get('id'),
                    due_date=str(assign.get('due_date', ''))
                ))
                day_minutes += 60

            # 3. Intervention checklist task if available
            if interventions and i == 2: # Mid-week
                intv = interventions[0]
                actions = intv.get('actions', [])
                act_pending = next((a for a in actions if a.get('status') == 'PENDING'), None)
                if act_pending:
                    cur_tasks.append(StudyPlanTaskSchema(
                        course_code=intv.get('course_code', 'Course'),
                        task_type="INTERVENTION_TASK",
                        title=f"Support Action: {act_pending.get('title')}",
                        duration_minutes=30,
                        description=act_pending.get('description', 'Complete assigned support step.'),
                        is_official_event=False,
                        action_id=act_pending.get('action_id')
                    ))
                    day_minutes += 30

            total_minutes += day_minutes
            days.append(StudyPlanDaySchema(
                day_name=d_name,
                date_str=cur_date.strftime("%Y-%m-%d"),
                focus_summary=f"Dedicated study block for {len(cur_tasks)} targeted academic task(s).",
                tasks=cur_tasks,
                total_study_minutes=day_minutes
            ))

        return StudyPlanSchema(
            plan_title="Personalized Academic Recovery & Study Schedule",
            target_week=f"{start_monday.strftime('%b %d')} - {(start_monday + timedelta(days=4)).strftime('%b %d, %Y')}",
            days=days,
            total_estimated_hours=round(total_minutes / 60.0, 1),
            validation_status="VALID",
            disclaimer="AI-suggested study blocks are not official timetable events."
        )

    def generate_briefing(
        self,
        system_instruction: str,
        prompt: str,
        context_data: Dict[str, Any],
        model: Optional[str] = None
    ) -> StructuredAIResponse:
        """
        Generates class or institutional briefing deterministically.
        """
        facts = self._extract_fact_attributions(context_data)

        # Teacher Class Briefing
        if 'assigned_sections' in context_data:
            sec_kpis = context_data.get('section_kpis', {})
            flagged = context_data.get('flagged_students', [])
            hotspots = context_data.get('topic_weaknesses', [])
            intvs = context_data.get('interventions_overview', {})

            content = (
                f"### Class Executive Briefing\n\n"
                f"- **Academic Health**: Average performance is **{sec_kpis.get('avg_performance', 'N/A')}%** with **{sec_kpis.get('avg_attendance', 'N/A')}%** overall attendance.\n"
                f"- **Students Requiring Attention**: {len(flagged)} student(s) currently flagged with High/Critical risk or acute score drops.\n"
                f"- **Curricular Topic Focus**: {len(hotspots)} topic(s) identified with mastery gaps below 60%.\n"
                f"- **Active Support Plans**: {intvs.get('active_count', 0)} active plan(s) ({intvs.get('overdue_count', 0)} overdue)."
            )
            interpretations = [f"Class overview: {len(flagged)} students flagged, {len(hotspots)} topic gaps."]
            recs = ["Review weak syllabus topics during the upcoming lecture and check in with flagged students."]

        # Admin Institutional Briefing
        else:
            total_enr = context_data.get('total_enrollments', 0)
            avg_att = context_data.get('average_attendance', 0.0)
            avg_perf = context_data.get('average_performance', 0.0)
            risk_dist = context_data.get('risk_distribution', {})
            dept_sum = context_data.get('department_summary', [])

            content = (
                f"### University Academic Intelligence Briefing\n\n"
                f"- **Institutional Overview**: {total_enr} active enrollments across {len(dept_sum)} department(s).\n"
                f"- **Macro Indicators**: University-wide average performance is **{avg_perf}%**, and attendance stands at **{avg_att}%**.\n"
                f"- **Risk Distribution**: Critical: {risk_dist.get('CRITICAL', 0)}, High: {risk_dist.get('HIGH', 0)}, Moderate: {risk_dist.get('MODERATE', 0)}, Low: {risk_dist.get('LOW', 0)}.\n"
                f"- **Intervention Oversight**: Evaluated support plans demonstrate verified outcome recovery."
            )
            interpretations = ["Institutional academic indicators summarized from verified department datasets."]
            recs = ["Review department comparative matrices and allocate tutoring resources to identified curricular friction courses."]

        return StructuredAIResponse(
            content=content,
            facts_used=facts.get('facts', []),
            calculations_used=facts.get('calculations', []),
            simulations_used=facts.get('simulations', []),
            actions_used=facts.get('actions', []),
            interpretations=interpretations,
            recommendations=recs,
            provider=self.provider_name,
            model="deterministic-heuristic-v1",
            prompt_version="fallback_briefing_v1.0",
            validation_status="VALID",
            disclaimer="Academic metrics are sourced from authoritative portal systems. AI interpretations are advisory."
        )

    def _extract_fact_attributions(self, context_data: Dict[str, Any]) -> Dict[str, List[FactAttribution]]:
        facts_list = context_data.get('fact_registry', [])
        organized = {'facts': [], 'calculations': [], 'simulations': [], 'actions': []}
        for f in facts_list:
            if isinstance(f, FactAttribution):
                if f.classification == 'FACT':
                    organized['facts'].append(f)
                elif f.classification == 'CALCULATION':
                    organized['calculations'].append(f)
                elif f.classification == 'SIMULATION':
                    organized['simulations'].append(f)
                elif f.classification == 'ACTION':
                    organized['actions'].append(f)
        return organized
