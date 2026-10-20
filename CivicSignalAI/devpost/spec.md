---
doc: spec
status: approved
---

# CivicSignal AI — Technical Spec

> Historical planning record: this approved specification describes the original anonymous, no-map, no-photo plan. The dated implementation revision at the end documents the later application and supersedes the old runtime/API descriptions for current operation. It does not claim the later features were in the original plan or that a learner completed a walkthrough.

## How This Works, In Plain Language
CivicSignal AI is a small, local civic reporting app with two main user flows: the citizen flow and the team flow. A citizen enters a short description, category, and optional landmark, then previews rule-based analysis before final submission. The analysis suggests a summary, likely missing details, priority, category-based routing cue, and possible duplicates. It is clearly labelled “Rule-based analysis,” so the app never implies that a heuristic suggestion is a verified fact.

The team flow uses the same persisted data. After a report is submitted, the team dashboard reads the same records as the citizen view. A team member can acknowledge the issue, add a progress note, and resolve it only after a resolution note is entered. The citizen view reloads the same report data and sees the updated timeline, status, and final resolution note.

The architecture keeps the proof of concept small and understandable. The app will use one lightweight backend with a local database so both sides read and write the same records. This solves the core requirement that the citizen and team views must stay in sync after refresh and restart. An external AI service is optional and may be added later behind a clearly isolated adapter, but it must never be required for the app to function.

This design is intentionally aimed at a five-person beginner-friendly team working within a hackathon window. It keeps the setup free, local, and testable without introducing paid accounts or heavy infrastructure.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. The citizen enters a description, category, and optional landmark. The browser validates the fields and sends them to the analysis-preview endpoint.
2. The backend analyzes the input using rules, reads existing reports only to suggest possible duplicates, and returns suggestions. Preview does not write to SQLite, create a report, or add a timeline event.
3. The citizen reviews the summary, category/route cue, priority, missing-detail prompts, and duplicate suggestions. These are suggestions, not verified facts.
4. The citizen's final submit action sends the original report fields to the report-creation endpoint. The backend recomputes summary and priority when analysis succeeds, then inserts the report and its initial creation timeline event in one SQLite transaction. It commits only if both inserts succeed; otherwise it rolls back both.
5. The report appears in the shared team queue. The citizen tracking screen shows report IDs submitted in that browser; this is a display convenience, not authentication or privacy protection.
6. The team acknowledges the report, moves it forward to in-progress, and may add progress notes. Status changes and notes are written to the same SQLite database and timeline.
7. The app displays an in-app confirmation/status notice when it receives a successful create or team update. It does not send email, SMS, push, or background notifications.
8. The team may add a short evidence note/reference. Evidence is optional; no file or photo upload is required. To resolve, the team must provide a non-empty resolution note.
9. The citizen reloads the shared data and sees status and timeline updates. Reports, statuses, and events remain available after refresh, SQLite connection close/reopen, and app restart.

## Stack
This stack choice is now final for the proposed specification. The recommendation is Python + FastAPI + SQLite for the backend and a lightweight browser frontend (plain HTML + CSS + JavaScript) for the UI. This recommendation is chosen because it is the simplest approach that still satisfies the shared-data and persistence requirements, keeps dependencies minimal, and remains accessible to a beginner-friendly five-person team.

### Comparison

#### Python + FastAPI + SQLite
- Beginner learning effort: low to moderate. Python is approachable and the API concepts are easy to explain. FastAPI keeps route definitions and validation clear and readable.
- Implementation complexity: low to moderate. One backend service and one database create a clean, explainable data flow.
- Team collaboration: good. Small number of moving parts makes code ownership simple and easier for a beginner team to review.
- Dependencies: small and free. Python, FastAPI, SQLite, and a local static frontend are enough for the MVP.
- Strengths: shared data layer, persistence, transparent API contract, easy testing, low cost.
- Weaknesses: requires a backend server, so there is an extra process to run locally.

#### React + TypeScript + Node/Express + SQLite
- Beginner learning effort: moderate to high. React, TypeScript, and Express introduce more moving parts and more syntax to learn.
- Implementation complexity: moderate to high. More files, build tooling, state concerns, and a framework layer increase the amount of debugging and setup a beginner team must manage.
- Team collaboration: workable but more complex. A larger frontend toolchain usually means more configuration and more abstraction to understand.
- Dependencies: larger and more package-heavy. More packages and tooling mean more places for setup issues and upgrade churn.
- Strengths: strong frontend structure and good long-term ergonomics for larger apps.
- Weaknesses: more complexity than needed to prove a small civic workflow; a bigger learning curve than the team requires for a devpost proof-of-concept.

