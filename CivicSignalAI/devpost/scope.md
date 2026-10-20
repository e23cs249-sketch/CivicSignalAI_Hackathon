---
doc: scope
status: approved
---

# CivicSignal AI

> Historical planning record: the original approved scope below predates account-based authentication, interactive map selection, and image uploads, which it listed as out of scope or later work. The dated implementation revision at the end documents subsequent code; it does not claim those features were in the original plan or verify Skill Pack activity.

AI-assisted civic issue reporting and resolution tracking for everyday public problems, designed as a focused proof of concept for a hackathon.

## The Unique Kernel
CivicSignal AI turns a basic civic complaint into a structured, AI-assisted workflow that helps citizens understand what happened, what team might need to act, and how the issue is progressing. The distinctive part is not just reporting—it is the transparent loop from issue submission to AI analysis, suggested routing, acknowledgement, updates, and resolution evidence.

## Who It's For
This is for residents who want a simple way to report everyday public problems and for a small test-team dashboard that needs a lightweight, transparent way to acknowledge, route, and update those issues. The typical user is a citizen with a local concern such as overflowing garbage, a broken streetlight, a damaged road, a water leak, or an unsafe sidewalk.

## The Core Loop
A citizen opens the app and submits an issue with a short description, category, and optional location or landmark. The app uses AI to summarize the report, suggest a category and priority, flag missing details, and surface likely duplicates. A test-team dashboard then acknowledges the report, adds a status update, and records a resolution note or evidence. The citizen receives a clear status change and can see how the issue progressed. In the MVP, any AI-generated output must come from a genuinely available free option with verified usage limits; if no suitable free AI service exists, the workflow falls back to a clearly labelled rule-based analysis so the app remains functional. AI-generated results and rule-based fallback results are clearly distinguished in the UI and data model.

## Inspiration & Identity
In spirit, this is inspired by civic service reporting tools and 311 workflows, but simplified and much more demo-friendly. The overall feeling should be clear, practical, and trustworthy rather than bureaucratic or intimidating. We want the experience to feel approachable for the public and organized for the responding team.

## Why This Matters to the Learner
This project matters because it addresses a real civic pain point: everyday public issues are often hard to report and even harder to track after submission. It also gives the team a realistic problem to solve with a clear user journey, a visible AI workflow, and a small but complete system that can be demonstrated in a short hackathon window.

## What "Working" Looks Like
The proof of concept works when a citizen can submit a report, see AI-generated analysis or a clearly labelled rule-based fallback, and then observe the issue move through a team dashboard from acknowledgement to progress updates to resolution evidence. The strongest demo moment is when a report is submitted, the AI suggests a duplicate or missing detail or the fallback offers a structured suggestion, the team acknowledges it, and the citizen sees a clear status update and final resolution note.

## The POC Boundary
In scope:
- citizen issue submission form with description, category, and optional location/landmark
- AI summary, suggested category, suggested priority, duplicate detection, and missing-detail prompts using a genuinely available free AI service with verified usage limits or a clearly labelled rule-based fallback when no suitable free AI option is available
- duplicate detection that compares new report descriptions against existing reports using a simple, explainable method and presents possible duplicates as suggestions rather than confirmed matches
- persistence of reports and status updates across page refreshes and app restarts
- required resolution note to mark a report resolved; photo or other evidence is optional
- citizen-facing issue tracking view with status progression
- test-team dashboard with acknowledgement, status updates, and resolution note/evidence
- simulated notifications and clearly labelled demo data
- single working path for a small number of issue categories

Out of scope for now:
- live government system integrations
- real geospatial mapping, routing, or GIS services
- real email/SMS or production notifications
- account-based auth beyond demo-safe mock flows
- large-scale data processing or analytics
- real-world incident dispatch or agency handoff

## Later
- map-based issue visualization and geocoding
- better duplicate detection using location and historical pattern matching
- real multi-team routing and assignment rules
- richer analytics for team performance and issue trends
- more advanced AI prompts and confidence scoring
- production-quality authentication and audit logs

## Explicitly Cut
- No paid API or surprise-charge AI service assumptions.
- No claim of real integration with public agencies or government systems.
- No live external dispatch or work-order syncing.
- No polished production-grade scaling or broad multi-city deployment.
- No fake claim that the app is already in use by a city unless it is implemented and verified.

## Implementation Revision — 2026-10-19

This revision records the current local application, verified against its FastAPI routes, services, and tests. It is not a retroactive change to the original approved scope.

- The current kernel is an authenticated report-to-response loop: a citizen owns a report, selects or enters a location, may attach private photo evidence, and can track its status and timeline; provisioned staff review and update the same persisted report.
- Citizen and team accounts use password hashes and server-side sessions. Citizens can access only their own reports and associated media; team routes require staff authentication.
- Reports include title, category, description, area/address, optionally confirmed map coordinates, a timeline, and optional original/progress photos. The browser supports a three-step issue/details/review flow.
- Analysis and duplicate matches are local rule-based suggestions. No external AI service is configured, and suggestions are not verified facts.
- The application uses SQLite and host-local private upload storage. It is a prototype, not connected to city systems and not a live service.
- Current exclusions remain live agency integration, external AI, geocoding, email/SMS delivery, cloud database/storage, and production deployment operations.
- Automated coverage is in `tests/`; the suite exercises authentication, ownership, workflow, media validation/authorization, and persistence. Current test results are recorded only after the final verification run.
