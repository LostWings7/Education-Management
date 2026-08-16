# Education Management Portal & Closed-Loop Academic Intelligence Platform

An enterprise-grade, modular Django application providing verified role-based workflows, deterministic academic intelligence engines, grounded AI copilot assistance, and a closed-loop academic recovery lifecycle.

---

## 1. Architectural Philosophy: The Closed-Loop Intelligence Loop

Traditional Student Information Systems (SIS) merely record academic failures post-hoc. This platform connects every academic signal into an unbroken chain of accountability and recovery:

$$\text{Data} \to \text{Intelligence} \to \text{Early Warning} \to \text{Why?} \to \text{Action} \to \text{Monitoring} \to \text{Outcome} \to \text{Recalculation} \to \text{Reporting}$$

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│   1. ACADEMIC DATA      │ ──> │ 2. DETERMINISTIC ENGINE │ ──> │   3. EARLY WARNING      │
│ Immutable Events & Logs │     │ OLS Regression & Buffers│     │ Risk (0-100) & Anomaly  │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
                                                                             │
┌─────────────────────────┐     ┌─────────────────────────┐                  ▼
│   6. STUDENT ACTION     │ <── │ 5. HUMAN INTERVENTION   │ <── ┌─────────────────────────┐
│ Prioritized Action Queue│     │ Faculty Approval & Plan │     │   4. EVIDENCE / WHY?    │
└─────────────────────────┘     └─────────────────────────┘     │ Universal Inspector     │
             │                                                  └─────────────────────────┘
             ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│   7. MONITORING         │ ──> │  8. MEASURABLE OUTCOME  │ ──> │  9. RECALC & REPORTING  │
│ Diagnostic Checkpoints  │     │ Verified Recovery Score │     │ Lower Risk & Transcripts│
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

---

## 2. Key Capabilities & Competitive Differentiation

| Capability Dimension | Conventional SIS / Portal | Our Closed-Loop Intelligence Platform |
| :--- | :--- | :--- |
| **Risk Scoring** | Binary "at-risk" flags or post-hoc term failure notices | **0-100 Continuous Score** with 5 normalized factors, trajectory regression, and dynamic floor guarding |
| **Attendance Analytics** | Simple static percentage counter | **Absence Buffer Engine** computing exact remaining missable sessions before falling below 75% |
| **Explainability** | Black box numbers or unexplained flags | **Universal "Why?" Evidence Inspector** exposing exact mathematical formulas and contributing factors |
| **Actionability** | Unprioritized assignment deadlines | **Normalized Priority Action Queue** ($0.45 \cdot U + 0.35 \cdot R + 0.20 \cdot I$) |
| **Remediation Loop** | Disconnected manual email threads | **Closed-Loop Lifecycle** with checkpoints, evidence scoring, and verified outcome recalculation |
| **AI Architecture** | Generic ChatGPT wrappers with hallucination risk | **Strict RBAC Scoped Copilot** grounded strictly in authoritative InsightObjects with local fallback |
| **Privacy & Safety** | Raw aggregate exports | **Minimum-population suppression ($N < 3$)** and projection safety guards ($N \ge 3$) |

---

## 3. Modular App Matrix

| App | Domain & Scope | Key Components |
|---|---|---|
| **`core`** | Identity, authentication, system roles, audit logging. | Custom `User` (email as unique login ID), `Role` enum, `AuditLog`, `TimeStampedModel`, `@role_required` decorators, `RoleRequiredMixin`. |
| **`academic`** | Academic structure & operations. | `Department`, `Program`, `AcademicYear`, `Semester`, `Course`, `Topic`, `ClassSection`, `Enrollment`, `ClassSchedule`, `ClassSession`, `AttendanceRecord`, `Assignment`, `Assessment`. |
| **`analytics`** | Deterministic Python calculation engines. | `PerformanceAnalyticsService`, `AttendanceAnalyticsService`, `TrendAnalyticsService`, `RiskEngineService`, `AnomalyDetectionService`, `StudentActionPriorityService`, `LongitudinalJourneyService`, `InstitutionalChangeDetectionService`. |
| **`ai_service`** | Provider-independent AI & fallback layer. | `BaseAIProvider`, `GeminiProvider`, `FallbackHeuristicProvider`, `AICopilotService`, `AIObservabilityService`. |
| **`interventions`** | Closed-loop academic intervention tracking. | `InterventionLifecycleService`, `InterventionRecommendationService`, `InterventionCheckpointService`, `InterventionImpactService`. |
| **`notifications`** | In-app, email, and digest dispatching. | `Notification`, `NotificationPreference`, `NotificationDispatcherService`. |
| **`portal`** | User-facing views, command centers, and UI shell. | Student Academic Command Center, Teacher Attention Radar, Admin Institutional Pulse, Universal Evidence Inspector, Global Command Palette (`Ctrl+K`). |

