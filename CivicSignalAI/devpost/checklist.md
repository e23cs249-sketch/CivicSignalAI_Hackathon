---
doc: checklist
status: approved
---

# Build Checklist

Build mode: Learn

## Slices

- [ ] **1. Citizen can preview and submit a report**
  Becomes usable: The local app opens to the citizen reporting screen. A valid report can be previewed with clearly labeled rule-based summary, category/priority suggestions, missing-detail prompts, and duplicate suggestions; preview creates no database row or timeline event. Final submission creates one persistent report and its initial timeline event.
  Why now: Combines bootstrapping with the first usable end-to-end behavior and proves the project's unique reporting-and-analysis kernel before building surrounding surfaces.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Issue Submission and AI Analysis`, `prd.md > Duplicate Suggestions`, `prd.md > Acceptance Criteria`
  Spec ref: `spec.md > Stack`, `spec.md > Where It Runs and How Someone Tries It`, `spec.md > Components > Citizen Reporting Interface`, `spec.md > Components > Rule Analysis Engine`, `spec.md > Components > Duplicate Detection Service`, `spec.md > API Contract > Preview analysis request`, `spec.md > API Contract > Report creation`, `spec.md > Analysis preview vs final submission`
  Build: Bootstrap the app in this slice: create the spec's file structure, set up Python 3.11+ with `py -m venv .venv`, activate with `.\.venv\Scripts\Activate.ps1`, and install FastAPI/Uvicorn from `requirements.txt` with `python -m pip install -r requirements.txt`. Add FastAPI static serving, SQLite connection/schema for `reports` and `report_events` using standard-library `sqlite3`, and the citizen form. Implement the spec-required `GET /api/health` route in `app/api/health.py`. Implement supported-category validation, rule-based preview and duplicate suggestions, then final report creation with backend-recomputed summary/priority and one SQLite transaction for the report plus its initial `created` event. Keep preview read-only; do not add external AI, authentication, or seeded-data tooling. Add focused input, preview, duplicate, creation, and rollback tests using Python's standard-library `unittest`.
  Verify (mechanical): Confirm `python --version` reports Python 3.11 or later. Run `python -m unittest discover -s tests`; confirm preview tests leave report/event counts unchanged, a successful create returns one report and one `created` event, and a forced initial-event insert failure rolls back the report. Start the app with the spec's Uvicorn command and confirm the citizen page loads. Confirm `GET /api/health` returns HTTP 200 with `{"status":"ok"}`. Do not complete this slice or begin the next until its relevant automated tests pass and the preview/submit behavior works in the running app.
  Learner check: Open the citizen page, enter an example such as a broken streetlight, preview and inspect the labeled suggestions, then submit. Confirm preview did not save anything and submission shows a report ID and confirmation.
  Commit: `Build citizen preview and atomic report creation`

- [ ] **2. Team can update a report through the shared timeline**
  Becomes usable: The team dashboard lists and opens persisted reports. A team member can acknowledge, move a report in progress, add progress/evidence notes, and resolve it only with a resolution note; the citizen can see the same updates after reloading.
  Why now: Extends the working report into the scope's core transparent response loop while keeping the single SQLite dataset and timeline as the source of truth.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Team Dashboard Actions`, `prd.md > Citizen Status Tracking`, `prd.md > Acceptance Criteria`
  Spec ref: `spec.md > Components > Team Dashboard`, `spec.md > Components > Persistence Layer`, `spec.md > API Contract > Report listing`, `spec.md > API Contract > Report details`, `spec.md > API Contract > Team status update`, `spec.md > API Contract > Timeline event mapping`, `spec.md > Allowed status transitions`, `spec.md > Data Model > ReportEvent or TimelineEntry`
  Build: Implement report list/detail/timeline reads and the team status-update endpoint. Add the team queue and detail controls using the approved HTML/CSS/JavaScript frontend. Enforce only `submitted -> acknowledged -> in_progress -> resolved`, non-empty resolution notes, and note/evidence-only updates in allowed states. Map each accepted update to the specified timeline event(s), insert events in deterministic order, and commit the report update plus its events in one transaction. Render progress, resolution, and optional text evidence from persisted events.
  Verify (mechanical): Run `python -m unittest discover -s tests`; verify valid transitions, skipped/backward/repeated transitions, note-only and evidence-only events, event ordering, HTTP 422/409 behavior, resolution-note enforcement, and rollback if an update/event write fails. Do not complete this slice or begin the next until its relevant automated tests pass and the team-to-citizen timeline behavior works in the running app.
  Learner check: Open the team dashboard, acknowledge a submitted report, move it in progress, add a note, then resolve it with a resolution note. Reload the citizen view and confirm the status and timeline match; try resolving without a note and confirm it is blocked.
  Commit: `Add shared team status and timeline workflow`