### Recommended final stack
- Frontend: plain HTML + CSS + JavaScript served by FastAPI locally
- Backend: Python + FastAPI
- Database: SQLite
- Storage: a local SQLite file on disk
- Database access: Python standard-library `sqlite3`; no ORM
- External AI: enhancement-only and excluded from the MVP; no credentials are needed

### Why this is the chosen stack
- It meets the project requirement that the citizen and team views use the same persisted records and timeline.
- It provides a clean, testable backend API without unnecessary complexity.
- It keeps the app free and manageable for a hackathon.
- It is easier for a beginner team to understand, debug, and explain in a short demo.
- It keeps the external AI layer optional and non-blocking.

This means the selected MVP stack is confirmed as:
- Frontend: plain HTML, CSS, and JavaScript served locally
- Backend: Python + FastAPI
- Database: SQLite
- Persistence: local SQLite file on disk
- External AI: optional and not required for the core workflow

For the MVP, rule-based analysis is the only analysis implementation. A future external AI adapter is an enhancement outside the MVP and may be considered only after verifying cost, terms, and limits. The core workflow has no external service credentials or network dependency.

The frontend will not be swapped to a heavier framework as part of this MVP. The spec stays intentionally small, local, and beginner-friendly, consistent with the approved scope and PRD.

This is the final technology decision for the proposed spec. It remains a draft until the team approves the specification, but the stack choice itself is no longer left unresolved.

### Documentation links
- Python: https://www.python.org/
- FastAPI: https://fastapi.tiangolo.com/
- SQLite: https://sqlite.org/
- Uvicorn: https://www.uvicorn.org/

## Where It Runs and How Someone Tries It
Runtime:
- Local development machine
- Backend runs as a local Python service
- Frontend runs in the browser and calls the local API
- Browser access is required for the demo, with no external deployment required for the MVP

Environment requirements:
- Python 3.11 or later
- SQLite support included with the Python runtime
- Browser for demo operation
- No external AI credentials

How to start it locally from the project root on Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for the citizen screen and `http://127.0.0.1:8000/team.html` for the team dashboard. FastAPI serves the `static/` directory and API from the same origin. Demo seeding/reset is optional; the app starts with the approved empty state unless the team intentionally adds clearly labelled sample records.

Demo recording:
- Public GitHub repository is required for the final hackathon submission.
- Deployment is optional and does not replace the required demo video.
- The demo should show the full workflow in under a few minutes: report submission → rule-based analysis → suggested duplicate → team acknowledgement → status change → resolution note → citizen update.

## Look and Feel
The visual direction should remain consistent with the PRD and scope:
- approachable and trustworthy, not bureaucratic or intimidating
- clean interface with minimal friction
- mobile-friendly public form with readable spacing and clear labels
- team dashboard that looks functional and professional but still simple
- strong emphasis on labels and status clarity
- neutral civic-tech palette: soft blue or slate accents with white backgrounds and readable contrast
- typography should be straightforward and highly legible, prioritizing clarity over decorative effects
- no heavy or flashy brand styling that would distract from the workflow

The stack selected should support this without requiring a large CSS system or complex component library. A minimal custom UI is enough for the proof of concept.

## Components

### Citizen Reporting Interface
What it does: collects the issue description, category, optional location or landmark, and shows analysis before submission.
PRD ref: `prd.md > Screens and Layout`, `prd.md > Issue Submission and AI Analysis`.
Responsibilities:
- validate required fields
- call analysis API
- show rule-based or AI-generated labels
- if analysis is unavailable, show the specified plain fallback message without fabricating suggestions and keep valid report submission enabled
- show a persistent “Local demo” notice; the application is not connected to a city service
- display duplicate suggestion panel
- submit the final report

### Citizen Tracking Interface
What it does: shows the citizen’s submitted issues and allows them to open a report detail view.
PRD ref: `prd.md > Citizen Status Tracking`.
Responsibilities:
- fetch the shared report list and display report IDs submitted through this browser, using a `localStorage` list of IDs
- make clear that this browser-side display filter is not authentication or access control; the backend and team dashboard use shared records
- render status timeline and final note
- join the report with the same shared persistence layer used by the team view

### Simulated Notifications
What it does: displays a brief in-app confirmation after submission and an in-app status/timeline notice when refreshed data contains a new team event.
PRD ref: `prd.md > Product Decisions`, `prd.md > Citizen Status Tracking`.
Responsibilities:
- use visible, clearly simulated in-app notices only
- rely on the persisted report timeline as the source of status history
- send no email, SMS, push, or background notifications