---

## 4. UI/UX Design System & Tokens

The interface follows a modern, technical, calm design system inspired by award-winning digital products:

- **Tokens (`static/css/tokens.css`)**: Deep neutral palette (slate-950 to slate-50) with indigo/violet intelligence accents (`#4f46e5`, `#6366f1`), emerald success (`#10b981`), amber warning (`#f59e0b`), rose danger (`#ef4444`), and cyan AI accents (`#06b6d4`).
- **Typography**: Inter typography system with tabular numeric figures for metrics and JetBrains Mono for mathematical formulas.
- **Microinteractions**: GPU-accelerated transforms (`transform`, `opacity`), scroll reveals (`IntersectionObserver`), accessible command palette (`Ctrl+K`), and slide-out evidence drawer.
- **Accessibility & Motion**: Full keyboard focus visibility, screen reader ARIA attributes, modal focus trapping, and `@media (prefers-reduced-motion: reduce)` overrides.

---

## 5. Seeded Demo Personas & Credentials

The system includes 7 comprehensively seeded student personas and administrative accounts:

| Persona / Role | Email | Password | Academic Profile & Behavior |
| :--- | :--- | :--- | :--- |
| **1. High Achiever** | `student@example.com` | `Student@12345` | Ada Lovelace: 96% attendance, 3.8 GPA, distinction milestone, low risk |
| **2. Attendance Deficit** | `student2@example.com` | `Student@12345` | Charles Babbage: 55% attendance, negative absence buffer, high risk |
| **3. Declining Trend** | `student3@example.com` | `Student@12345` | John von Neumann: Negative OLS regression trajectory slope, high risk |
| **4. Missing Coursework** | `student4@example.com` | `Student@12345` | Margaret Hamilton: Multiple overdue assignments, moderate risk |
| **5. Steady Improver** | `student5@example.com` | `Student@12345` | Linus Torvalds: Positive OLS slope trajectory (+1.4), improving health |
| **6. Concept Friction** | `student6@example.com` | `Student@12345` | Dennis Ritchie: Theory struggle on specific course topics |
| **7. Sudden Anomaly / Rescue** | `student7@example.com` | `Student@12345` | Katherine Johnson: Acute plunge (75&rarr;78&rarr;76&rarr;38), active recovery plan |
| **Faculty (CS)** | `teacher@example.com` | `Teacher@12345` | Alan Turing: Computer Science Professor & Attention Radar |
| **Faculty (DB)** | `teacher2@example.com` | `Teacher@12345` | Grace Hopper: Database Systems Professor |
| **Faculty (AI)** | `teacher3@example.com` | `Teacher@12345` | Claude Shannon: Artificial Intelligence Professor |
| **Administrator** | `admin@example.com` | `Admin@12345` | Institutional Command, Macro Pulse, Data Quality & AI Observability |

---

## 6. Installation & Quickstart

### Step 1: Clone & Setup Virtual Environment
```bash
git clone <repo-url>
cd "Education Management"

# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
```

### Step 4: Run Migrations & Seed Demo Data
```bash
python manage.py migrate
python manage.py reset_demo_data
```

### Step 5: Start Development Server
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your browser.

---

## 7. Automated Test Suite Verification

Run the complete automated test suite (147 tests across all 7 phases):

```bash
# Check Django system integrity
python manage.py check

# Run all automated tests
python manage.py test
```

### Verification Output:
```text
Creating test database for alias 'default'...
...................................................................................................................................................
----------------------------------------------------------------------
Ran 147 tests in 190.376s

OK
Destroying test database for alias 'default'...
Found 147 test(s).
System check identified no issues (0 silenced).
```