- [ ] **3. Citizen can track reports and identify demo samples**
  Becomes usable: The citizen tracking screen shows reports submitted in that browser, report details and shared timeline. Citizen and team screens clearly identify the local demo; intentionally seeded sample rows are labeled separately.
  Why now: Builds on the shared API from slice 2 so both views show consistent persisted records, response fields, and demo labeling without implying privacy or live city integration.
  PRD ref: `prd.md > Screens and Layout`, `prd.md > Citizen Status Tracking`, `prd.md > Persistence and Recovery`, `prd.md > States and Boundaries`, `prd.md > Product Decisions`, `prd.md > Acceptance Criteria`
  Spec ref: `spec.md > Components > Citizen Tracking Interface`, `spec.md > Components > Simulated Notifications`, `spec.md > Components > Team Dashboard`, `spec.md > API Contract > Report listing`, `spec.md > API Contract > Report details`, `spec.md > Data Model > Report`, `spec.md > Data Model > Demo-data semantics`
  Build: Implement citizen list/detail views using the shared list/detail endpoints and browser-stored submitted report IDs as a display filter only. Render status and timeline data from the API. Include `demo_data_flag` and `analysis_source` in list responses and `demo_data_flag` in detail responses; keep values aligned with the persisted report model. Show the persistent local-demo notice on both screens and a sample label only when `demo_data_flag` is true. Keep sample seeding optional; use an intentionally flagged test fixture rather than adding a seed/reset feature. Add the specified in-app notices and empty/no-result states.
  Verify (mechanical): Run `python -m unittest discover -s tests`; verify list/detail responses expose the required fields, API-created reports return `demo_data_flag: false`, seeded test samples return `true`, and analysis-failure records return `analysis_source: unavailable`. Confirm empty/no-result and local-demo labeling tests pass. Do not complete this slice or begin the next until its relevant automated tests pass and tracking/demo labels work in the running app.
  Learner check: Submit a report in the citizen screen, view it in tracking and the team queue, then refresh after a team update. Confirm the timeline is shared, the local-demo notice is visible in both views, and only a seeded sample has the sample label.
  Commit: `Add citizen tracking and demo labels`

- [ ] **4. App handles failures and survives restart**
  Becomes usable: Valid reports can still be submitted if rule-based analysis fails, invalid inputs and failed database writes are reported clearly, and persisted reports and events remain available after closing/reopening SQLite and restarting the app.
  Why now: Completes the required recovery and failure states after the full reporting/team/tracking journey exists, then verifies the proof of concept against its acceptance criteria.
  PRD ref: `prd.md > Issue Submission and AI Analysis`, `prd.md > Persistence and Recovery`, `prd.md > States and Boundaries`, `prd.md > Acceptance Criteria`
  Spec ref: `spec.md > API Contract > Shared conventions`, `spec.md > API Contract > Preview analysis request`, `spec.md > API Contract > Report creation`, `spec.md > Data Model > Design note`, `spec.md > Analysis preview vs final submission`, `spec.md > Important Failure Modes`, `spec.md > Testing plan`, `spec.md > Where It Runs and How Someone Tries It`
  Build: Implement the specified preview `503` behavior without writes and the final-submit fallback that saves the report/event with null summary and priority plus `analysis_source: unavailable`, without a misleading analysis label. Show the clear fallback message and keep submission enabled for valid input. Handle database errors with transaction rollback and clear UI feedback. Complete connection close/reopen and application-restart persistence checks, then run the full acceptance suite. Do not add external AI credentials, notifications, authentication, or other out-of-scope services.
  Verify (mechanical): Run `python -m unittest discover -s tests`; verify preview failure returns `503` with no writes, final submission still persists the report and initial event without fabricated suggestions, failed report/event inserts roll back together, and data survives SQLite connection close/reopen and app restart. Start with `python -m uvicorn app.main:app --reload` and confirm the final core journey works. Do not complete this slice until the full automated suite passes and the failure/restart behavior works in the running app.
  Learner check: Temporarily exercise the analysis-unavailable path and confirm the app explains that no suggestions were generated while allowing submission. Restart the app and confirm the saved report and complete timeline remain visible. Try invalid input and a resolution without a note.
  Commit: `Verify failure handling and restart persistence`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — after slice 1, while feedback can still shape the remaining workflow
- [ ] Final kick-the-tires exploration and feedback completed — after slice 4

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

Complete this section after all implementation slices and final review, during the Skill Pack's Learning Wrap-Up. `devpost/app-map.html` is required before the `5-build` handoff, but it is not a prerequisite to starting or completing implementation slices.

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [x] `devpost/app-map.html` generated from current code, checked in a local browser, and shown as a reference, including a project-grounded practice to reuse

Activity and evidence: No learner walkthrough or learning activity is evidenced by this workspace. The standalone map was opened from `file://` and rendered; this verifies the artifact only.
Route and stops: Reference-only route through `static/report.html` and `static/js/app.js`, `app/api/reports.py` and `app/database.py`, then `app/api/team.py` and the tracking/dashboard scripts. No learner tour is claimed.
Edit outcome: No learning exercise edit was attempted; application/security changes for submission preparation are documented separately and are not presented as learner practice.
Reflection: No learner reflection is evidenced. A placeholder is provided in `devpost/submission-draft.md` for the owner to write a genuine reflection.
Activity mode: Static source reference only; no hands-on learner activity verified.

## Revisions

- 2026-10-19: Added a source-based `devpost/app-map.html` reference and a factual submission/demo prep file. The original slice and learner-check boxes remain unchecked because this workspace does not contain evidence that those Skill Pack activities occurred. The app-map is not a substitute for the learner's code tour, final review, eligibility proof, or reflection.