### Team Dashboard
What it does: gives team members an operational queue for incoming reports.
PRD ref: `prd.md > Team Dashboard Actions`.
Responsibilities:
- list reports with status filters
- show a persistent “Local demo” notice; identify intentionally seeded sample rows as demo samples
- open report detail
- acknowledge issues
- update progress notes
- resolve reports only when a resolution note is present
- optionally enter a short evidence note or reference; no file/photo upload is required
- show clear empty and no-filter-results states

### Shared API Layer
What it does: exposes endpoints for the frontend and enforces consistent rules for validation, persistence, and timeline updates.
PRD ref: `prd.md > Persistence and Recovery`, `prd.md > Acceptance Criteria`.
Responsibilities:
- create reports
- read report lists and details
- update status and notes
- guard required resolution logic
- persist the same records in the shared database

### Rule Analysis Engine
What it does: performs the default heuristic analysis without relying on an external service.
PRD ref: `prd.md > Issue Submission and AI Analysis`.
Responsibilities:
- parse report text
- suggest a summary from the report description
- infer likely category and priority from keywords
- flag missing fields
- compare the new description against existing reports for duplicate suggestions
- return results with a “Rule-based analysis” label

### Duplicate Detection Service
What it does: compares incoming descriptions against existing reports using a simple explainable method.
PRD ref: `prd.md > Duplicate Suggestions`.
Responsibilities:
- normalize text for comparison
- use keyword overlap and similarity checks
- return suggested duplicate candidates that are clearly labeled as suggestions
- never auto-merge or auto-confirm duplicates

### Optional External AI Adapter
What it does: documents a possible future enhancement; this adapter is not implemented in the MVP.
PRD ref: `prd.md > Issue Submission and AI Analysis`.
Responsibilities:
- remain outside the core workflow unless a later, approved project revision adds it
- require verification of availability, terms, usage limits, and possible charges before use
- preserve the rule-based engine as the working fallback

### Persistence Layer
What it does: reads and writes reports and timeline entries in the chosen database.
PRD ref: `prd.md > Persistence and Recovery`.
Responsibilities:
- save report creation data
- save status updates and notes
- reload on page refresh and app restart
- ensure both views use the same records and shared timeline

## API Contract
The backend provides a small, explicit API for the prototype. All routes are local to the demo app and are designed for a beginner-friendly implementation. The contract below is intentionally simple and constrained to the approved project scope.

### Shared conventions
- Base path: `/api`
- JSON request/response bodies unless otherwise noted
- Invalid JSON, missing fields, invalid field values, and blank required notes return HTTP 422 with field-level details
- Not-found errors return HTTP 404
- A valid request that conflicts with the report's current state returns HTTP 409
- The app is a demo without real authentication, session users, or private citizen-level access controls

### Supported categories
These five category values are based only on the issue examples already present in the approved scope and PRD:
- `overflowing_garbage` — overflowing garbage
- `broken_streetlight` — broken streetlight
- `damaged_road` — damaged road
- `water_leak` — water leak
- `unsafe_sidewalk` — unsafe sidewalk

The rule-based `category_suggestion` uses one of these values or returns null when there is not enough signal. It is a category-based routing suggestion only: it does not assign a department, route to an agency, or trigger a real-world handoff.

### Preview analysis request
`POST /api/reports/preview`

Request body:
- `description`: required string, trimmed length 1-2000 characters
- `category`: required string from the supported category list above
- `landmark`: optional string, max 200 characters

Behavior:
- Runs the rule-based analysis engine only
- Returns suggested summary, category hint, priority hint, missing fields, and duplicate suggestions
- Does not create a persisted report
- Does not create a report timeline event
- Does not write to SQLite

Response 200:
- `source`: `rule_based`
- `summary`: string
- `category_suggestion`: one supported category value or null
- `priority_hint`: `low`, `medium`, `high`, or null
- `missing_fields`: array of strings
- `duplicate_suggestions`: array of objects with `id`, `summary`, and `match_reason`

The backend may read existing reports to calculate duplicate suggestions, but preview must not insert, update, or delete any database row.

Error response:
- 503: analysis engine failed; return `detail: Analysis unavailable; you may still submit your report.` and make no database changes

### Report creation
`POST /api/reports`

Request body:
- `description`: required string, trimmed length 1-2000 characters
- `category`: required string from the supported category list above
- `landmark`: optional string, max 200 characters

Validation rules:
- `description` and `category` are required
- `description` may not be empty or whitespace-only
- `category` must be one of the five supported categories
- `landmark` is optional and may be empty or null
- A report can be created even when duplicate suggestions are present; they are recommendations only
- The backend recomputes summary and priority from the final submitted description; client-supplied summary and priority fields are not accepted
- `demo_data_flag` is server-controlled and is not accepted from this request; reports created through this endpoint default to `false`
- if rule-based analysis fails, creation still proceeds with the submitted description, category, and landmark; no summary or priority is fabricated
- insert the report and its initial `created` event in one SQLite transaction; commit only when both inserts succeed, and roll back both if either insert fails

Response 201:
- `id`: unique report id
- `description`, `category`, `landmark`
- `status`: `submitted`
- `summary`: backend-generated rule-based summary, or null if analysis failed
- `priority_hint`: suggested value or null if analysis failed
- `analysis_source`: `rule_based` or `unavailable`
- `analysis_warning`: present only when analysis is unavailable, with the message “Analysis unavailable; your report was saved without suggestions.”
- `demo_data_flag`: `false`
- `created_at`, `updated_at`, `resolved_at`
- `resolution_note`: null
- `timeline`: one initial `created` event with `actor_type: citizen`, `actor_name: Citizen`, `message: Report submitted`, and the creation timestamp

Error responses:
- 422: invalid request body, missing required field, unsupported category, or field constraint failure
- 500: report or initial event could not be saved; the transaction is rolled back and neither record is created

### Report listing
`GET /api/reports`

Query params:
- `status`: optional filter, one of `submitted`, `acknowledged`, `in_progress`, `resolved`

Response 200:
- array of report summaries containing `id`, `description`, `category`, `landmark`, `status`, `summary`, `priority_hint`, `demo_data_flag`, `analysis_source`, `created_at`, and `updated_at`
- without a filter, the API returns all shared demo reports; the citizen browser applies its local submitted-ID display filter, while the team dashboard displays the shared queue

### Report details
`GET /api/reports/{report_id}`

Response 200:
- full report including `id`, `description`, `category`, `landmark`, `status`, `summary`, `priority_hint`, `demo_data_flag`, `analysis_source`, `created_at`, `updated_at`, `resolved_at`, `resolution_note`, and timeline entries

Error responses:
- 404: report not found

### Team status update
`PATCH /api/reports/{report_id}/status`

Request body:
- `status`: optional target status, one of `acknowledged`, `in_progress`, `resolved`; omit it for a note-only update
- `note`: optional string for progress notes
- `resolution_note`: optional string
- `evidence_note`: optional short text/reference; no file upload
- `actor_name`: required string for the team member making the update

Validation rules:
- `actor_name` must be non-empty
- include `status` or at least one of `note`, `resolution_note`, or `evidence_note`
- provided notes must contain non-whitespace text
- note-only updates are allowed while status is `acknowledged` or `in_progress` and leave status unchanged
- evidence-only updates are allowed while status is `acknowledged` or `in_progress` and leave status unchanged
- `resolution_note` is allowed only with `status: resolved`
- resolving requires a non-empty `resolution_note`
- every requested status change must follow the allowed transition list below

Response 200:
- updated report object
- `timeline_events`: the event or events appended by this request; a status change and a separate progress note may append two events

Error responses:
- 422: invalid body, unsupported status value, blank required text, or missing resolution note
- 404: report not found
- 409: valid status value but disallowed transition, note-only update in a state that does not allow notes, or attempt to modify a resolved report
- 500: the report update or one of its timeline events could not be saved; the transaction is rolled back

### Timeline event mapping
Every accepted team update changes the report and inserts its corresponding event record(s) in the same SQLite transaction. If the report update or any event insert fails, the transaction rolls back and the API returns HTTP 500; a partial update is never reported as successful. Events use `actor_type: team` and the request's `actor_name`.

- A transition to `acknowledged` or `in_progress` inserts one `status_changed` event with `status_from`, `status_to`, and a readable status-change message.
- A non-empty `note` inserts one separate `progress_note` event, including when sent with a status transition.
- A transition to `resolved` inserts one `resolved` event with `status_from: in_progress` and `status_to: resolved`. Its message is the required `resolution_note`, and it carries any optional `evidence_note` sent with the resolution.
- An `evidence_note` sent by itself while `acknowledged` or `in_progress` inserts one `evidence_added` event. If sent with a non-resolution status change, it inserts a separate `evidence_added` event.
- For a request containing multiple accepted changes, insert events in this order: status/resolution event, progress-note event, then `evidence_added` when applicable. Evidence attached to a `resolved` event is included there and does not create a second event. The API response returns events in insertion order.
- A resolution note cannot be sent by itself; it is accepted only with the transition to `resolved`. No update is accepted after resolution.

### Timeline events
`GET /api/reports/{report_id}/timeline`

Response 200:
- array of timeline entries with `id`, `report_id`, `event_type`, `actor_type`, `actor_name`, `message`, `status_from`, `status_to`, `evidence_note`, and `created_at`
- `event_type` is `created`, `status_changed`, `progress_note`, `evidence_added`, or `resolved`; fields not applicable to an event are null

Error response:
- 404: report not found

### Health check
`GET /api/health`

Response 200:
- `status: ok`

## Allowed status transitions
The only status changes are forward and sequential:
- `submitted -> acknowledged`
- `acknowledged -> in_progress`
- `in_progress -> resolved`, only with a trimmed, non-empty `resolution_note`

No other status change is allowed. A status cannot be skipped, moved backward, or changed after `resolved`. Repeating the current status is not a status update; the team can submit a note-only update where allowed. The backend rejects a disallowed transition with HTTP 409 and rejects missing/blank required text with HTTP 422.

## Testing plan
The test suite should validate the real app behavior against the local SQLite database and the HTTP contract, not just in-memory mocks.

- Input validation tests for missing description, missing category, empty strings, and unsupported category values
- Analysis preview tests verifying that preview returns analysis output and duplicate suggestions without creating or changing a report or timeline event
- Report creation tests verifying that valid reports are saved once, assigned a unique ID, and appear in list/detail views with exactly one initial creation event; submitted summary and priority fields are rejected and backend values are authoritative
- Duplicate suggestion tests verifying that likely matches are surfaced as suggestions only and do not block submission
- Category-routing tests verifying suggestions use only the supported category values and never assign a real team or agency
- Status transition tests covering every allowed transition, skipped/backward/repeated transitions, note-only updates, and updates after resolution
- Resolution-note tests verifying missing or whitespace-only notes are rejected and a valid note is recorded with the resolved event
- Optional evidence tests verifying a report can be resolved without evidence and that a supplied text/reference is visible in the timeline
- Simulated-notification tests verifying in-app confirmation/status notices without any external delivery
- Empty/no-result tests verifying clear citizen and team messages for no reports and for filters with no matches
- Persistence tests ensuring data remains available after closing and reopening the SQLite connection, and after restart of the application process
- Timeline mapping tests verifying status, progress-note, resolution-note, evidence-only, and combined updates create the specified event types in deterministic order and appear in the timeline
- List/detail response tests verifying `GET /api/reports` returns `demo_data_flag` and `analysis_source`, and `GET /api/reports/{report_id}` returns both fields consistently; normal API-created reports return `demo_data_flag: false`, intentionally seeded samples return `true`, and reports saved after analysis failure return `analysis_source: unavailable`
- Demo-data UI tests verifying both screens show the local-demo notice and seeded rows are labeled as demo samples
- Analysis-failure tests verifying preview returns HTTP 503 without writes, while final submission still creates a report and event with null suggestions and an unavailable source label
- Atomic-creation tests forcing the initial event insert to fail and verifying that the report insert is rolled back; successful creation leaves exactly one report and one initial event

## Security and access model
This is a demonstration application. It does not implement real authentication, private user accounts, or citizen-level access restrictions. The citizen browser stores the IDs it submitted and uses them only to filter what that browser displays. This is a convenience, not a security boundary: the API and team dashboard use shared demo records, and anyone with access to the local app can access those records. Do not describe reports as private or isolated.

The same persisted report records and timeline are shared across the citizen and team views in the local app, but the prototype is not a production-grade access-control system.

## Data Model
The app will store a single source of truth for reports and their timeline. The citizen and team dashboards must read the same persisted data rather than separate local states.

### Report
- id: unique report identifier
- description: trimmed, non-empty citizen report text (maximum 2000 characters)
- category: issue category selected by user
- landmark: optional location or landmark string
- status: one of submitted, acknowledged, in_progress, resolved
- priority_hint: suggested priority from analysis output, or null if rule-based analysis failed
- summary: generated summary text or null if rule-based analysis failed
- created_at: timestamp
- updated_at: timestamp
- resolved_at: timestamp or null
- resolution_note: note required before a report is resolved
- demo_data_flag: boolean; defaults to false for API-created reports and is true only for intentionally seeded sample reports
- analysis_source: `rule_based` or `unavailable`

### ReportEvent or TimelineEntry
- id: unique event identifier
- report_id: foreign key to Report.id
- event_type: created, status_changed, progress_note, evidence_added, resolved
- actor_type: citizen or team
- actor_name: human-readable actor label
- message: note or status message
- status_from: previous status for `status_changed` or `resolved` events; otherwise null
- status_to: new status for `status_changed` or `resolved` events, or `submitted` for the creation event; otherwise null
- evidence_note: optional text/reference, not a file
- created_at: timestamp

### AnalysisResult (preview response only; not stored)
- source: rule_based or external_ai
- summary: rule-based preview summary
- category_suggestion: suggested category
- priority_hint: suggested priority
- missing_fields: list of missing detail prompts
- duplicate_ids: list of likely duplicate IDs

Preview results exist only in the API response/browser. The final report stores the backend-recomputed summary and priority on the Report record; there is no analysis-results table in the MVP.

### Demo-data semantics
`demo_data_flag` defaults to `false` for reports created through the normal report API. If the team intentionally seeds sample reports, each seeded row must set the flag to `true`; seeding remains optional. The flag distinguishes seeded examples, not real versus private citizens: every record in this local proof of concept is demo data. Both citizen and team screens therefore show a persistent “Local demo — not connected to a city service” notice. Rows with `demo_data_flag: true` also show a “Demo sample” label. The normal API does not allow clients to set this flag.

### Design note
Use two SQLite tables, `reports` and `report_events`, accessed with Python's standard-library `sqlite3` module. No ORM or separate analysis-results table is needed. Summary, priority, category suggestion, missing fields, and duplicate suggestions are computed by the rule-based service; preview results remain only in the response/browser until final submission. When analysis succeeds, the backend recomputes and stores summary and priority during report creation. If it fails, those fields remain null and the report is still saved with `analysis_source: unavailable`.

Report creation and its initial `created` event are inserted in one explicit SQLite transaction. Both inserts must succeed before commit; any failure rolls the transaction back so neither row remains. Team updates and their mapped event rows are also committed together as described in the API contract.

### Analysis preview vs final submission
The preview flow and final report submission are intentionally separate.

- `POST /api/reports/preview` returns analysis suggestions only and does not persist anything.
- `POST /api/reports` is the one final-submit action; it recomputes authoritative summary and priority, then creates the report and exactly one initial timeline entry.
- A report must not exist in the database until the user submits the final form.
- A preview may read existing reports for duplicate comparison, but it must never write a report, timeline event, or audit record.
- If preview analysis fails, return HTTP 503 with a clear unavailable message and no fabricated fields; the UI must still allow final submission of valid input.
- If analysis fails during final creation, persist the report and initial event with null summary/priority and `analysis_source: unavailable`; do not claim that analysis succeeded.

This rule is important for clarity and for the beginner-friendly architecture: the user can inspect and revise the recommendation before committing the report.

## External AI and fallback rules
External AI is enhancement-only and is not part of the MVP implementation. Rule-based analysis must work without external credentials, API keys, paid services, or network access. If a later project revision proposes an external service, verify availability, terms, usage limits, and possible charges before enabling it; label output “AI-generated” only when an external model actually produced it. MVP heuristic output is always labelled “Rule-based analysis.”

## File Structure
This is the proposed file structure for the proof of concept. It is intentionally small and readable for a beginner team.

```text
civicsignal-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                  # settings and environment config
│   ├── database.py                # SQLite connection and schema setup
│   ├── models.py                  # simple data classes and SQLite row mapping
│   ├── schemas.py                 # request/response validation models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── reports.py             # report routes
│   │   └── health.py              # health check endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis.py            # rule-based analysis logic
│   │   ├── duplicates.py          # duplicate detection logic
│   │   ├── status.py              # status transition logic
│   └── utils/
│       ├── __init__.py
│       └── labels.py              # shared labels for UI text and display
├── static/
│   ├── index.html                 # citizen reporting page
│   ├── team.html                  # team dashboard and detail view
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js                 # citizen-side behavior
│       ├── team.js                # team-side behavior
│       └── api.js                 # fetch helpers
├── tests/
│   ├── test_analysis.py
│   ├── test_duplicates.py
│   ├── test_api_reports.py
│   ├── test_status_flow.py
│   └── test_persistence.py
├── data/
│   └── civicsignal.db            # SQLite file, generated at runtime
├── devpost/
│   ├── learner-profile.md
│   ├── scope.md
│   ├── prd.md
│   └── spec.md
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

This structure keeps the app understandable to a beginner team while still making the backend, frontend, and data layer explicit.

## External Services and Dependencies
The app should avoid external dependencies on the critical path unless they are verified and free.

### Backend framework
- FastAPI
- Purpose: API and local web service
- Cost: free
- Rate limits: none for local dev
- Required setup: Python environment and dependency install

### Database
- SQLite
- Purpose: persistent local data store for reports and events
- Cost: free
- Data model: local file-based database without external service setup
- Notes: using SQLite keeps the MVP easy to reason about and test

### Optional external AI service
- Purpose: optional enhancement for summarization or classification after verification
- Constraint: must be free, verified, and fully optional
- Required checks before enabling: availability, usage limits, terms, and possible charges
- Fallback: rule-based analysis remains active if the service is unavailable or unauthorized

### Frontend assets
- Plain HTML/CSS/JavaScript served by FastAPI
- Purpose: deliver the citizen and team views without a heavy framework
- Cost: free
- Tradeoff: a small amount of custom CSS/JavaScript instead of framework-provided components

## Important Failure Modes
- **Database unavailable or a write fails** → roll back the active transaction, show a clear error, and do not report a successful save or partial timeline update.
- **Input invalid or required fields missing** → show inline validation and prevent submission.
- **No reports or no filter matches** → show the corresponding clear empty/no-results message rather than an empty table or broken panel.
- **Rule-based analysis fails unexpectedly** → preview returns HTTP 503 with “Analysis unavailable; you may still submit your report.” and makes no database changes. The submit control remains available for valid input. If analysis fails again during final creation, save the report and creation event with `summary: null`, `priority_hint: null`, and `analysis_source: unavailable`; show “Analysis unavailable; your report was saved without suggestions.” Do not invent suggestions or display either an AI-generated or Rule-based analysis label for that failed result.
- **External AI service is unreachable or rate-limited** → fall back to rule-based analysis and clearly label the output.
- **Duplicate detector returns matches** → show them as suggestions only; do not block or auto-confirm the report.
- **Team tries to resolve without a resolution note** → block action and show error text; require note before state change.

## What Was Simplified and Why
- **Single local backend instead of multiple services** — this keeps the proof of concept cohesive and makes shared persistence straightforward.
- **SQLite instead of a hosted database** — this meets the persistence and restart requirement without introducing cloud setup or payment risk.
- **No auth system** — the MVP is built around a demo-safe workflow and does not need real accounts to prove the reporting loop.
- **No live mapping or GIS** — location is optional and can be a text landmark instead of a real map service.
- **No real government integration** — the product is intentionally local and demonstrative, matching the approved boundaries.
- **No binary photo/file upload** — evidence remains optional and can be described or referenced with a short text field, avoiding file storage complexity.

## Decisions and Open Issues
This spec is intentionally written as a draft blueprint for review.

### Decisions made in this draft
- Final recommended stack: Python + FastAPI + SQLite + plain HTML/CSS/JavaScript frontend.
- Rule-based analysis is the default and must work without an external AI service.
- The same persisted report records and timeline are used by both citizen and team views.
- Status transitions are explicit, with resolution requiring a note.
- Duplicate suggestions are non-binding and not treated as confirmed facts.
- Persistence is tested against the real storage solution chosen for the app, not only in-memory or browser state.
- Demo data is labelled clearly and does not imply authenticated private user isolation.
- The analysis preview is separate from final submission and does not persist a report.
- The app is a demo-only workflow without real authentication or private citizen-level access controls.
- Demo-data seeding/reset is optional; normal startup shows the empty state.

### Tradeoff explained
The local backend + SQLite approach adds a small amount of setup compared with browser-only state, but it is the simplest option that satisfies the shared-data and restart requirements. It is also free and easier for a beginner team to reason about than a more complex authentication-heavy or cloud-backed architecture. This keeps the app focused on the proof-of-concept, while the optional AI adapter remains isolated and non-essential.

### Learner uncertainty
No distinct learner uncertainty about the chosen technical approach was explicitly identified in the planning record. The learner's stated goal is to understand the code and plan-first workflow; that goal is carried forward without inventing a separate uncertainty.

### Open issues and approval dependencies
- None remain from the approved scope or PRD; `prd.md > Open Questions` states that none remain.

External AI is enhancement-only and excluded from the MVP. The selected MVP frontend remains plain HTML, CSS, and JavaScript; changing that choice would require a separately approved revision.

This specification is intentionally draft-only and is being shown for review before approval or the next planning/build stage.

## Implementation Revision — 2026-10-19

This implementation record was checked against `app/main.py`, the API/service modules, active HTML/JavaScript, and the current tests. The approved text above remains the historical plan; this revision describes later implementation and does not establish that the learner completed the Build workflow.

### Runtime and frontend
- FastAPI is created in `app/main.py`; its lifespan initializes or additively upgrades SQLite. Uvicorn serves the app and mounts `static/`.
- `GET /` serves citizen sign-in/registration; `/home`, `/report` (also `/report.html`), `/static/index.html`, and `/static/report.html` require a citizen session. `/team-login` is the staff sign-in page; `/team` and `/team.html` require a staff session; `/tracking.html` requires a citizen session.
- Citizen pages and scripts are `static/auth.html`, `static/index.html`, `static/report.html`, `static/js/auth.js`, `citizen-session.js`, and `app.js`. The report UI has issue, location/details, and review steps. `app.js` sends preview and submission requests, initializes the map, and uploads selected photos.
- The tracking UI is root `tracking.html` with `static/js/tracking.js`; the team dashboard is root `team.html` with `static/js/team-dashboard.js`. Both use `static/js/api-client.js` where applicable. `team-login.html` and `team-signup.html` are root-served pages. The active frontend is plain HTML/CSS/JavaScript; `App.tsx` and `index.css` are retained but are not wired into a build or route.

### API and authorization
- Citizen authentication: `POST /api/auth/citizen/register`, `/login`, `/logout`; `GET /api/auth/citizen/me`.
- Staff authentication: `POST /api/auth/team/login`, `/logout`; `GET /api/auth/team/me`. Staff accounts are created by the interactive `python -m app.provision_team_user` utility; startup does not seed an account.
- Citizen report API: `POST /api/reports/preview`, `POST /api/reports`, `GET /api/reports/mine`, `POST /api/reports/{id}/images`.
- Team workflow: `GET /api/reports` and `POST /api/team/reports/{id}/updates` require staff authentication. `GET /api/reports/{id}/tracking` and `GET /api/reports/media/{media_id}` require either staff access or ownership by the signed-in citizen. `GET /api/health` is the health endpoint.
- Passwords use scrypt hashes. Opaque session tokens are stored as hashes, expire after eight hours, and are delivered with HTTP-only, SameSite Strict cookies. Secure-cookie behavior is configurable for HTTPS. Login attempts are throttled, and mutating requests check origin where implemented. Citizens cannot enumerate or retrieve another citizen's report or image; staff endpoints require a staff session.
- Report creation persists ownership, report fields (including confirmed coordinates), and the initial event. Team updates and timeline events are stored in shared SQLite. Workflow includes submitted, acknowledged, in-progress, resolved, and rejected states; resolution requires a note and rejection requires a reason.

### Data, media, dependencies, and tests
- SQLite uses `app/database.py` and the standard-library `sqlite3`. Tables include reports, report events, report media, citizen/team users, citizen/team sessions, and team login attempts. Existing databases are additively upgraded; startup does not clear existing accounts or reports.
- Images are validated and re-encoded with Pillow. Uploads allow JPG, PNG, and WebP, at most four per request and 5 MB each, and are stored under `data/private-uploads` by default or `CIVICSIGNAL_UPLOAD_DIR`. Stored paths are not returned to clients. Media is served through an authenticated endpoint, never from the public static directory.
- The only analysis implementation is local heuristic/rule-based logic and duplicate suggestions. Leaflet, Google Fonts, Unsplash imagery, and OpenStreetMap tiles are network-dependent. No external AI, email, OAuth, password-reset, cloud storage/database, or city-system integration is configured.
- Settings: `CIVICSIGNAL_DATABASE_PATH`, `CIVICSIGNAL_COOKIE_SECURE`, and `CIVICSIGNAL_UPLOAD_DIR`. `.env.example` documents them, but the app reads process environment variables and does not itself load `.env`.
- Python requirement used by the project guide is Python 3.11+. Install with `python -m pip install -r requirements.txt`; run with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`; run backend tests with `python -m pytest -q`. The current test files cover analysis, API reports, citizen auth/ownership, duplicates, media, persistence, and team workflow. Node syntax checks are documented in the root README; there is no configured frontend build or automated browser suite.
- Local SQLite and filesystem storage are single-host prototype choices. Back up the database and uploads together; do not expose either in a public source repository.
